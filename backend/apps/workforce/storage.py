"""Chat uploads live outside public MEDIA_ROOT and require an authenticated download."""
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage

class PrivateChatStorage(FileSystemStorage):
    @property
    def base_location(self):
        return getattr(settings, "PRIVATE_CHAT_ROOT", settings.BASE_DIR / "private_uploads")

    @property
    def location(self):
        return os.path.abspath(self.base_location)


def private_chat_storage():
    return PrivateChatStorage()
