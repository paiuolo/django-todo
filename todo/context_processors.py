from django.conf import settings

from .models import TaskList
from .utils import staff_check


def todo_context(request):
    if staff_check(request.user):
        task_lists = TaskList.objects.all()
    else:
        task_lists = TaskList.objects.filter(group__in=request.user.groups.all())

    return {
        "TASK_LISTS": task_lists
    }
