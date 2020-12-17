import os

from django.conf import settings
from django.utils.functional import cached_property

from filer.storage import PrivateFileSystemStorage as FilerPrivateFileSystemStorage


class PrivateFileSystemStorage(FilerPrivateFileSystemStorage):
    @cached_property
    def base_location(self):
        return self._value_or_setting(self._location, settings.PRIVATE_ROOT)

    @cached_property
    def location(self):
        return os.path.abspath(self.base_location)

    @cached_property
    def base_url(self):
        if self._base_url is not None and not self._base_url.endswith('/'):
            self._base_url += '/'
        return self._value_or_setting(self._base_url, '/private/')


# storage instance
custom_fs = PrivateFileSystemStorage()
