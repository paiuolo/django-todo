from django import template

from ..models import TaskList
from ..utils import staff_check

register = template.Library()


@register.simple_tag
def todo_user_task_lists(user):
    if staff_check(user):
        return TaskList.objects.filter(is_active=True, is_scaffold=False)
    else:
        return TaskList.objects.filter(is_active=True, is_scaffold=False).filter(group__in=user.groups.all())
