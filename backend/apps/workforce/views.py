from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView as BaseAPIView
from rest_framework.permissions import IsAuthenticated, BasePermission

CLIENT_ROLE_SLUGS = ("client", "client_portal")


def is_employee(user):
    return not (user.role and user.role.slug in CLIENT_ROLE_SLUGS)


class EmployeeOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_active and request.user.state != "suspended" and is_employee(request.user)

class APIView(BaseAPIView):
    permission_classes = [IsAuthenticated, EmployeeOnly]
from apps.accounts.models import User, Department, Role
from apps.delivery.models import Project, ProjectMember, Task
from .models import DailyLog, Thread, Message


def ceo(user):
    return user.is_superuser or bool(user.role and user.role.is_director)


def projects(user):
    qs = Project.objects.exclude(is_archived=True).exclude(state="closed")
    if ceo(user): return qs
    criterion = Q(members__user=user) | Q(manager=user) | Q(tasks__assignee=user)
    if user.is_department_head and user.department_id:
        criterion |= Q(members__user__department_id=user.department_id) | Q(tasks__assignee__department_id=user.department_id)
    return qs.filter(criterion).distinct()


def staff(user):
    qs = User.objects.filter(is_active=True).exclude(state="suspended").exclude(role__slug__in=CLIENT_ROLE_SLUGS)
    return qs if ceo(user) else qs.filter(department_id=user.department_id) if user.is_department_head and user.department_id else qs.filter(pk=user.pk)


def task_scope(user):
    qs = Task.objects.select_related("assignee", "project")
    return qs if ceo(user) else qs.filter(assignee__in=staff(user))


class TaskForm(serializers.Serializer):
    text = serializers.CharField(max_length=200)
    assignee = serializers.UUIDField()
    project = serializers.UUIDField()
    priority = serializers.ChoiceField(choices=["low", "normal", "high", "urgent"], default="normal")
    due_date = serializers.DateField(required=False, allow_null=True)


class LogForm(serializers.ModelSerializer):
    class Meta:
        model = DailyLog
        fields = ["id", "project", "date", "minutes", "summary"]
        read_only_fields = ["id"]
    def validate(self, data):
        if not projects(self.context["request"].user).filter(pk=data["project"].pk).exists():
            raise serializers.ValidationError("Choose one of your assigned projects.")
        if data["date"] > timezone.localdate(timezone=ZoneInfo("Africa/Nairobi")): raise serializers.ValidationError("Daily logs cannot be dated in the future.")
        if not 1 <= data["minutes"] <= 1440: raise serializers.ValidationError("Enter between 1 and 1440 minutes.")
        if not data["summary"].strip(): raise serializers.ValidationError("Describe the work you completed.")
        return data


class WorkspaceView(APIView):
    def get(self, request):
        user = request.user
        logs = DailyLog.objects.filter(user__in=staff(user)).select_related("user", "project")[:100]
        return Response({
            "can_assign": ceo(user) or user.is_department_head,
            "is_ceo": ceo(user), "employee_number": user.employee_number,
            "departments": list((Department.objects.all() if ceo(user) else Department.objects.filter(pk=user.department_id)).values("id", "label")),
            "projects": list(projects(user).values("id", "ref", "name", "stage", "completion")),
            "people": list(staff(user).values("id", "display_name", "employee_number")),
            "tasks": [{"id":t.id, "text":t.text, "done":t.done, "project":t.project.name, "assignee":t.assignee.display_name if t.assignee else "Unassigned", "can_complete":ceo(user) or user.is_department_head or t.assignee_id==user.id} for t in task_scope(user).order_by("done", "-created_at")[:200]],
            "logs": [{"id":l.id, "date":l.date, "minutes":l.minutes, "summary":l.summary, "person":l.user.display_name, "project":l.project.name} for l in logs],
        })
    def post(self, request):
        if not (ceo(request.user) or request.user.is_department_head): raise PermissionDenied("Only the CEO or a department head can assign work.")
        form = TaskForm(data=request.data); form.is_valid(raise_exception=True)
        person = get_object_or_404(staff(request.user), pk=form.validated_data["assignee"])
        project = get_object_or_404(projects(request.user), pk=form.validated_data["project"])
        with transaction.atomic():
            task = Task.objects.create(text=form.validated_data["text"], assignee=person, project=project, created_by=request.user, project_label=project.short_label[:20], priority=form.validated_data["priority"], due_date=form.validated_data.get("due_date"))
            ProjectMember.objects.get_or_create(project=project, user=person, defaults={"role_label":"Contributor"})
        return Response({"id":task.id}, status=201)


class CompleteView(APIView):
    def patch(self, request, pk):
        task = get_object_or_404(task_scope(request.user), pk=pk)
        from .collaboration import TaskUpdate, task_data
        form = TaskUpdate(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data
        if any(k in data for k in ["priority", "due_date"]) and not (ceo(request.user) or request.user.is_department_head):
            raise PermissionDenied("Your department head manages priorities and deadlines.")
        for key, value in data.items():
            setattr(task, key, value)
        task.save(update_fields=set(data) | {"updated_at"})
        return Response(task_data(task, request.user))



class LogsView(APIView):
    def post(self, request):
        form = LogForm(data=request.data, context={"request":request}); form.is_valid(raise_exception=True)
        form.save(user=request.user, created_by=request.user)
        return Response(form.data, status=201)


class MembershipView(APIView):
    def post(self, request):
        if not ceo(request.user): raise PermissionDenied("The CEO manages project membership.")
        form = TaskForm(data={**request.data, "text":"membership"}); form.is_valid(raise_exception=True)
        person = get_object_or_404(staff(request.user), pk=form.validated_data["assignee"])
        project = get_object_or_404(projects(request.user), pk=form.validated_data["project"])
        ProjectMember.objects.get_or_create(project=project,user=person,defaults={"role_label":"Contributor"})
        return Response({"detail":"Project membership saved."})


class SetupView(APIView):
    def get(self, request):
        if not ceo(request.user): raise PermissionDenied()
        return Response({"departments":list(Department.objects.values("id","label")), "roles":list(Role.objects.values("id","label"))})
