import email.utils
import logging
import os
import time

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.template.loader import render_to_string
from django.utils import timezone  # pai
from django.db.models import Q  # pai
from django.db import transaction  # pai
from django.utils.translation import gettext_lazy as _  # pai

from todo.defaults import defaults
from todo.models import Attachment, Comment, Task

from filer.models import File as FilerFile, Folder as FilerFolder  # pai

log = logging.getLogger(__name__)

if 'django_sso_app' in settings.INSTALLED_APPS:
    from django_sso_app.core.permissions import is_staff

    def staff_check(user):
        if defaults("TODO_STAFF_ONLY"):
            return is_staff(user)
        else:
            # If unset or False, allow all logged in users
            return True

else:
    def staff_check(user):
        """If TODO_STAFF_ONLY is set to True, limit view access to staff users only.
            # FIXME: More granular access control needed - see
            https://github.com/shacker/django-todo/issues/50
        """

        if defaults("TODO_STAFF_ONLY"):
            return user.is_staff
        else:
            # If unset or False, allow all logged in users
            return True


def user_can_read_task(task, user):
    # return task.task_list.group in user.groups.all() or user.is_superuser
    # pai
    if staff_check(user):
        return True
    else:
        return task.created_by == user or task.assigned_to == user or (task.assigned_to is None and
                                                                       task.task_list.group in user.groups.all())


def todo_get_backend(task):
    """Returns a mail backend for some task"""
    mail_backends = getattr(settings, "TODO_MAIL_BACKENDS", None)
    if mail_backends is None:
        return None

    task_backend = mail_backends[task.task_list.slug]
    if task_backend is None:
        return None

    return task_backend


def todo_get_mailer(user, task):
    """A mailer is a (from_address, backend) pair"""
    task_backend = todo_get_backend(task)
    if task_backend is None:
        return (None, mail.get_connection)

    from_address = getattr(task_backend, "from_address")
    from_address = email.utils.formataddr((user.username, from_address))
    return (from_address, task_backend)


def todo_send_mail(user, task, subject, body, recip_list):
    """Send an email attached to task, triggered by user"""
    references = Comment.objects.filter(task=task).only("email_message_id")
    references = (ref.email_message_id for ref in references)
    references = " ".join(filter(bool, references))

    from_address, backend = todo_get_mailer(user, task)
    message_hash = hash((subject, body, from_address, frozenset(recip_list), references))

    message_id = (
        # the task_id enables attaching back notification answers
        "<notif-{task_id}."
        # the message hash / epoch pair enables deduplication
        "{message_hash:x}."
        "{epoch}@django-todo>"
    ).format(
        task_id=task.pk,
        # avoid the -hexstring case (hashes can be negative)
        message_hash=abs(message_hash),
        epoch=int(time.time()),
    )

    # the thread message id is used as a common denominator between all
    # notifications for some task. This message doesn't actually exist,
    # it's just there to make threading possible
    thread_message_id = "<thread-{}@django-todo>".format(task.pk)
    references = "{} {}".format(references, thread_message_id)

    with backend() as connection:
        message = mail.EmailMessage(
            subject,
            body,
            from_address,
            recip_list,
            [],  # Bcc
            headers={
                **getattr(backend, "headers", {}),
                "Message-ID": message_id,
                "References": references,
                "In-reply-to": thread_message_id,
            },
            connection=connection,
        )
        message.send()


def send_notify_mail(new_task):
    """
    Send email to assignee if task is assigned to someone other than submittor.
    Unassigned tasks should not try to notify.
    """

    if new_task.assigned_to == new_task.created_by:
        return

    current_site = Site.objects.get_current()
    subject = render_to_string("todo/email/assigned_subject.txt", {"task": new_task})
    body = render_to_string(
        "todo/email/assigned_body.txt", {"task": new_task, "site": current_site}
    )

    recip_list = [new_task.assigned_to.email]
    todo_send_mail(new_task.created_by, new_task, subject, body, recip_list)


def send_email_to_thread_participants(task, msg_body, user, subject=None):
    """Notify all previous commentors on a Task about a new comment."""

    current_site = Site.objects.get_current()
    email_subject = subject
    if not subject:
        subject = render_to_string("todo/email/assigned_subject.txt", {"task": task})

    email_body = render_to_string(
        "todo/email/newcomment_body.txt",
        {"task": task, "body": msg_body, "site": current_site, "user": user},
    )

    # Get all thread participants
    commenters = Comment.objects.filter(task=task)
    recip_list = set(ca.author.email for ca in commenters if ca.author is not None)
    for related_user in (task.created_by, task.assigned_to):
        if related_user is not None:
            recip_list.add(related_user.email)
    recip_list = list(m for m in recip_list if m)

    todo_send_mail(user, task, email_subject, email_body, recip_list)


def check_previous_task_lists_completeness(task_list, procedure_uuid=None):
    """
    Checks previous task list completion status
    """
    if task_list is not None and task_list.previous_task_list is not None:
        return task_list.previous_task_list.all_tasks_completed(procedure_uuid) and \
               check_previous_task_lists_completeness(task_list.previous_task_list, procedure_uuid=procedure_uuid)
    else:
        return True


def set_all_next_task_lists_not_completed(task_list, procedure_uuid=None):
    """
    Set completion status False for next task lists
    """
    for tl in task_list.__class__.objects.filter(is_active=True).filter(previous_task_list=task_list):
        tl.set_all_tasks_not_completed(procedure_uuid)

        set_all_next_task_lists_not_completed(tl, procedure_uuid)


