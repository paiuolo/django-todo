from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework import status

from ..utils import staff_check, get_user_groups, user_can_toggle_task_done, toggle_task_completed
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
            return TaskList.objects.filter(group__in=get_user_groups(user))

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
            return TaskList.objects.filter(group__in=get_user_groups(user))

    def retrieve(self, request, *args, **kwargs):
        return super(TaskListDetailApiView, self).retrieve(request, *args, **kwargs)


class TaskDetailApiView(ReadOnlyModelViewSet):
    lookup_field = 'pk'
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        user = self.request.user

        if not staff_check(user):
            return Task.objects.filter(Q(created_by=user) | Q(assigned_to=user))
        else:
            return Task.objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.action in ('mark_done', 'mark_pending'):
            return Serializer
        else:
            return TaskSerializer

    def retrieve(self, request, pk=None, *args, **kwargs):
        return super(TaskDetailApiView, self).retrieve(request, pk, *args, **kwargs)

    def _toggle_done(self, request, task):
        if not user_can_toggle_task_done(request.user, task):
            return Response(_("Can not change task completion status."),
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            toggle_task_completed(task.id, user=request.user)

        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        else:
            return redirect(task.get_absolute_rest_url(), permanent=False)

    def mark_done(self, request, pk=None, *args, **kwargs):
        task = get_object_or_404(Task, pk=pk)

        if task.completed:
            return Response(_("Task already done."), status=status.HTTP_400_BAD_REQUEST)

        return self._toggle_done(request, task)

    def mark_pending(self, request, pk=None, *args, **kwargs):
        task = get_object_or_404(Task, pk=pk)

        if not task.completed:
            return Response(_("Task not done."), status=status.HTTP_400_BAD_REQUEST)

        return self._toggle_done(request, task)
