"""Delivery: projects, phases, milestones, requirements, tasks, risks, closure and support.

Every string the design renders is stored, so the screens are rebuilt from rows rather
than re-typed in the client. Cross-app references are string references (SPEC).
"""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel, RefModel, TagClass

# The design's four ink values (renderVals line 2264).
INK = "#111"
MAGENTA = "#111111"
CYAN = "#3d3d3d"
MUTED = "#6b6b6b"

PHASE_NAMES = ["Discovery", "Core build", "Integration", "Rollout", "Support handover"]


class Project(RefModel):
    ref_prefix = "PRJ"
    ref_digits = 3

    HEALTH = [
        ("Healthy", "Healthy"),
        ("Watch", "Watch"),
        ("At risk", "At risk"),
        ("Closed", "Closed"),
    ]
    STATE = [
        ("active", "Active"),
        ("closing", "Closing"),
        ("closed", "Closed"),
        ("support", "In support"),
    ]

    is_archived = models.BooleanField(default=False, db_index=True)
    name = models.CharField(max_length=120)
    full_name = models.CharField(max_length=200, blank=True)
    short_label = models.CharField(max_length=60, blank=True, help_text="Milestone register label")
    tag_label = models.CharField(max_length=20, blank=True, help_text="Task chip label")

    organisation = models.ForeignKey(
        "crm.Organisation", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="projects",
    )
    client_label = models.CharField(max_length=120)
    contract = models.ForeignKey(
        "crm.Contract", null=True, blank=True, on_delete=models.SET_NULL, related_name="projects",
    )
    contract_ref = models.CharField(max_length=32, blank=True)

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="managed_projects",
    )
    manager_name = models.CharField(max_length=80, blank=True)

    stage = models.CharField(max_length=40, default="Discovery")
    phase_index = models.PositiveSmallIntegerField(default=0)
    completion = models.PositiveSmallIntegerField(default=0)

    contract_value = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    contract_value_note = models.CharField(max_length=80, blank=True)
    invoiced = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    received = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    budget_planned = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    budget_spent = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    budget_used_pct = models.PositiveSmallIntegerField(default=0)

    margin_actual = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    margin_planned = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    margin_forecast = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    margin_note = models.CharField(max_length=200, blank=True)

    health = models.CharField(max_length=20, choices=HEALTH, default="Healthy")
    tag_class = models.CharField(max_length=20, choices=TagClass.choices, default=TagClass.ACCENT)
    state = models.CharField(max_length=12, choices=STATE, default="active")

    margin_series = models.JSONField(default=dict, blank=True)
    cost_series = models.JSONField(default=dict, blank=True)

    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.ref} · {self.name}"

    @staticmethod
    def health_for(margin_actual):
        """Health follows the margin unless someone sets it deliberately."""
        margin = float(margin_actual or 0)
        if margin < 25:
            return "At risk", TagClass.ACCENT_2
        if margin < 32:
            return "Watch", TagClass.OUTLINE
        return "Healthy", TagClass.ACCENT

    @property
    def phase_label(self):
        return f"stage {self.phase_index + 1} of {len(PHASE_NAMES)} · {PHASE_NAMES[self.phase_index]}"

    @property
    def margin_col(self):
        return MAGENTA if self.health == "At risk" else INK

    @property
    def budget_col(self):
        return MAGENTA if self.budget_used_pct > self.completion + 10 else CYAN


