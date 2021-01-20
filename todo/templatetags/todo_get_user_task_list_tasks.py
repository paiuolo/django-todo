from django import template

from ..utils import get_user_task_list_tasks

register = template.Library()


@register.simple_tag
def todo_get_user_task_list_tasks(task_list, user, completed=None):
    return get_user_task_list_tasks(task_list, user, completed)
