import datetime
import os

import bleach
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404  # pai
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from todo.defaults import defaults
from todo.features import HAS_TASK_MERGE
from todo.forms import AddEditTaskForm
from todo.models import Attachment, Comment, Task
from todo.utils import (
    send_email_to_thread_participants,
    staff_check,
    toggle_task_completed,
    user_can_read_task,
)

from filer.models import File as FilerFile, Folder as FilerFolder  # pai

if HAS_TASK_MERGE:
    from dal import autocomplete


def handle_add_comment(request, task):
    if not request.POST.get("add_comment"):
        return

    Comment.objects.create(
        author=request.user, task=task, body=bleach.clean(request.POST["comment-body"], strip=True)
    )

    send_email_to_thread_participants(
        task,
        request.POST["comment-body"],
        request.user,
        subject='New comment posted on task "{}"'.format(task.title),
    )

    messages.success(request, "Comment posted. Notification email sent to thread participants.")


@login_required
# @user_passes_test(staff_check)  # pai, permit owner updates
def task_detail(request, task_id: int) -> HttpResponse:
    """View task details. Allow task details to be edited. Process new comments on task.
    """

    task = get_object_or_404(Task, pk=task_id)
    # comment_list = Comment.objects.filter(task=task_id).order_by("-date")  # pai

    # Ensure user has permission to view task. Superusers can view all tasks.
    # Get the group this task belongs to, and check whether current user is a member of that group.
    if not user_can_read_task(task, request.user):
        raise PermissionDenied

    comment_list = Comment.objects.filter(task=task_id).order_by("-date")  # pai

    # Handle task merging
    if not HAS_TASK_MERGE:
        merge_form = None
    else:

        class MergeForm(forms.Form):
            merge_target = forms.ModelChoiceField(
                queryset=Task.objects.all(),
                widget=autocomplete.ModelSelect2(
                    url=reverse("todo:task_autocomplete", kwargs={"task_id": task_id})
                ),
            )

        # Handle task merging
        if not request.POST.get("merge_task_into"):
            merge_form = MergeForm()
        else:
            merge_form = MergeForm(request.POST)
            if merge_form.is_valid():
                merge_target = merge_form.cleaned_data["merge_target"]
            if not user_can_read_task(merge_target, request.user):
                raise PermissionDenied

            task.merge_into(merge_target)
            return redirect(reverse("todo:task_detail", kwargs={"task_id": merge_target.pk}))

    # Save submitted comments
    handle_add_comment(request, task)

    # Save task edits
    if not request.POST.get("add_edit_task"):
        form = AddEditTaskForm(request.user, instance=task, initial={"task_list": task.task_list})
    else:
        form = AddEditTaskForm(
            request.user, request.POST, instance=task, initial={"task_list": task.task_list}
        )

        if form.is_valid():
            item = form.save(commit=False)
            item.note = bleach.clean(form.cleaned_data["note"], strip=True)
            item.title = bleach.clean(form.cleaned_data["title"], strip=True)
            item.save()
            messages.success(request, "The task has been edited.")
            return redirect(
                "todo:list_detail", list_id=task.task_list.id, list_slug=task.task_list.slug
            )

    # Mark complete
    if request.POST.get("toggle_done"):
        results_changed = toggle_task_completed(task.id)
        if results_changed:
            messages.success(request, f"Changed completion status for task {task.id}")

        return redirect("todo:task_detail", task_id=task.id)

    if task.due_date:
        thedate = task.due_date
    else:
        thedate = datetime.datetime.now()

    # Handle uploaded files
    if request.FILES.get("attachment_file_input"):
        file = request.FILES.get("attachment_file_input")

        if file.size > defaults("TODO_MAXIMUM_ATTACHMENT_SIZE"):
            messages.error(request, f"File exceeds maximum attachment size.")
            return redirect("todo:task_detail", task_id=task.id)

        name, extension = os.path.splitext(file.name)

        if extension not in defaults("TODO_LIMIT_FILE_ATTACHMENTS"):
            messages.error(request, f"This site does not allow upload of {extension} files.")
            return redirect("todo:task_detail", task_id=task.id)

        # pai
        #Attachment.objects.create(
        #    task=task, added_by=request.user, timestamp=datetime.datetime.now(), file=file
        #)
        user = task.created_by  #!!

        if 'django_sso_app' in settings.INSTALLED_APPS:
            user_id = user.sso_id
        else:
            user_id = user.username

        created_attachment = Attachment.objects.create(
            task=task, added_by=user, timestamp=datetime.datetime.now(), file=file
        )

        created_attachment_task = created_attachment.task
        created_attachment_task_list = created_attachment_task.task_list

        # creating filer folders
        users_folder, _created = FilerFolder.objects.get_or_create(name='users')
        user_folder, _created = FilerFolder.objects.get_or_create(name=user_id,
                                                                  parent=users_folder,
                                                                  owner=user)
        user_tasks_folder, _created = FilerFolder.objects.get_or_create(name='tasks',
                                                                        parent=user_folder)
        user_tasklist_folder, _created = FilerFolder.objects.get_or_create(name=created_attachment_task_list.slug,
                                                                           parent=user_tasks_folder)
        user_tasklist_task_folder, _created = FilerFolder.objects.get_or_create(name=str(created_attachment_task.id),
                                                                                parent=user_tasklist_folder)

        # creating filer file
        filer_file = FilerFile()
        filer_file.file = created_attachment.file
        filer_file.owner = user
        filer_file.original_filename = os.path.basename(created_attachment.file.name)
        filer_file.folder = user_tasklist_task_folder

        filer_file.save()

        # update attachment
        created_attachment.filer_file = filer_file
        created_attachment.save()

        messages.success(request, f"File attached successfully")
        return redirect("todo:task_detail", task_id=task.id)

    context = {
        "task": task,
        "comment_list": comment_list,
        "form": form,
        "merge_form": merge_form,
        "thedate": thedate,
        "comment_classes": defaults("TODO_COMMENT_CLASSES"),
        "attachments_enabled": defaults("TODO_ALLOW_FILE_ATTACHMENTS"),
    }

    return render(request, "todo/task_detail.html", context)
