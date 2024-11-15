from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _  # pai
from django.http import HttpResponseNotAllowed

from todo.models import Task
from todo.utils import toggle_task_completed
from todo.utils import staff_check, user_can_toggle_task_done  # pai


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
        if not user_can_toggle_task_done(request.user, task):
            # raise PermissionDenied
            messages.error(request, _("Can not change completion status for ") + '"' + task.title + '".')

            return redirect(reverse("todo:task_detail",
                                    args=(task.pk,)))

        if task.procedure_uuid is None:
            _redir_url = reverse("todo:list_detail", kwargs={"list_id": task.task_list.id,
                                                             "list_slug": task.task_list.slug})
        else:
            _redir_url = reverse('procedures:instance-detail', args=[task.procedure_uuid])

        # prevent toggle for specific actions
        if (request.GET.get('done', False) and task.completed) or \
           (request.GET.get('not_done', False) and not task.completed):
            # task has changed completion status while user was looking at page
            messages.error(request, _("Can not change completion status for ") + '"' + task.title + '".')

            redir_url = _redir_url

        else:
            try:
                toggle_task_completed(task.id, user=request.user)

            except Exception as e:
                messages.error(request,
                               _("Can not change completion status.") + ' ' + str(e))

                # redirect to task detail
                redir_url = reverse("todo:task_detail",
                                    args=(task.pk,))
            else:
                messages.success(request, _("Task completion status changed for ") + '"' + task.title + '".')

                redir_url = request.GET.get('next', _redir_url)

        return redirect(redir_url)

    else:
        return HttpResponseNotAllowed(permitted_methods=('post', 'options'))
