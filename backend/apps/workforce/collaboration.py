"""Scoped task boards and daily reports for the company workspace."""
from zoneinfo import ZoneInfo
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from apps.delivery.models import Task
from apps.accounts.models import Department
from .models import DailyReport
from .views import APIView, task_scope, staff, ceo


def local_now():
    return timezone.localtime(timezone.now(), ZoneInfo("Africa/Nairobi"))


def page_rows(queryset, request, size=50):
    form = PageForm(data=request.query_params)
    form.is_valid(raise_exception=True)
    page = form.validated_data["page"]
    count = queryset.count()
    start = (page - 1) * size
    return list(queryset[start:start + size]), {"count": count, "page": page, "has_next": start + size < count}


class PageForm(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, max_value=100000, default=1)


class TaskUpdate(serializers.Serializer):
    status = serializers.ChoiceField(choices=["todo", "in_progress", "blocked", "done"], required=False)
    done = serializers.BooleanField(required=False)
    priority = serializers.ChoiceField(choices=["low", "normal", "high", "urgent"], required=False)
    due_date = serializers.DateField(required=False, allow_null=True)
    def validate(self, data):
        if not data:
            raise serializers.ValidationError("Provide a status, priority or deadline.")
        if "status" in data and "done" in data and data["done"] != (data["status"] == "done"):
            raise serializers.ValidationError("Status and completion must agree.")
        return data


def task_data(task, user):
    return {"id": task.id, "text": task.text, "done": task.done, "status": task.status,
            "priority": task.priority, "due_date": task.due_date, "project": task.project.name,
            "project_id": task.project_id, "assignee_id": task.assignee_id,
            "department": task.assignee.department_id if task.assignee else None,
            "assignee": task.assignee.display_name if task.assignee else "Unassigned",
            "can_complete": ceo(user) or user.is_department_head or task.assignee_id == user.id}


class TasksView(APIView):
    def get(self, request):
        qs = task_scope(request.user).select_related("assignee__department").order_by("done", "due_date", "-created_at", "id")
        for key, field in [("department", "assignee__department_id"), ("project", "project_id"), ("assignee", "assignee_id")]:
            if request.query_params.get(key):
                value = serializers.UUIDField().run_validation(request.query_params[key])
                qs = qs.filter(**{field: value})
        for key in ["status", "priority"]:
            if request.query_params.get(key):
                value = TaskUpdate().fields[key].run_validation(request.query_params[key])
                qs = qs.filter(**{key: value})
        if request.query_params.get("due_before"):
            value = serializers.DateField().run_validation(request.query_params["due_before"])
            qs = qs.filter(due_date__lte=value)
        if request.query_params.get("q", "").strip():
            qs = qs.filter(text__icontains=request.query_params["q"].strip()[:200])
        rows, meta = page_rows(qs, request)
        return Response({**meta, "results": [task_data(t, request.user) for t in rows]})


class ReportForm(serializers.ModelSerializer):
    tasks = serializers.ListField(child=serializers.UUIDField(), max_length=100, required=False, default=list)
    class Meta:
        model = DailyReport
        fields = ["date", "completed", "tomorrow", "blockers", "tasks"]
    def validate_date(self, value):
        if value > local_now().date():
            raise serializers.ValidationError("Reports cannot be dated in the future.")
        return value
    def validate_completed(self, value):
        if not value.strip():
            raise serializers.ValidationError("Describe today's work.")
        return value.strip()
    def validate_tasks(self, values):
        ids = set(values)
        if task_scope(self.context["request"].user).filter(pk__in=ids).count() != len(ids):
            raise serializers.ValidationError("Choose tasks in your scope.")
        return list(ids)


def report_data(report):
    return {"id": report.id, "user_id": report.user_id, "person": report.user.display_name,
            "department": report.user.department.label if report.user.department else "Unassigned",
            "date": report.date, "completed": report.completed, "tomorrow": report.tomorrow,
            "blockers": report.blockers, "updated_at": report.updated_at,
            "tasks": [{"id": t.id, "text": t.text} for t in report.tasks.all()]}


class ReportsView(APIView):
    def get(self, request):
        day = serializers.DateField().run_validation(request.query_params.get("date", str(local_now().date())))
        people = staff(request.user)
        if request.query_params.get("department"):
            department = serializers.UUIDField().run_validation(request.query_params["department"])
            people = people.filter(department_id=department)
        qs = DailyReport.objects.filter(user__in=people, date=day).select_related("user__department").prefetch_related("tasks")
        submitted_ids = qs.values_list("user_id", flat=True)
        missing = people.exclude(pk__in=submitted_ids) if day.weekday() < 5 else people.none()
        own = DailyReport.objects.filter(user=request.user, date=day).select_related("user__department").prefetch_related("tasks").first()
        rows, meta = page_rows(qs, request)
        now = local_now()
        return Response({**meta, "results": [report_data(r) for r in rows], "submitted": qs.count(),
                         "expected": people.count() if day.weekday() < 5 else 0,
                         "missing": list(missing.order_by("display_name").values("id", "display_name", "employee_number")),
                         "blocker_count": qs.exclude(blockers="").count(), "date": day,
                         "own_report": report_data(own) if own else None,
                         "reminder": day == now.date() and day.weekday() < 5 and now.hour >= 16 and not own,
                         "can_manage": ceo(request.user) or request.user.is_department_head,
                         "departments": list((Department.objects.all() if ceo(request.user) else Department.objects.filter(pk=request.user.department_id)).values("id", "label"))})
    def post(self, request):
        form = ReportForm(data=request.data, context={"request": request})
        form.is_valid(raise_exception=True)
        data = dict(form.validated_data)
        tasks = data.pop("tasks")
        day = data.pop("date")
        with transaction.atomic():
            report, created = DailyReport.objects.update_or_create(user=request.user, date=day, defaults=data)
            if created:
                report.created_by = request.user
                report.save(update_fields=["created_by"])
            report.tasks.set(tasks)
        return Response(report_data(report), status=201 if created else 200)
