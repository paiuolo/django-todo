from django.conf.urls import url

from rest_framework.urlpatterns import format_suffix_patterns

from .views import ExternalAddApiView, TaskListsApiView, TaskListDetailApiView, TaskDetailApiView


_api_urlpatterns = [
    url(r'^ticket/add/$', ExternalAddApiView.as_view({'post': 'create'}), name='external_add'),

    url(r'^list/$', TaskListsApiView.as_view({'get': 'list'}), name='lists'),
    url(r'^list/(?P<pk>\w+)/$', TaskListDetailApiView.as_view({'get': 'retrieve'}), name='list_detail'),

    url(r'^task/(?P<pk>\d+)/mark-done/$', TaskDetailApiView.as_view({'post': 'mark_done'}),
        name='task_mark_done'),
    url(r'^task/(?P<pk>\d+)/mark-pending/$', TaskDetailApiView.as_view({'post': 'mark_pending'}),
        name='task_mark_pending'),

    url(r'^task/(?P<pk>\d+)/$', TaskDetailApiView.as_view({'get': 'retrieve'}), name='task_detail')
]

api_urlpatterns = (format_suffix_patterns(_api_urlpatterns), 'todo_api')
