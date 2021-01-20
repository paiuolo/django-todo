from django import template

from ..utils import get_task_list_tasks

register = template.Library()


@register.simple_tag
def todo_get_task_list_tasks(task_list, user=None, completed=None):
    return get_task_list_tasks(task_list, user, completed)
