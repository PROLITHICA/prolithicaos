from django.db import models
from django.conf import settings
from apps.core.models import BaseModel
from .storage import private_chat_storage

class DailyLog(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey("delivery.Project", on_delete=models.PROTECT)
    date = models.DateField()
    minutes = models.PositiveIntegerField()
    summary = models.TextField(max_length=4000)
    class Meta:
        ordering = ["-date", "-created_at"]

class Thread(BaseModel):
    name = models.CharField(max_length=120, blank=True)
    direct_key = models.CharField(max_length=80, unique=True, null=True, blank=True)
    department = models.OneToOneField("accounts.Department", null=True, blank=True, on_delete=models.PROTECT, related_name="chat_channel")
    archived = models.BooleanField(default=False)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="chat_threads")

class Message(BaseModel):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=4000, blank=True)
    pinned = models.BooleanField(default=False, db_index=True)
    attachment = models.FileField(upload_to="%Y/%m", storage=private_chat_storage, blank=True)
    attachment_name = models.CharField(max_length=200, blank=True)
    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["thread", "-created_at", "-id"], name="chat_history_idx")]

class DailyReport(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="daily_reports")
    date = models.DateField(db_index=True)
    completed = models.TextField(max_length=4000)
    tomorrow = models.TextField(max_length=4000, blank=True)
    blockers = models.TextField(max_length=4000, blank=True)
    tasks = models.ManyToManyField("delivery.Task", blank=True, related_name="daily_reports")

    class Meta:
        ordering = ["-date", "-updated_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["user", "date"], name="one_daily_report_per_person")]
