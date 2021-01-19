from django.db.models import Q

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin

from ..utils import staff_check
from ..models import Task, TaskList
from .serializers import (TicketSerializer, TaskSerializer,
                          TaskListSerializer, TaskListDetailSerializer)


class ExternalAddApiView(CreateModelMixin, GenericViewSet):
    model = Task
    serializer_class = TicketSerializer
    permission_classes = (IsAuthenticated, )
    queryset = Task.objects.none()


class TaskListsApiView(ListModelMixin, GenericViewSet):
    serializer_class = TaskListSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        user = self.request.user
        if staff_check(user):
            return TaskList.objects.all()
        else:
            return TaskList.objects.filter(group__in=user.groups.all())

    def list(self, request, *args, **kwargs):
        return super(TaskListsApiView, self).list(request, *args, **kwargs)


class TaskListDetailApiView(RetrieveModelMixin, GenericViewSet):
    serializer_class = TaskListDetailSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        user = self.request.user
        if staff_check(user):
            return TaskList.objects.all()
        else:
            return TaskList.objects.filter(group__in=user.groups.all())

    def retrieve(self, request, *args, **kwargs):
        return super(TaskListDetailApiView, self).retrieve(request, *args, **kwargs)


class TaskDetailApiView(ReadOnlyModelViewSet):
    serializer_class = TaskSerializer
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        user = self.request.user

        if not staff_check(user):
            return Task.objects.filter(Q(created_by=user) | Q(assigned_to=user))
        else:
            return Task.objects.filter(is_active=True)

    def retrieve(self, request, pk=None, *args, **kwargs):
        return super(TaskDetailApiView, self).retrieve(request, pk, *args, **kwargs)
