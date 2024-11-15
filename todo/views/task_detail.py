import bleach
from django import forms
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required  # , user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _  # pai

from todo.defaults import defaults
from todo.features import HAS_TASK_MERGE
from todo.forms import AddEditTaskForm
from todo.models import Comment, Task
from todo.utils import (
    send_email_to_thread_participants,
    staff_check,
    # toggle_task_completed,
    user_can_read_task,
)

from todo.utils import add_attachment_file  # pai

if HAS_TASK_MERGE:
    from dal import autocomplete


def handle_add_comment(request, task):
    if not request.POST.get("add_comment"):
        return

    comment_body = bleach.clean(request.POST["comment-body"], strip=True)

    _comment, created = Comment.objects.get_or_create(
        author=request.user, task=task, body=comment_body
    )

    if created:
        send_email_to_thread_participants(
            task,
            request.POST["comment-body"],
            request.user,
            subject='New comment posted on task "{}"'.format(task.title),
        )

        messages.success(request, _("Comment posted. Notification email sent to thread participants."))


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
        # raise PermissionDenied  # pai
        raise Http404

    comment_list = Comment.objects.filter(task=task_id).order_by("-created_at")  # pai

    # Handle task merging
    if not HAS_TASK_MERGE:
        merge_form = None
    else:

        class MergeForm(forms.Form):
            merge_target = forms.ModelChoiceField(
                queryset=Task.objects.filter(is_active=True),
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
    # staff can edit task, non staff can only if creator
    if (task.procedure_uuid is None and staff_check(request.user) or
            (task.procedure_uuid is None and task.created_by == request.user)) \
       and request.POST.getlist("add_edit_task"):  # pai

        form = AddEditTaskForm(
            request.user, request.POST, instance=task, initial={"task_list": task.task_list}
        )

        if form.is_valid():
            item = form.save(commit=False)
            item.note = bleach.clean(form.cleaned_data["note"], strip=True)
            item.title = bleach.clean(form.cleaned_data["title"], strip=True)
            item.save()
            messages.success(request, _("The task has been edited."))
            return redirect(
                "todo:list_detail", list_id=task.task_list.id, list_slug=task.task_list.slug
            )
    else:
        form = AddEditTaskForm(request.user, instance=task, initial={"task_list": task.task_list})

    """
    # pai (why duplicate toggle_done view?)
    # Mark complete
    if request.POST.get("toggle_done"):
        results_changed = toggle_task_completed(task.id, user=request.user)
        if results_changed:
            messages.success(request, _("Task completion status changed for ") + '"' + task.title + '".')
        else:
            messages.error(request, _("Can not change completion status for ") + '"' + task.title + '".')

        return redirect("todo:task_detail", task_id=task.id)
    """

    if task.due_date:
        thedate = task.due_date
    else:
        thedate = timezone.now()

    # Handle uploaded files
    # pai
    # Attachment.objects.create(
    #    task=task, added_by=request.user, timestamp=datetime.datetime.now(), file=file
    # )

    attachment_file = request.FILES.get("attachment_file_input", None)
    if attachment_file is not None:
        try:
            add_attachment_file(request, attachment_file, task)  # pai

        except Exception as e:
            messages.error(request, str(e))
            return redirect("todo:task_detail", task_id=task.id)

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
