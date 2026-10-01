"""Department channels, retained history, decisions and private attachments."""
import io
import zipfile
from pathlib import Path
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from apps.accounts.models import User, Department
from .models import Thread, Message
from .views import APIView, ceo, CLIENT_ROLE_SLUGS
from .collaboration import page_rows


def employees():
    return User.objects.filter(is_active=True).exclude(state="suspended").exclude(role__slug__in=CLIENT_ROLE_SLUGS)


def group_admins():
    return employees().filter(Q(is_superuser=True) | Q(role__is_director=True))


def visible_threads(user):
    direct = Q(direct_key__isnull=False, members=user)
    groups = Q(direct_key__isnull=True)
    if not ceo(user):
        groups &= Q(department_id=user.department_id) if user.department_id else Q(pk__in=[])
        groups |= Q(direct_key__isnull=True, department__isnull=True, members=user)
    return Thread.objects.filter(direct | groups).distinct()


def can_pin(user, thread):
    return not thread.direct_key and (ceo(user) or bool(user.is_department_head and user.department_id and thread.department_id == user.department_id))


def thread_data(thread, user):
    if thread.department_id:
        members = employees().filter(Q(department_id=thread.department_id) | Q(pk__in=group_admins()))
    else:
        members = list(thread.members.all())
        if not thread.direct_key:
            members = list({u.pk: u for u in members + list(group_admins())}.values())
    return {"id": thread.id, "name": thread.name if not thread.direct_key else ", ".join(u.display_name for u in members if u.pk != user.pk),
            "direct": bool(thread.direct_key), "department": thread.department_id, "archived": thread.archived,
            "can_manage": bool(not thread.direct_key and ceo(user)), "can_pin": can_pin(user, thread),
            "members": [{"id": u.id, "name": u.display_name, "admin": bool(not thread.direct_key and ceo(u))} for u in members]}


class ThreadForm(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False, default="")
    members = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=100)
    direct = serializers.BooleanField(default=False)
    def validate(self, data):
        ids = set(data["members"])
        ids.discard(self.context["request"].user.id)
        if not ids or employees().filter(pk__in=ids).count() != len(ids):
            raise serializers.ValidationError("Choose active employees.")
        if data["direct"] and len(ids) != 1:
            raise serializers.ValidationError("A private conversation has two participants.")
        if not data["direct"] and not data["name"].strip():
            raise serializers.ValidationError("Give the group a name.")
        data["members"] = ids
        return data


class ThreadsView(APIView):
    def get(self, request):
        departments = Department.objects.all() if ceo(request.user) else Department.objects.filter(pk=request.user.department_id)
        for department in departments:
            Thread.objects.get_or_create(department=department, defaults={"name": department.label, "created_by": request.user})
        threads = visible_threads(request.user).prefetch_related("members").order_by("archived", "-updated_at")
        return Response({"threads": [thread_data(t, request.user) for t in threads],
                         "people": list(employees().exclude(pk=request.user.pk).values("id", "display_name", "employee_number"))})
    def post(self, request):
        form = ThreadForm(data=request.data, context={"request": request})
        form.is_valid(raise_exception=True)
        data = form.validated_data
        with transaction.atomic():
            if data["direct"]:
                key = ":".join(sorted([str(request.user.id), str(next(iter(data["members"]))) ]))
                thread, _ = Thread.objects.get_or_create(direct_key=key, defaults={"created_by": request.user})
            else:
                thread = Thread.objects.create(name=data["name"], created_by=request.user)
            thread.members.add(request.user, *data["members"])
            if not data["direct"]:
                thread.members.add(*group_admins())
        return Response({"id": thread.id}, status=201)


class MessageForm(serializers.Serializer):
    body = serializers.CharField(max_length=4000, required=False, allow_blank=True, default="")
    file = serializers.FileField(required=False)
    def validate_file(self, file):
        if file.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Attachments must be 10 MB or smaller.")
        suffix = Path(file.name).suffix.lower()
        allowed = {".pdf", ".txt", ".csv", ".png", ".jpg", ".jpeg", ".docx", ".xlsx"}
        if suffix not in allowed:
            raise serializers.ValidationError("Use PDF, text, CSV, PNG, JPEG, DOCX or XLSX.")
        content = file.read()
        file.seek(0)
        valid = True
        if suffix == ".pdf": valid = content.startswith(b"%PDF-")
        elif suffix == ".png": valid = content.startswith(b"\x89PNG\r\n\x1a\n")
        elif suffix in {".jpg", ".jpeg"}: valid = content.startswith(b"\xff\xd8\xff")
        elif suffix in {".txt", ".csv"}:
            try:
                content.decode("utf-8")
                valid = b"\x00" not in content
            except UnicodeDecodeError: valid = False
        elif suffix in {".docx", ".xlsx"}:
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    names = archive.namelist()
                    valid = "[Content_Types].xml" in names and ("word/document.xml" if suffix == ".docx" else "xl/workbook.xml") in names
            except zipfile.BadZipFile: valid = False
        if not valid:
            raise serializers.ValidationError("File contents do not match the selected file type.")
        return file
    def validate(self, data):
        if not data.get("body", "").strip() and not data.get("file"):
            raise serializers.ValidationError("Write a message or attach a file.")
        return data


