from django.urls import path
from .views import WorkspaceView, CompleteView, LogsView, SetupView, MembershipView
from .collaboration import TasksView, ReportsView
from .chat import ThreadsView, MessagesView, PinView, AttachmentView

urlpatterns = [
    path("", WorkspaceView.as_view()),
    path("tasks/", TasksView.as_view()),
    path("tasks/<uuid:pk>/", CompleteView.as_view()),
    path("logs/", LogsView.as_view()),
    path("reports/", ReportsView.as_view()),
    path("threads/", ThreadsView.as_view()),
    path("threads/<uuid:pk>/messages/", MessagesView.as_view()),
    path("messages/<uuid:pk>/", PinView.as_view()),
    path("messages/<uuid:pk>/attachment/", AttachmentView.as_view()),
    path("setup/", SetupView.as_view()),
    path("memberships/", MembershipView.as_view()),
]
