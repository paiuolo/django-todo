# Generated by Django 2.2.17 on 2021-02-03 12:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import todo.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('todo', '0012_filer_file_20201217_1211'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='task',
            options={'ordering': ['procedure_uuid', 'priority', 'created_at']},
        ),
        migrations.RemoveField(
            model_name='attachment',
            name='timestamp',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='date',
        ),
        migrations.RemoveField(
            model_name='task',
            name='created_date',
        ),
        migrations.AddField(
            model_name='attachment',
            name='created_at',
            field=models.DateTimeField(default=todo.models.now, editable=False, verbose_name='date'),
        ),
        migrations.AddField(
            model_name='comment',
            name='created_at',
            field=models.DateTimeField(default=todo.models.now, editable=False, verbose_name='date'),
        ),
        migrations.AddField(
            model_name='task',
            name='completed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='todo_completed_by', to=settings.AUTH_USER_MODEL, verbose_name='completed by'),
        ),
        migrations.AddField(
            model_name='task',
            name='created_at',
            field=models.DateTimeField(default=todo.models.now, editable=False, verbose_name='created at'),
        ),
        migrations.AddField(
            model_name='task',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='is active'),
        ),
        migrations.AddField(
            model_name='task',
            name='procedure_uuid',
            field=models.CharField(blank=True, db_index=True, max_length=36, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='respects_priority',
            field=models.BooleanField(default=False, verbose_name='respects priority'),
        ),
        migrations.AddField(
            model_name='task',
            name='updated_at',
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='updated at'),
        ),
        migrations.AddField(
            model_name='tasklist',
            name='created_at',
            field=models.DateTimeField(default=todo.models.now, editable=False, verbose_name='created at'),
        ),
        migrations.AddField(
            model_name='tasklist',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='is active'),
        ),
        migrations.AddField(
            model_name='tasklist',
            name='previous_task_list',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='todo.TaskList', verbose_name='previous task list'),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='added_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='added by'),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='todo.Task', verbose_name='task'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='author',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='author'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='body',
            field=models.TextField(blank=True, verbose_name='body'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='email_from',
            field=models.CharField(blank=True, max_length=320, null=True, verbose_name='email from'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='email_message_id',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='email message id'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='todo.Task', verbose_name='task'),
        ),
        migrations.AlterField(
            model_name='task',
            name='assigned_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='todo_assigned_to', to=settings.AUTH_USER_MODEL, verbose_name='assigned to'),
        ),
        migrations.AlterField(
            model_name='task',
            name='completed',
            field=models.BooleanField(default=False, verbose_name='completed'),
        ),
        migrations.AlterField(
            model_name='task',
            name='completed_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='completed date'),
        ),
        migrations.AlterField(
            model_name='task',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='todo_created_by', to=settings.AUTH_USER_MODEL, verbose_name='created by'),
        ),
        migrations.AlterField(
            model_name='task',
            name='due_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='due date'),
        ),
        migrations.AlterField(
            model_name='task',
            name='note',
            field=models.TextField(blank=True, null=True, verbose_name='note'),
        ),
        migrations.AlterField(
            model_name='task',
            name='priority',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='priority'),
        ),
        migrations.AlterField(
            model_name='task',
            name='task_list',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='todo.TaskList', verbose_name='task list'),
        ),
        migrations.AlterField(
            model_name='task',
            name='title',
            field=models.CharField(max_length=255, verbose_name='title'),
        ),
        migrations.AlterField(
            model_name='tasklist',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.Group', verbose_name='group'),
        ),
        migrations.AlterField(
            model_name='tasklist',
            name='name',
            field=models.CharField(max_length=255, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='tasklist',
            name='slug',
            field=models.SlugField(default='', max_length=255, verbose_name='slug'),
        ),
    ]