def message_data(message, user):
    return {"id": message.id, "body": message.body, "author": message.author.display_name,
            "created_at": message.created_at, "mine": message.author_id == user.id,
            "pinned": message.pinned, "attachment_name": message.attachment_name,
            "attachment_url": f"/workspace/messages/{message.id}/attachment/" if message.attachment else None}


class MessagesView(APIView):
    def get(self, request, pk):
        thread = get_object_or_404(visible_threads(request.user), pk=pk)
        qs = thread.messages.select_related("author").order_by("-created_at", "-id")
        if request.query_params.get("q", "").strip():
            qs = qs.filter(Q(body__icontains=request.query_params["q"].strip()[:200]) | Q(attachment_name__icontains=request.query_params["q"].strip()[:200]))
        if request.query_params.get("pinned") == "true":
            qs = qs.filter(pinned=True)
        # Preserve the legacy array contract for existing integrations.
        if "page" not in request.query_params:
            return Response([message_data(m, request.user) for m in reversed(list(qs[:200]))])
        rows, meta = page_rows(qs, request)
        return Response({**meta, "results": [message_data(m, request.user) for m in reversed(rows)],
                         "archived": thread.archived, "can_pin": can_pin(request.user, thread)})
    def post(self, request, pk):
        thread = get_object_or_404(visible_threads(request.user), pk=pk)
        if thread.archived:
            raise serializers.ValidationError("This conversation is archived and read-only.")
        form = MessageForm(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data
        attachment = data.get("file")
        message = Message.objects.create(thread=thread, author=request.user, body=data["body"], created_by=request.user,
                                         attachment=attachment or "", attachment_name=Path(attachment.name).name[:200] if attachment else "")
        thread.save(update_fields=["updated_at"])
        return Response({"id": message.id}, status=201)
    def patch(self, request, pk):
        thread = get_object_or_404(visible_threads(request.user), pk=pk)
        if thread.direct_key or not ceo(request.user):
            raise PermissionDenied("Only the CEO can manage company groups.")
        if "archived" in request.data:
            thread.archived = serializers.BooleanField().run_validation(request.data["archived"])
            thread.save(update_fields=["archived", "updated_at"])
            return Response({"detail": "Conversation updated."})
        if thread.department_id:
            raise serializers.ValidationError("Department membership follows employee department assignments.")
        form = ThreadForm(data={"name": request.data.get("name", thread.name), "members": request.data.get("members", []), "direct": False}, context={"request": request})
        form.is_valid(raise_exception=True)
        with transaction.atomic():
            thread.name = form.validated_data["name"]
            thread.save(update_fields=["name", "updated_at"])
            thread.members.set([request.user, *form.validated_data["members"], *group_admins()])
        return Response({"detail": "Group membership updated."})
    def delete(self, request, pk):
        thread = get_object_or_404(visible_threads(request.user), pk=pk)
        if thread.direct_key or not ceo(request.user):
            raise PermissionDenied("Only the CEO can archive a company group.")
        thread.archived = True
        thread.save(update_fields=["archived", "updated_at"])
        return Response(status=204)


class PinView(APIView):
    def patch(self, request, pk):
        message = get_object_or_404(Message.objects.filter(thread__in=visible_threads(request.user)).select_related("thread"), pk=pk)
        if not can_pin(request.user, message.thread):
            raise PermissionDenied("Only the department head or CEO can pin decisions.")
        if message.thread.archived:
            raise serializers.ValidationError("Archived decisions are read-only.")
        message.pinned = serializers.BooleanField().run_validation(request.data.get("pinned"))
        message.save(update_fields=["pinned", "updated_at"])
        return Response(message_data(message, request.user))


class AttachmentView(APIView):
    def get(self, request, pk):
        message = get_object_or_404(Message.objects.filter(thread__in=visible_threads(request.user)), pk=pk)
        if not message.attachment:
            raise serializers.ValidationError("This message has no attachment.")
        try:
            response = FileResponse(message.attachment.open("rb"), as_attachment=True, filename=message.attachment_name, content_type="application/octet-stream")
        except FileNotFoundError:
            from rest_framework.exceptions import NotFound
            raise NotFound("The attachment is unavailable. Contact your administrator.")
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response
