from django.apps import AppConfig


class TodoConfig(AppConfig):
    name = 'todo'

    def ready(self):
        try:
            from . import signals  # noqa F401

        except ImportError:
            pass
