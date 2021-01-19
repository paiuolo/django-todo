from django import template

from ..utils import user_can_toggle_task_done

register = template.Library()


@register.simple_tag
def todo_user_can_toggle_task_done(user, task):
    return user_can_toggle_task_done(user, task)
