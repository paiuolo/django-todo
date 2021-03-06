from __future__ import unicode_literals

# import datetime  # pai
import os
import textwrap

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import DEFAULT_DB_ALIAS, models
from django.db.transaction import Atomic, get_connection
from django.urls import reverse
from django.utils.translation import gettext_lazy as _  # pai
from django.utils import timezone

from filer.fields.file import FilerFileField  # pai

from .storage import custom_fs  # pai


def now():
    """
    Returns an aware or naive datetime.datetime, depending on settings.USE_TZ.
    """
    return timezone.now()


def get_attachment_upload_dir(instance, filename):
    """Determine upload dir for task attachment files.
    """
    # pai
    # return "/".join(["tasks", "attachments", str(instance.task.id), filename])

    instance_class_name = instance.__class__.__name__
    if instance_class_name == 'Attachment':
        instance_user = instance.added_by
    else:
        instance_user = instance.user

    if 'django_sso_app' in settings.INSTALLED_APPS:
        # file will be uploaded to PRIVATE_ROOT/users/<user__sso_id>/<upload__upload_type/<filename>
        user_id = instance_user.sso_id
    else:
        user_id = instance_user.username

    return os.path.sep.join(['users',
                             user_id,
                             'tasks',
                             str(instance.task.task_list.slug),
                             str(instance.task.id),
                             filename])


class LockedAtomicTransaction(Atomic):
    """
    modified from https://stackoverflow.com/a/41831049
    this is needed for safely merging

    Does a atomic transaction, but also locks the entire table for any transactions, for the duration of this
    transaction. Although this is the only way to avoid concurrency issues in certain situations, it should be used with
    caution, since it has impacts on performance, for obvious reasons...
    """

    def __init__(self, *models, using=None, savepoint=None):
        if using is None:
            using = DEFAULT_DB_ALIAS
        super().__init__(using, savepoint)
        self.models = models

    def __enter__(self):
        super(LockedAtomicTransaction, self).__enter__()

        # Make sure not to lock, when sqlite is used, or you'll run into problems while running tests!!!
        if settings.DATABASES[self.using]["ENGINE"] != "django.db.backends.sqlite3":
            cursor = None
            try:
                cursor = get_connection(self.using).cursor()
                for model in self.models:
                    cursor.execute(
                        "LOCK TABLE {table_name}".format(table_name=model._meta.db_table)
                    )
            finally:
                if cursor and not cursor.closed:
                    cursor.close()


class TaskList(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('name'))  # pai
    slug = models.SlugField(default="", verbose_name=_('slug'), max_length=255)
    group = models.ForeignKey(Group, verbose_name=_('group'), on_delete=models.CASCADE)

    is_active = models.BooleanField(verbose_name=_('is active'), default=True)  # pai

    previous_task_list = models.ForeignKey('self', verbose_name=_('previous task list'),
                                           on_delete=models.SET_NULL, null=True, blank=True)  # pai

    created_at = models.DateTimeField(verbose_name=_('created at'), default=now, editable=False)  # pai

    def __str__(self):
        ret = self.name

        if not self.is_active:
            ret += ' [inactive]'

        return ret

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Task Lists"

        # Prevents (at the database level) creation of two lists with the same slug in the same group
        unique_together = ("group", "slug")

    # pai
    def get_relative_rest_url(self):
        return reverse("todo_api:list_detail", args=[self.pk])

    # pai
    def set_all_tasks_completed(self, procedure_uuid=None):
        """
        Set completion status to True for all tasks
        """
        for t in self.task_set.filter(completed=False, procedure_uuid=procedure_uuid):
            t.completed = True
            t.save()

    def set_all_tasks_not_completed(self, procedure_uuid=None):
        """
        Set completion status to False for all tasks
        """
        for t in self.task_set.filter(completed=True, procedure_uuid=procedure_uuid):
            t.completed = False
            t.save()

    def all_tasks_completed(self, procedure_uuid=None):
        """
        Tells if all tasks are completed
        """
        return self.task_set.filter(completed=True, procedure_uuid=procedure_uuid).count() == \
               self.task_set.filter(procedure_uuid=procedure_uuid).count()

    def get_last_completed_task(self, procedure_uuid=None):
        """
        Returns last completed task
        """
        return self.task_set.filter(completed=True, procedure_uuid=procedure_uuid).order_by('-completed_date').first()


