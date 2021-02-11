import csv
import datetime

from django.contrib import admin
from django.http import HttpResponse
from django.conf import settings
from django.utils.translation import gettext_lazy as _  # pai

from todo.models import Attachment, Comment, Task, TaskList


def export_to_csv(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    content_disposition = f"attachment; filename={opts.verbose_name}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = content_disposition
    writer = csv.writer(response)
    fields = [
        field for field in opts.get_fields() if not (field.many_to_many and not field.one_to_many)
    ]
    # Write a first row with header information
    writer.writerow([field.verbose_name for field in fields])
    # Write data rows
    for obj in queryset:
        data_row = []
        for field in fields:
            value = getattr(obj, field.name)
            if isinstance(value, datetime.datetime):
                value = value.strftime("%d/%m/%Y")
            data_row.append(value)
        writer.writerow(data_row)
    return response


export_to_csv.short_description = _("Export to CSV")


class TaskListAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "group", "previous_task_list", "created_at", "is_active")


class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "created_at", "task_list", "completed", "priority", "due_date", "is_active", "assigned_to", "procedure_uuid")
    list_filter = ("task_list",)
    ordering = ("priority",)
    search_fields = ("title", "procedure_uuid")
    actions = [export_to_csv]


class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "created_at", "snippet")


class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("task", "added_by", "created_at", "file")
    autocomplete_fields = ["added_by", "task"]


admin.site.register(TaskList, TaskListAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Attachment, AttachmentAdmin)


# pai
from django.contrib.admin.sites import NotRegistered

try:
    # disable filer unwanted features
    from filer.models import ThumbnailOption, FolderPermission

    admin.site.unregister(ThumbnailOption)
    admin.site.unregister(FolderPermission)
except NotRegistered:
    pass
