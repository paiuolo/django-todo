from django.contrib import messages
from django.contrib.auth.decorators import login_required  # , user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _  # pai

from todo.models import Task
from todo.utils import staff_check, user_can_delete_task


@login_required
#@user_passes_test(staff_check)  # pai
def delete_task(request, task_id: int) -> HttpResponse:
    """Delete specified task.
    Redirect to the list from which the task came.
    """

    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id)

        # Permissions
        if not user_can_delete_task(request.user, task):
            # raise PermissionDenied  # pai
            messages.error(request, _("Can not delete task '{}'.").format(task.title))

            redir_url = reverse(
                "todo:task_detail",
                args=(task.pk,),
            )

        else:
            # can delete
            task.delete()

            messages.success(request, _("Task '{}' has been deleted.").format(task.title))

            redir_url = reverse(
                "todo:list_detail",
                kwargs={"list_id": task.task_list.id, "list_slug": task.task_list.slug},
            )

        return redirect(redir_url)

    else:
        raise PermissionDenied
