from django import template

from ..utils import get_user_tasks

register = template.Library()


@register.simple_tag
def todo_user_tasks(task_list, user, completed=None):
    return get_user_tasks(task_list, user, completed)
