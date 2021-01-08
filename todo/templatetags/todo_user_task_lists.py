from django import template

from ..models import TaskList
from ..utils import staff_check

register = template.Library()


@register.simple_tag
def todo_user_task_lists(user):
    if staff_check(user):
        return TaskList.objects.all()
    else:
        return TaskList.objects.filter(group__in=user.groups.all())
