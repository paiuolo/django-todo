import bleach
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Q  # pai
from django.core.paginator import Paginator

from todo.forms import AddEditTaskForm
from todo.models import Task, TaskList
from todo.utils import send_notify_mail, staff_check, get_user_task_list_tasks


@login_required
# @user_passes_test(staff_check)  # pai, permit owner listing
def list_detail(request, list_id=None, list_slug=None, view_completed=False) -> HttpResponse:
    """Display and manage tasks in a todo list.
    """

    # Defaults
    task_list = None
    form = None

    # Which tasks to show on this list view?
    if list_slug == "mine":
        tasks = Task.objects.filter(is_active=True).filter(Q(assigned_to=request.user) |
                                                           Q(assigned_to__isnull=True,
                                                           task_list__group__in=request.user.groups.all()))
    else:
        # pai
        #if task_list.group not in request.user.groups.all() and not request.user.is_superuser:
        if staff_check(request.user):
            # Show a specific list, ensuring permissions.
            task_list = get_object_or_404(TaskList, id=list_id)

            tasks = Task.objects.filter(is_active=True) \
                                .filter(task_list=task_list.id) \
                                .prefetch_related('created_by', 'assigned_to')
        else:
            # Show a specific list, ensuring permissions.
            task_list = get_object_or_404(TaskList, id=list_id, group__in=request.user.groups.all())

            tasks = get_user_task_list_tasks(task_list, request.user)

    # Additional filtering
    if view_completed:
        tasks = tasks.filter(completed=True)
    else:
        tasks = tasks.filter(completed=False)

    # ######################
    #  Add New Task Form
    # ######################

    if request.POST.getlist("add_edit_task"):
        form = AddEditTaskForm(
            request.user,
            request.POST,
            initial={"assigned_to": request.user.id, "priority": 999, "task_list": task_list},
        )

        if form.is_valid():
            new_task = form.save(commit=False)
            new_task.created_by = request.user
            new_task.note = bleach.clean(form.cleaned_data["note"], strip=True)
            form.save()

            # Send email alert only if Notify checkbox is checked AND assignee is not same as the submitter
            if (
                "notify" in request.POST
                and new_task.assigned_to
                and new_task.assigned_to != request.user
            ):
                send_notify_mail(new_task)

            messages.success(request, 'New task "{t}" has been added.'.format(t=new_task.title))
            return redirect(request.path)
        else:
            pass
    else:
        # Don't allow adding new tasks on some views
        if list_slug not in ["mine", "recent-add", "recent-complete"]:
            form = AddEditTaskForm(
                request.user,
                initial={"assigned_to": request.user.id, "priority": 999, "task_list": task_list},
            )

    # Pagination
    paginator = Paginator(tasks, 20)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "list_id": list_id,
        "list_slug": list_slug,
        "task_list": task_list,
        "form": form,
        "tasks": tasks,
        "view_completed": view_completed,
        'page_obj': page_obj
    }

    return render(request, "todo/list_detail.html", context)
