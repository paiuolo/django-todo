from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.core.paginator import Paginator  # pai

from todo.models import Task
from todo.utils import staff_check
from todo.forms import SearchForm


@login_required
# @user_passes_test(staff_check)  # pai
def search(request) -> HttpResponse:
    """Search for tasks user has permission to see.
    """

    query_string = ''

    if request.POST:
        form = SearchForm(request.POST)

        if form.is_valid():
            query_string = form.cleaned_data.get('q', '').strip()

    else:
        if "q" in request.GET:
            query_string = request.GET["q"].strip()

        initial = {'q': query_string}
        form = SearchForm(initial=initial)

    context = {"form": form}

    if query_string != '':
        found_tasks = Task.objects.filter(is_active=True).filter(
            Q(title__icontains=query_string) | Q(note__icontains=query_string)
        )

    else:
        found_tasks = None

    # Only include tasks that are in groups of which this user is a member:
    # if not request.user.is_superuser:
    if found_tasks is not None:
        if not staff_check(request.user):  # pai
            found_tasks = found_tasks.filter(Q(created_by=request.user) |
                                             Q(assigned_to=request.user) |
                                             Q(assigned_to__isnull=True,
                                               task_list__group__in=request.user.groups.all()))

    # Pagination
    paginator = Paginator(found_tasks if found_tasks is not None else [], 10)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context["page_obj"] = page_obj

    context["query_string"] = query_string
    context["found_tasks"] = found_tasks

    return render(request, "todo/search_results.html", context)
