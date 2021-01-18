import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Q  # pai
from django.utils import timezone  # pai

from todo.forms import SearchForm
from todo.models import Task, TaskList
from todo.utils import staff_check


@login_required
# @user_passes_test(staff_check)  # pai
def list_lists(request) -> HttpResponse:
    """Homepage view - list of lists a user can view, and ability to add a list.
    """

    thedate = timezone.now()
    searchform = SearchForm(auto_id=False)

    # Make sure user belongs to at least one group.
    if not request.user.groups.all().exists():
        messages.warning(
            request,
            "You do not yet belong to any groups. Ask your administrator to add you to one.",
        )

    # Superusers see all lists
    lists = TaskList.objects.filter(is_active=True).order_by("group__name", "name")
    if not request.user.is_superuser:
        lists = lists.filter(group__in=request.user.groups.all())

    list_count = lists.count()

    # superusers see all lists, so count shouldn't filter by just lists the admin belongs to
    if request.user.is_superuser:
        task_count = Task.objects.filter(is_active=True, is_scaffold=False).filter(completed=False).count()
    else:
        if not staff_check(request.user):
            task_count = (
                Task.objects.filter(is_active=True, is_scaffold=False).filter(completed=False)
                    .filter(task_list__group__in=request.user.groups.all()).filter(
                                Q(created_by=request.user) | Q(assigned_to=request.user))  # pai
                    .count()
            )
        else:
            task_count = (
                Task.objects.filter(is_active=True, is_scaffold=False).filter(completed=False)
                .count()
            )

    context = {
        "lists": lists,
        "thedate": thedate,
        "searchform": searchform,
        "list_count": list_count,
        "task_count": task_count,
    }

    return render(request, "todo/list_lists.html", context)
