from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _  # pai

from todo.models import Task
from todo.utils import toggle_task_completed
from todo.utils import staff_check


@login_required
#@user_passes_test(staff_check)  # pai
def toggle_done(request, task_id: int) -> HttpResponse:
    """Toggle the completed status of a task from done to undone, or vice versa.
    Redirect to the list from which the task came.
    """
    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)

        # Permissions
        # pai
        if not (
            (task.created_by == request.user)
            or request.user.is_superuser
            or (task.assigned_to == request.user)
            or staff_check(request.user)  # pai
            or ((task.assigned_to is None) and (task.task_list.group in request.user.groups.all()))  # pai
        ):
            raise PermissionDenied

        toggled = toggle_task_completed(task.id, user=request.user)
        if toggled:
            messages.success(request, _("Task completion status changed for ") + '"' + task.title + '".')
        else:
            messages.error(request, _("Can not change completion status for ") + '"' + task.title + '".')

        redir_url = reverse(
            "todo:list_detail",
            kwargs={"list_id": task.task_list.id, "list_slug": task.task_list.slug},
        )

        return redirect(redir_url)

    else:
        raise PermissionDenied
