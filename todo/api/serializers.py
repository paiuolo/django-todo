import base64
import mimetypes
import binascii
import uuid

from django.core.files.base import ContentFile
from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q

from rest_framework import serializers
from rest_framework.fields import Field

from ..models import Task, TaskList, Comment
from ..utils import add_attachment_file, staff_check

User = get_user_model()


class PartialObjectSerializer(serializers.Serializer):
    _partial = serializers.SerializerMethodField(method_name='get_partial')

    def get_partial(self, obj):
        return True


class UrlObjectSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField(required=False, method_name='get_url')

    def get_url(self, instance):
        request = self.context['request']

        return request.build_absolute_uri(instance.get_absolute_rest_url())


class Base64FileField(Field):
    _ERROR_MESSAGE = _('Base64 string is incorrect')

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError(self._ERROR_MESSAGE)

        try:
            mime, encoded_data = data.replace('data:', '', 1).split(';base64,')
            extension = mimetypes.guess_extension(mime)
            file = ContentFile(base64.b64decode(encoded_data), name='{name}{extension}'.format(name=str(uuid.uuid4()),
                                                                                               extension=extension))
        except (ValueError, binascii.Error):
            raise serializers.ValidationError(self._ERROR_MESSAGE)

        return file

    def to_representation(self, value):
        if not value:
            return None

        request = self.context['request']
        return request.build_absolute_uri(value.url)


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    date = serializers.DateTimeField()

    class Meta:
        model = Comment
        fields = ('author', 'date', 'body')

    def get_author(self, instance):
        if 'django_sso_app' in settings.INSTALLED_APPS:
            request = self.context['request']
            return request.build_absolute_uri(reverse('django_sso_app_user:rest-detail',
                                                      args=[instance.author.sso_id]))
        else:
            return instance.author.username


class TaskSerializer(serializers.ModelSerializer, UrlObjectSerializer):
    created_by = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField(required=False)

    created_date = serializers.DateTimeField()
    due_date = serializers.DateTimeField(required=False)

    completed = serializers.BooleanField(required=False)
    completed_date = serializers.DateTimeField(required=False)

    comments = CommentSerializer(many=True, source='comment_set')

    task_list = serializers.SerializerMethodField(required=False)

    attachments = serializers.SerializerMethodField(required=False)

    class Meta:
        model = Task
        fields = ('title', 'note',
                  'created_by',
                  'assigned_to',
                  'created_date', 'due_date',
                  'completed', 'completed_date',
                  'comments',
                  'attachments',
                  'task_list',
                  'url',
                  )

    def get_created_by(self, instance):
        if 'django_sso_app' in settings.INSTALLED_APPS:
            request = self.context['request']
            return request.build_absolute_uri(reverse('django_sso_app_user:rest-detail',
                                                      args=[instance.created_by.sso_id]))
        else:
            return instance.created_by.username

    def get_assigned_to(self, instance):
        if 'django_sso_app' in settings.INSTALLED_APPS:
            request = self.context['request']
            return request.build_absolute_uri(reverse('django_sso_app_user:rest-detail',
                                                      args=[instance.assigned_to.sso_id]))
        else:
            return instance.created_by.username

    def get_attachments(self, instance):
        request = self.context['request']

        return list(map(lambda x: request.build_absolute_uri(x.filer_file.url), instance.attachment_set.all()))

    def get_upload_attachment(self, instance):
        request = self.context['request']

        return request.build_absolute_uri(reverse('todo_api:attachment_upload',
                                                  args=[instance.id]))

    def get_task_list(self, instance):
        request = self.context['request']

        return request.build_absolute_uri(instance.task_list.get_absolute_rest_url())


class PartialTaskSerializer(TaskSerializer, UrlObjectSerializer, PartialObjectSerializer):
    class Meta(TaskSerializer.Meta):
        fields = ('title',
                  'created_by',
                  'assigned_to',
                  'created_date', 'due_date',
                  'completed', 'completed_date',
                  'url',
                  '_partial')


class TicketSerializer(TaskSerializer, UrlObjectSerializer, PartialObjectSerializer):
    attachment = Base64FileField(required=False)

    class Meta(TaskSerializer.Meta):
        fields = ('title', 'note',
                  'url',
                  'attachment',
                  '_partial')

    def create(self, validated_data):
        request = self.context['request']

        validated_data['task_list'] = TaskList.objects.get(slug=settings.TODO_DEFAULT_LIST_SLUG)
        validated_data['created_by'] = request.user
        validated_data['created_date'] = timezone.now()
        validated_data['assigned_to'] = User.objects.get(username=settings.TODO_DEFAULT_ASSIGNEE)

        attachment_file_data = validated_data.pop('attachment', None)

        task = super(TicketSerializer, self).create(validated_data)

        if attachment_file_data is not None:
            try:
                add_attachment_file(request, attachment_file_data, task)

            except Exception as e:
                raise serializers.ValidationError(str(e))

            else:
                task.refresh_from_db()

        return task


class TaskListSerializer(serializers.ModelSerializer, UrlObjectSerializer, PartialObjectSerializer):
    class Meta:
        model = TaskList
        fields = ('name',
                  'url',
                  '_partial')


class TaskListDetailSerializer(serializers.ModelSerializer, UrlObjectSerializer):
    tasks = serializers.SerializerMethodField(required=False)

    class Meta:
        model = TaskList
        fields = ('name',
                  'url',
                  'tasks')

    def get_tasks(self, instance):
        request = self.context['request']
        user = request.user

        if not staff_check(user):
            tasks = Task.objects.filter(is_active=True).filter(Q(created_by=user) | Q(assigned_to=user)).filter(task_list=instance)
        else:
            tasks = Task.objects.filter(is_active=True).filter(task_list=instance.id)

        return PartialTaskSerializer(tasks, many=True, context=self.context).data
