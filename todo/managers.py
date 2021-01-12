from django.db import models


class ActiveModelsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True, is_scaffold=False)