@transaction.atomic
def toggle_task_completed(task_id: int, user=None) -> bool:
    """Toggle the `completed` bool on Task from True to False or vice versa."""
    try:
        task = Task.objects.get(id=task_id)

        # task respects_priority checks
        if task.completed:
            if task.respects_priority:
                next_completed_tasks = Task.objects.filter(is_active=True) \
                    .filter(task_list=task.task_list) \
                    .filter(procedure_uuid=task.procedure_uuid) \
                    .filter(priority__gt=task.priority, completed=True)
                for t in next_completed_tasks:
                    # reopen next tasks
                    # t.completed_by = None  # keep track
                    t.completed = False
                    t.save()

                # toggle next task_list's completion status
                set_all_next_task_lists_not_completed(task.task_list, task.procedure_uuid)

        else:
            if task.respects_priority:
                previous_incomplete_tasks_count = Task.objects.filter(is_active=True) \
                    .filter(task_list=task.task_list) \
                    .filter(procedure_uuid=task.procedure_uuid) \
                    .filter(priority__lt=task.priority, completed=False) \
                    .count()
                if previous_incomplete_tasks_count > 0:
                    log.info('Must complete {} previous tasks'.format(previous_incomplete_tasks_count))
                    raise Exception(_('Must complete previous tasks.'))
                    # return False
                else:
                    if not check_previous_task_lists_completeness(task.task_list, task.procedure_uuid):
                        log.info(_('Must complete previous task lists.'))
                        # return False
                        raise Exception(_('Must complete previous task lists.'))

        # toggle value
        task.completed = not task.completed

        if task.completed:
            if user is not None:
                task.completed_by = user
        # keep track
        # else:
        #     task.completed_by = None

        task.save()

        return True

    except Task.DoesNotExist:
        log.info(f"Task {task_id} not found.")
        # return False
        raise Exception(_('Not found.'))


def remove_attachment_file(attachment_id: int) -> bool:
    """Delete an Attachment object and its corresponding file from the filesystem."""
    try:
        attachment = Attachment.objects.get(id=attachment_id)
        if attachment.file:
            if os.path.isfile(attachment.file.path):
                os.remove(attachment.file.path)

        attachment.delete()
        return True

    except Attachment.DoesNotExist:
        log.info(f"Attachment {attachment_id} not found.")
        return False


# pai
@transaction.atomic
def add_attachment_file(request, file_data, task):
    if file_data.size > defaults("TODO_MAXIMUM_ATTACHMENT_SIZE"):
        raise Exception(_("File exceeds maximum attachment size."))

    name, extension = os.path.splitext(file_data.name)

    if extension not in defaults("TODO_LIMIT_FILE_ATTACHMENTS"):
        raise Exception(_("This site does not allow upload of '{}' files.").format(extension))

    user = request.user  # !!

    if 'django_sso_app' in settings.INSTALLED_APPS:
        user_id = user.sso_id
    else:
        user_id = user.username

    created_attachment = Attachment.objects.create(
        task=task, added_by=user, timestamp=timezone.now(), file=file_data
    )

    created_attachment_task = created_attachment.task
    created_attachment_task_list = created_attachment_task.task_list

    # creating filer folders
    users_folder, _created = FilerFolder.objects.get_or_create(name='users')
    user_folder, _created = FilerFolder.objects.get_or_create(name=user_id,
                                                              parent=users_folder,
                                                              owner=user)
    user_tasks_folder, _created = FilerFolder.objects.get_or_create(name='tasks',
                                                                    parent=user_folder)
    user_tasklist_folder, _created = FilerFolder.objects.get_or_create(name=created_attachment_task_list.slug,
                                                                       parent=user_tasks_folder)
    user_tasklist_task_folder, _created = FilerFolder.objects.get_or_create(name=str(created_attachment_task.id),
                                                                            parent=user_tasklist_folder)

    # creating filer file
    filer_file = FilerFile()
    filer_file.file = created_attachment.file
    filer_file.owner = user
    filer_file.original_filename = os.path.basename(created_attachment.file.name)
    filer_file.folder = user_tasklist_task_folder

    filer_file.save()

    # update attachment
    created_attachment.filer_file = filer_file
    created_attachment.save()


def get_user_task_list_tasks(task_list, user, completed=None):
    tasks = task_list.task_set\
        .filter(is_active=True)\
        .filter(Q(created_by=user) |
                Q(assigned_to=user) |
                Q(assigned_to__isnull=True, task_list__group__in=user.groups.all())) \
        .prefetch_related('created_by', 'assigned_to')

    if completed is not None:
        tasks = tasks.filter(completed=completed)

    return tasks


def get_task_list_tasks(task_list, user=None, completed=None):
    if user is not None:
        if staff_check(user):
            tasks = task_list.task_set.all()
        else:
            tasks = get_user_task_list_tasks(task_list, user)
    else:
        tasks = task_list.task_set.all()

    if completed is not None:
        tasks = tasks.filter(completed=completed)

    return tasks


def user_can_toggle_task_done(user, task):
    if staff_check(user):
        return True
    else:
        if task.assigned_to is None:
            if task.task_list.group in user.groups.all():
                return True
            else:
                return False
        else:
            return task.assigned_to == user


def user_can_view_task_list(user, task_list):
    if staff_check(user):
        return True
    else:
        return task_list.group in user.groups.all()


def user_can_delete_task(user, task):
    if staff_check(user):
        return True
    else:
        # task has no procedure and has been created by user
        return task.procedure_uuid is None and \
               task.created_by == user
