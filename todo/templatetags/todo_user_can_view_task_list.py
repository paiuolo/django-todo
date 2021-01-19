from django import template

from ..utils import user_can_view_task_list

register = template.Library()


@register.simple_tag
def todo_user_can_view_task_list(user, task_list):
    return user_can_view_task_list(user, task_list)
