import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Q  # pai
from django.utils import timezone  # pai
from django.core.paginator import Paginator  # pai

from todo.forms import SearchForm
from todo.models import Task, TaskList
from todo.utils import staff_check, get_user_groups


@login_required
# @user_passes_test(staff_check)  # pai
def list_lists(request) -> HttpResponse:
    """Homepage view - list of lists a user can view, and ability to add a list.
    """

    thedate = timezone.now()
    searchform = SearchForm(auto_id=False)

    # Make sure user belongs to at least one group.
    if not request.user.is_superuser:  # pai
        if not get_user_groups(request.user).exists():
            messages.warning(
                request,
                "You do not yet belong to any groups. Ask your administrator to add you to one.",
            )

    lists = TaskList.objects.filter(is_active=True).order_by("group__name", "name")

    # superusers see all lists, so count shouldn't filter by just lists the admin belongs to  # pai disabled
    if not staff_check(request.user):
        task_count = (
            Task.objects.filter(is_active=True).filter(completed=False)
                .filter(task_list__group__in=get_user_groups(request.user)).filter(
                            Q(created_by=request.user) | Q(assigned_to=request.user))  # pai
                .count()
        )

        lists = lists.filter(group__in=get_user_groups(request.user))
    else:
        task_count = (
            Task.objects.filter(is_active=True).filter(completed=False)
            .count()
        )

    list_count = lists.count()

    # Pagination
    paginator = Paginator(lists, 20)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "lists": lists,
        "thedate": thedate,
        "searchform": searchform,
        "list_count": list_count,
        "task_count": task_count,
        'page_obj': page_obj
    }

    return render(request, "todo/list_lists.html", context)
