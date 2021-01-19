from django import template

from ..utils import staff_check

register = template.Library()


@register.simple_tag
def todo_staff_check(user):
    return staff_check(user)
