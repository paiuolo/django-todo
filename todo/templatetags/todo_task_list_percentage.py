from django import template

from ..utils import get_task_list_tasks

register = template.Library()


@register.simple_tag
def todo_task_list_percentage(task_list, user):
    user_tasks = get_task_list_tasks(task_list, user).count()

    if user_tasks == 0:
        return 0
    else:
        completed_user_tasks = get_task_list_tasks(task_list, user, True).count()
        return int((completed_user_tasks * 100) / user_tasks)
