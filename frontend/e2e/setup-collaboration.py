import os
import secrets
import json
from pathlib import Path
from django.core.management import call_command
from apps.accounts.models import User, Department, Role
from apps.delivery.models import Project, ProjectMember, Task
from apps.workforce.models import Thread, Message
from rest_framework_simplejwt.tokens import RefreshToken
# Run only against the isolated browser-check SQLite database.
from django.conf import settings
assert os.environ.get('PROLITHICA_E2E') == '1', 'Explicit E2E setup flag required.'
assert Path(settings.DATABASES['default']['NAME']).name == 'workspace-e2e.sqlite3', 'Use an isolated workspace-e2e.sqlite3 database.'
call_command('migrate',verbosity=0)
if not User.objects.filter(email='workspace-review@example.test').exists():
    department=Department.objects.create(slug='workspace-review-engineering',label='Engineering · browser fixture',home_view='tech')
    other=Department.objects.create(slug='workspace-review-finance',label='Finance · browser fixture',home_view='finance')
    role=Role.objects.create(slug='workspace-review-director',label='CEO',is_director=True)
    employee_role=Role.objects.create(slug='workspace-review-employee',label='Employee')
    ceo=User.objects.create_user('workspace-review@example.test',secrets.token_urlsafe(24),display_name='Workspace reviewer',role=role,department=department)
    employee=User.objects.create_user('workspace-employee@example.test',secrets.token_urlsafe(24),display_name='Engineering reviewer',role=employee_role,department=department)
    finance=User.objects.create_user('workspace-finance@example.test',secrets.token_urlsafe(24),display_name='Finance reviewer',role=employee_role,department=other)
    project=Project.objects.create(name='Workspace browser fixture',short_label='Review')
    ProjectMember.objects.create(project=project,user=employee)
    Task.objects.create(project=project,assignee=employee,text='Review workspace release',priority='high',due_date='2026-10-01')
    for i in range(54): Task.objects.create(project=project,assignee=employee,text=f'Browser fixture task {i:02}',status=['todo','in_progress','blocked','done'][i%4])
    thread=Thread.objects.create(name=department.label,department=department)
    Message.objects.bulk_create([Message(thread=thread,author=employee,body=f'Browser history {i:03}') for i in range(205)])
rows={}
for name,email in [('ceo','workspace-review@example.test'),('employee','workspace-employee@example.test'),('finance','workspace-finance@example.test')]:
    user=User.objects.get(email=email);token=RefreshToken.for_user(user)
    rows[name]={'access':str(token.access_token),'refresh':str(token)}
session_path=Path(os.environ.get('WORKSPACE_SESSION_FILE','work/e2e-session.json'))
session_path.parent.mkdir(parents=True,exist_ok=True)
session_path.write_text(json.dumps(rows))
session_path.chmod(0o600)
print('Isolated collaboration fixture and browser sessions prepared.')