class ProjectMember(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role_label = models.CharField(max_length=60, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("project", "user")
        ordering = ["order"]

    def __str__(self):
        return f"{self.user} on {self.project.ref}"


class Phase(BaseModel):
    """One step of the delivery stepper. Its state follows the project's phase_index."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="phases")
    index = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=40)

    class Meta:
        unique_together = ("project", "index")
        ordering = ["index"]

    def __str__(self):
        return f"{self.project.ref} · {self.index + 1} {self.name}"

    @property
    def state(self):
        if self.index < self.project.phase_index:
            return "Complete"
        return "In progress" if self.index == self.project.phase_index else "Not started"

    @property
    def bar_width(self):
        if self.index < self.project.phase_index:
            return "100%"
        return "55%" if self.index == self.project.phase_index else "0%"


class Milestone(RefModel):
    ref_prefix = "MS"
    ref_digits = 3

    ACCEPTANCE = [
        ("Accepted", "Accepted"),
        ("In review", "In review"),
        ("Not due", "Not due"),
        ("Not required", "Not required"),
    ]
    BILLING = [
        ("Paid", "Paid"),
        ("Blocked", "Blocked"),
        ("Scheduled", "Scheduled"),
        ("Ready to bill", "Ready to bill"),
        ("Sent", "Sent"),
        ("Invoiced", "Invoiced"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    code = models.CharField(max_length=8, blank=True)
    name = models.CharField(max_length=120)

    planned_date = models.DateField(null=True, blank=True)
    planned_label = models.CharField(max_length=40, blank=True)
    actual_date = models.DateField(null=True, blank=True)
    actual_label = models.CharField(max_length=40, default="—")
    late_days = models.PositiveSmallIntegerField(default=0)

    value = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    value_display = models.CharField(max_length=20, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="milestones",
    )
    owner_name = models.CharField(max_length=80, blank=True)

    acceptance = models.CharField(max_length=20, choices=ACCEPTANCE, default="Not due")
    acceptance_tag_class = models.CharField(
        max_length=20, choices=TagClass.choices, default=TagClass.NEUTRAL
    )
    billing = models.CharField(max_length=20, choices=BILLING, default="Scheduled")
    tag_class = models.CharField(max_length=20, choices=TagClass.choices, default=TagClass.OUTLINE)

    register_order = models.PositiveSmallIntegerField(default=99)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["project__order", "order"]

    def save(self, *args, **kwargs):
        # A milestone is known by its position on the project: M1, M2, M3 ...
        if not self.code and self.project_id:
            taken = Milestone.objects.filter(project_id=self.project_id).exclude(pk=self.pk)
            self.code = f"M{taken.count() + 1}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.name}"

    @property
    def label(self):
        return f"{self.code} · {self.name}"

    @property
    def actual_col(self):
        if self.late_days:
            return MAGENTA
        return INK if self.actual_label and self.actual_label != "—" else MUTED


class Requirement(RefModel):
    ref_prefix = "REQ"
    ref_digits = 3

    STATUS = [
        ("Accepted", "Accepted"),
        ("In test", "In test"),
        ("Open", "Open"),
        ("Blocked", "Blocked"),
        ("Deferred", "Deferred"),
    ]
    PRIORITY = [("Must", "Must"), ("Should", "Should"), ("Could", "Could")]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="requirements")
    opportunity = models.ForeignKey(
        "crm.Opportunity", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="requirements",
    )

    text = models.CharField(max_length=200, help_text="Requirements register wording")
    detail_text = models.CharField(max_length=200, blank=True, help_text="Project screen wording")
    short_text = models.CharField(max_length=120, blank=True, help_text="Traceability wording")

    source = models.CharField(max_length=80, blank=True)
    detail_source = models.CharField(max_length=80, blank=True)
    trace_origin = models.CharField(max_length=120, blank=True)
    from_change_request = models.BooleanField(default=False)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="requirements",
    )
    owner_name = models.CharField(max_length=80, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY, default="Must")

    status = models.CharField(max_length=12, choices=STATUS, default="Open")
    tag_class = models.CharField(max_length=20, choices=TagClass.choices, default=TagClass.OUTLINE)

    # Traceability: implementation, test and client acceptance.
    implementation_task = models.CharField(max_length=40, blank=True)
    test_ref = models.CharField(max_length=40, blank=True)
    work_label = models.CharField(max_length=80, blank=True)
    test_state = models.CharField(max_length=40, blank=True)
    accepted_state = models.CharField(max_length=20, blank=True)
    accepted_tag_class = models.CharField(
        max_length=20, choices=TagClass.choices, default=TagClass.NEUTRAL
    )
    milestone = models.ForeignKey(
        Milestone, null=True, blank=True, on_delete=models.SET_NULL, related_name="requirements"
    )

    detailed = models.BooleanField(default=False)
    in_trace = models.BooleanField(default=False)
    register_order = models.PositiveSmallIntegerField(default=99)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["register_order", "ref"]

    def __str__(self):
        return f"{self.ref} · {self.text}"


class Task(RefModel):
    ref_prefix = "TASK"
    ref_digits = 3

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    requirement = models.ForeignKey(
        Requirement, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks"
    )
    milestone = models.ForeignKey(
        Milestone, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks"
    )
    text = models.CharField(max_length=200)
    meta = models.CharField(max_length=200, blank=True)
    project_label = models.CharField(max_length=20, blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="tasks",
    )
    points = models.PositiveSmallIntegerField(default=0)
    done = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=[("todo", "To do"), ("in_progress", "In progress"), ("blocked", "Blocked"), ("done", "Done")], default="todo", db_index=True)
    priority = models.CharField(max_length=8, choices=[("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")], default="normal", db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    tag_class = models.CharField(max_length=20, choices=TagClass.choices, default=TagClass.NEUTRAL)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        # Older project screens still update `done`; keep both representations aligned.
        fields = kwargs.get("update_fields")
        if fields and "done" in fields and "status" not in fields:
            self.status = "done" if self.done else "todo"
            kwargs["update_fields"] = set(fields) | {"status"}
        elif fields and "status" in fields:
            self.done = self.status == "done"
            kwargs["update_fields"] = set(fields) | {"done"}
        elif self._state.adding:
            if self.done:
                self.status = "done"
            self.done = self.status == "done"
        else:
            previous = type(self).objects.filter(pk=self.pk).values("done", "status").first()
            if previous and previous["status"] == self.status and previous["done"] != self.done:
                self.status = "done" if self.done else "todo"
            else:
                self.done = self.status == "done"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text


class ProgressUpdate(BaseModel):
    KIND = [
        ("Progress", "Progress"),
        ("Blocker", "Blocker"),
        ("Decision", "Decision"),
        ("Risk", "Risk"),
        ("Stage", "Stage"),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="updates")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="progress_updates",
    )
    who = models.CharField(max_length=80)
    role_label = models.CharField(max_length=60, blank=True)
    when_label = models.CharField(max_length=40, blank=True)
    kind = models.CharField(max_length=12, choices=KIND, default="Progress")
    text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"{self.who}: {self.kind}"

    @property
    def tag_class(self):
        if self.kind in ("Blocker", "Risk"):
            return TagClass.ACCENT_2
        return TagClass.OUTLINE if self.kind == "Stage" else TagClass.NEUTRAL

    @property
    def dot(self):
        return "#111" if self.kind in ("Blocker", "Risk") else "#fff"


class Risk(RefModel):
    ref_prefix = "RSK"
    ref_digits = 3

    SEVERITY = [("Critical", "Critical"), ("High", "High"), ("Medium", "Medium"), ("Low", "Low")]

    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="risks"
    )
    severity = models.CharField(max_length=12, choices=SEVERITY, default="Medium")
    tag_class = models.CharField(max_length=20, choices=TagClass.choices, default=TagClass.OUTLINE)
    title = models.CharField(max_length=200)
    body = models.TextField()

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="risks",
    )
    owner_name = models.CharField(max_length=80, blank=True)

    exposure_label = models.CharField(max_length=40, blank=True)
    exposure_amount = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    probability = models.PositiveSmallIntegerField(default=0)
    impact = models.PositiveSmallIntegerField(default=0)
    bar_width = models.PositiveSmallIntegerField(default=0, help_text="of the 200 unit bar")
    bar_col = models.CharField(max_length=8, default=CYAN)

    raised_on = models.DateField(null=True, blank=True)
    raised_label = models.CharField(max_length=40, blank=True)
    cta = models.CharField(max_length=60, blank=True)
    route = models.CharField(max_length=40, blank=True)
    open = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class RiskAction(BaseModel):
    risk = models.ForeignKey(Risk, on_delete=models.CASCADE, related_name="actions")
    label = models.CharField(max_length=80)
    btn_class = models.CharField(max_length=20, default="btn-secondary")
    route = models.CharField(max_length=40, blank=True)
    toast = models.CharField(max_length=250, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.label


class Closure(BaseModel):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="closure")
    support_contract_ref = models.CharField(max_length=32, blank=True)
    after_closure = models.TextField(blank=True)
    retro_worked = models.TextField(blank=True)
    retro_hurt = models.TextField(blank=True)
    retro_change = models.TextField(blank=True)
    closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["project__order"]

    def __str__(self):
        return f"Closure of {self.project.ref}"

    @property
    def confirmed_count(self):
        return self.items.filter(confirmed=True).count()

    @property
    def total_count(self):
        return self.items.count()

    @property
    def progress_label(self):
        return f"{self.confirmed_count} of {self.total_count} closure conditions confirmed"

    @property
    def cta(self):
        if self.total_count and self.confirmed_count == self.total_count:
            return "Close project and start support"
        return "Confirm remaining items"


class ClosureItem(BaseModel):
    closure = models.ForeignKey(Closure, on_delete=models.CASCADE, related_name="items")
    code = models.CharField(max_length=8)
    text = models.CharField(max_length=200)
    meta = models.CharField(max_length=200, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="closure_items",
    )
    owner_name = models.CharField(max_length=80, blank=True)
    tag_class = models.CharField(max_length=20, choices=TagClass.choices, default=TagClass.NEUTRAL)
    confirmed = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("closure", "code")
        ordering = ["order"]

    def __str__(self):
        return self.text


class SupportTicket(RefModel):
    ref_prefix = "INC"
    ref_digits = 3

    SEVERITY = [("P1", "P1"), ("P2", "P2"), ("P3", "P3"), ("P4", "P4")]
    STATE = [
        ("In progress", "In progress"),
        ("Scheduled", "Scheduled"),
        ("Queued", "Queued"),
        ("Escalated", "Escalated"),
        ("Resolved", "Resolved"),
    ]

    title = models.CharField(max_length=160)
    detail_title = models.CharField(max_length=200, blank=True)
    organisation = models.ForeignKey(
        "crm.Organisation", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="tickets",
    )
    organisation_label = models.CharField(max_length=120, blank=True)
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets"
    )
    system_label = models.CharField(max_length=80, blank=True)

    severity = models.CharField(max_length=4, choices=SEVERITY, default="P3")
    severity_tag_class = models.CharField(
        max_length=20, choices=TagClass.choices, default=TagClass.OUTLINE
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="tickets",
    )
    owner_name = models.CharField(max_length=80, blank=True)

    sla_remaining = models.CharField(max_length=30, default="—")
    sla_pct = models.PositiveSmallIntegerField(default=0)
    sla_col = models.CharField(max_length=8, default=CYAN)
    breached = models.BooleanField(default=False)

    state = models.CharField(max_length=20, choices=STATE, default="Queued")
    tag_class = models.CharField(max_length=20, choices=TagClass.choices, default=TagClass.NEUTRAL)
    meta = models.CharField(max_length=200, blank=True)
    on_engineering_desk = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.ref} · {self.title}"


class MarginCause(BaseModel):
    """One line of the margin decomposition on the cause screen."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="margin_causes")
    impact_points = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    weight = models.PositiveSmallIntegerField(default=0, help_text="bar width, percent")
    title = models.CharField(max_length=120)
    body = models.TextField()
    meta = models.CharField(max_length=200, blank=True)
    step_label = models.CharField(
        max_length=30, blank=True, help_text="Planned-to-actual waterfall label"
    )

    action_label = models.CharField(max_length=80, blank=True)
    action_btn_class = models.CharField(max_length=20, default="btn-secondary")
    action_toast = models.CharField(max_length=250, blank=True)
    action_order = models.PositiveSmallIntegerField(null=True, blank=True)

    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title

    @property
    def impact_label(self):
        return f"{self.impact_points.normalize():f} pts" if self.impact_points else "—"