class Task(models.Model):
    title = models.CharField(max_length=255, verbose_name=_('title'))
    task_list = models.ForeignKey(TaskList, verbose_name=_('task list'), on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(verbose_name=_('created at'), default=now, editable=False)  # pai
    updated_at = models.DateTimeField(verbose_name=_('updated at'), null=True, blank=True, editable=False)  # pai
    due_date = models.DateTimeField(verbose_name=_('due date'), blank=True, null=True)  # pai
    completed = models.BooleanField(verbose_name=_('completed'), default=False)
    completed_date = models.DateTimeField(verbose_name=_('completed date'), blank=True, null=True)  # pai
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('created by'),
        null=True,
        blank=True,
        related_name="todo_created_by",
        on_delete=models.CASCADE,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('assigned to'),
        blank=True,
        null=True,
        related_name="todo_assigned_to",
        on_delete=models.CASCADE,
    )
    note = models.TextField(verbose_name=_('note'), blank=True, null=True)
    priority = models.PositiveIntegerField(verbose_name=_('priority'), blank=True, null=True)

    is_active = models.BooleanField(verbose_name=_('is active'), default=True)  # pai

    procedure_uuid = models.CharField(max_length=36, null=True, blank=True, db_index=True)  # pai

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('completed by'),
        blank=True,
        null=True,
        related_name="todo_completed_by",
        on_delete=models.SET_NULL,
    )  # pai

    respects_priority = models.BooleanField(verbose_name=_('respects priority'), default=False)  # pai

    # on_complete_notify = models ...

    class Meta:
        ordering = ["procedure_uuid", "priority", "created_at"]

    # Has due date for an instance of this object passed?
    def overdue_status(self):
        "Returns whether the Tasks's due date has passed or not."
        #if self.due_date and datetime.date.today() > self.due_date:  # pai
        if self.due_date and now() > self.due_date:  # pai
            return True

    def __str__(self):
        ret = self.title
        if not self.is_active:
            ret += ' [inactive]'

        return ret

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.updated_at = now()
        return super(Task, self).save(*args, **kwargs)

    def get_relative_url(self):
        return reverse("todo:task_detail", kwargs={"task_id": self.id})

    # pai
    def get_relative_rest_url(self):
        return reverse("todo_api:task_detail", args=[self.pk])

    # pai
    """
    # Auto-set the Task creation / completed date
    def save(self, **kwargs):
        # If Task is being marked complete, set the completed_date
        if self.completed:
            self.completed_date = now()
        super(Task, self).save()
    """

    def merge_into(self, merge_target):
        if merge_target.pk == self.pk:
            raise ValueError("can't merge a task with self")

        # lock the comments to avoid concurrent additions of comments after the
        # update request. these comments would be irremediably lost because of
        # the cascade clause
        with LockedAtomicTransaction(Comment):
            Comment.objects.filter(task=self).update(task=merge_target)
            self.delete()


class Comment(models.Model):
    """
    Not using Django's built-in comments because we want to be able to save
    a comment and change task details at the same time. Rolling our own since it's easy.
    """

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('author'), on_delete=models.CASCADE, blank=True, null=True
    )
    task = models.ForeignKey(Task, verbose_name=_('task'), on_delete=models.CASCADE)
    created_at = models.DateTimeField(verbose_name=_('date'), default=now, editable=False)  # pai
    email_from = models.CharField(verbose_name=_('email from'), max_length=320, blank=True, null=True)
    email_message_id = models.CharField(verbose_name=_('email message id'), max_length=255, blank=True, null=True)

    body = models.TextField(verbose_name=_('body'), blank=True)

    class Meta:
        # an email should only appear once per task
        unique_together = ("task", "email_message_id")

    @property
    def author_text(self):
        if self.author is not None:
            return str(self.author)

        assert self.email_message_id is not None
        return str(self.email_from)

    @property
    def snippet(self):
        body_snippet = textwrap.shorten(self.body, width=35, placeholder="...")
        # Define here rather than in __str__ so we can use it in the admin list_display
        return "{author} - {snippet}...".format(author=self.author_text, snippet=body_snippet)

    def __str__(self):
        return self.snippet


class Attachment(models.Model):
    """
    Defines a generic file attachment for use in M2M relation with Task.
    """

    task = models.ForeignKey(Task, verbose_name=_('task'), on_delete=models.CASCADE)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('added by'), on_delete=models.CASCADE)
    created_at = models.DateTimeField(verbose_name=_('date'), default=now, editable=False)  # pai
    # pai
    # file = models.FileField(upload_to=get_attachment_upload_dir, max_length=255)
    file = models.FileField(storage=custom_fs,
                            upload_to=get_attachment_upload_dir,
                            max_length=255)

    filer_file = FilerFileField(null=True,
                                blank=True,
                                on_delete=models.SET_NULL)

    def filename(self):
        return os.path.basename(self.file.name)

    def extension(self):
        name, extension = os.path.splitext(self.file.name)
        return extension

    def __str__(self):
        return f"{self.task.id} - {self.file.name}"
