from django import template

from ..models import TaskList
from ..utils import staff_check, get_user_groups

register = template.Library()


@register.simple_tag
def todo_user_task_lists(user):
    if staff_check(user):
        return TaskList.objects.filter(is_active=True).order_by('group__name')
    else:
        return TaskList.objects.filter(is_active=True).filter(group__in=get_user_groups(user)).order_by('group__name')
