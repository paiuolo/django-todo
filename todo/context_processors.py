from django.conf import settings

from .models import TaskList
from .utils import staff_check, get_user_groups


def todo_context(request):
    if staff_check(request.user):
        task_lists = TaskList.objects.all()
    else:
        task_lists = TaskList.objects.filter(group__in=get_user_groups(request.user))

    return {
        "TASK_LISTS": task_lists,
        "TODO_ENABLE_ISSUE_TRACKER": getattr(settings, 'TODO_ENABLE_ISSUE_TRACKER', True)
    }
