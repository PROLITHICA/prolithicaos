from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User, Department, Role
from apps.delivery.models import Project, ProjectMember, Task
from .models import DailyLog, Thread, Message

class WorkspaceTests(TestCase):
    def setUp(self):
        self.client=APIClient()
        self.department=Department.objects.create(slug='engineering',label='Engineering')
        self.other_department=Department.objects.create(slug='finance',label='Finance')
        self.director=Role.objects.create(slug='director',label='CEO',is_director=True)
        self.employee_role=Role.objects.create(slug='employee',label='Employee',scope='assigned_projects')
        self.ceo=User.objects.create_user('ceo@example.com','Company-pass-123',display_name='CEO',role=self.director)
        self.hod=User.objects.create_user('hod@example.com','Company-pass-123',display_name='Head',department=self.department,is_department_head=True,role=self.employee_role)
        self.employee=User.objects.create_user('one@example.com','Company-pass-123',display_name='One',department=self.department,role=self.employee_role)
        self.other=User.objects.create_user('other@example.com','Company-pass-123',display_name='Other',department=self.other_department,role=self.employee_role)
        self.project=Project.objects.create(name='Test Project')
        ProjectMember.objects.create(project=self.project,user=self.hod)
    def login_as(self,user): self.client.force_authenticate(user)
    def test_real_account_number_password_and_suspension(self):
        self.login_as(self.ceo)
        payload={'display_name':'New employee','email':'new@example.com','password':'Fresh-company-pass-293','department':str(self.department.pk),'role':str(self.employee_role.pk)}
        response=self.client.post('/api/users/',payload); self.assertEqual(response.status_code,201,response.data)
        user=User.objects.get(email='new@example.com'); self.assertEqual(user.employee_number,'EN-P005');self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password',response.data)
        self.client.force_authenticate(None)
        response=self.client.post('/api/auth/login/',{'email':user.email,'password':payload['password']});self.assertEqual(response.status_code,200)
        token=response.data['access']
        self.login_as(self.ceo);self.client.patch(f'/api/users/{user.pk}/',{'state':'suspended'})
        self.client.force_authenticate(None);self.client.credentials(HTTP_AUTHORIZATION='Bearer '+token)
        self.assertEqual(self.client.get('/api/workspace/').status_code,401)
        self.client.credentials();self.assertEqual(self.client.post('/api/auth/login/',{'email':user.email,'password':payload['password']}).status_code,403)
    def test_employee_cannot_manage_users(self):
        self.login_as(self.employee);self.assertEqual(self.client.get('/api/users/').status_code,403)
    def test_hod_department_assignment_and_profile(self):
        self.login_as(self.hod)
        payload={'text':'Build a form','project':str(self.project.pk),'assignee':str(self.employee.pk)}
        response=self.client.post('/api/workspace/',payload);self.assertEqual(response.status_code,201,response.data)
        payload['assignee']=str(self.other.pk);self.assertEqual(self.client.post('/api/workspace/',payload).status_code,404)
        self.login_as(self.employee)
        self.assertEqual(len(self.client.get('/api/profile/').data['projects']),1)
        self.assertEqual(self.client.post('/api/workspace/',payload).status_code,403)
    def test_daily_logs_owned_and_scoped(self):
        ProjectMember.objects.create(project=self.project,user=self.employee)
        self.login_as(self.employee)
        payload={'project':str(self.project.pk),'date':str(timezone.localdate()),'minutes':90,'summary':'Implemented form','user':str(self.other.pk)}
        self.assertEqual(self.client.post('/api/workspace/logs/',payload).status_code,201)
        self.assertEqual(DailyLog.objects.get().user,self.employee)
        payload['minutes']=1500;self.assertEqual(self.client.post('/api/workspace/logs/',payload).status_code,400)
        self.login_as(self.other);self.assertEqual(self.client.get('/api/workspace/').data['logs'],[])
        self.assertEqual(self.client.post('/api/workspace/logs/',payload).status_code,400)
    def test_group_admin_and_private_direct_messages(self):
        self.login_as(self.employee)
        response=self.client.post('/api/workspace/threads/',{'name':'Engineering','members':[str(self.hod.pk)],'direct':False},format='json')
        self.assertEqual(response.status_code,201,response.data);group=Thread.objects.get(pk=response.data['id']);self.assertIn(self.ceo,group.members.all())
        response=self.client.post('/api/workspace/threads/',{'members':[str(self.hod.pk)],'direct':True},format='json')
        direct=response.data['id'];self.client.post(f'/api/workspace/threads/{direct}/messages/',{'body':'Private note'})
        self.assertEqual(Message.objects.get().body,'Private note')
        self.login_as(self.ceo);self.assertEqual(self.client.get(f'/api/workspace/threads/{direct}/messages/').status_code,404)
        self.assertEqual(self.client.get(f'/api/workspace/threads/{group.pk}/messages/').status_code,200)
        self.login_as(self.other);self.assertEqual(self.client.get(f'/api/workspace/threads/{group.pk}/messages/').status_code,404)
        self.login_as(self.hod)
        again=self.client.post('/api/workspace/threads/',{'members':[str(self.employee.pk)],'direct':True},format='json')
        self.assertEqual(str(again.data['id']),str(direct))
    def test_task_completion_cannot_cross_departments(self):
        task=Task.objects.create(project=self.project,assignee=self.employee,text='Scoped task')
        self.login_as(self.other)
        self.assertEqual(self.client.patch(f'/api/workspace/tasks/{task.pk}/',{'done':True},format='json').status_code,404)
        self.login_as(self.employee)
        self.assertEqual(self.client.patch(f'/api/workspace/tasks/{task.pk}/',{'done':True},format='json').status_code,200)
    def test_ceo_cannot_remove_own_access(self):
        self.login_as(self.ceo)
        self.assertEqual(self.client.patch(f'/api/users/{self.ceo.pk}/',{'state':'suspended'}).status_code,400)
        self.assertEqual(self.client.post(f'/api/users/{self.ceo.pk}/grant/',{'role':'employee'}).status_code,400)

    def test_only_ceo_can_manage_group_members(self):
        self.login_as(self.employee)
        response=self.client.post('/api/workspace/threads/',{'name':'Team','members':[str(self.hod.pk)]},format='json')
        path=f"/api/workspace/threads/{response.data['id']}/messages/"
        self.assertEqual(self.client.patch(path,{'members':[str(self.other.pk)]},format='json').status_code,403)
        self.login_as(self.ceo)
        self.assertEqual(self.client.patch(path,{'name':'Updated team','members':[str(self.other.pk)]},format='json').status_code,200)
        self.login_as(self.employee);self.assertEqual(self.client.get(path).status_code,404)
        self.login_as(self.other);self.assertEqual(self.client.get(path).status_code,200)

    def test_client_portal_accounts_cannot_open_employee_workspace_or_chat(self):
        portal_role=Role.objects.create(slug='client_portal',label='Client portal',scope='own_records')
        portal=User.objects.create_user('portal@example.com','Company-pass-123',display_name='Portal User',role=portal_role)
        self.login_as(portal)
        self.assertEqual(self.client.get('/api/workspace/').status_code,403)
        self.assertEqual(self.client.get('/api/workspace/threads/').status_code,403)
        self.assertEqual(self.client.post('/api/workspace/threads/',{'name':'Attempt','members':[str(self.employee.pk)]},format='json').status_code,403)

    def test_project_setup_is_repeatable_and_keeps_company_edits(self):
        from django.core.management import call_command
        historical=Project.objects.create(ref='PRJ-041',name='LIMS',full_name='LIMS')
        call_command('setup_workspace',verbosity=0)
        historical.refresh_from_db()
        self.assertEqual(historical.name,'LIMS (legislative information system)')
        self.assertEqual(Project.objects.filter(name__in=[
            'Bunema billing system','PBO Workflow','Expresscarpets','Kienyeji Hub',
            'Goalhub','Partec internal system','LIMS (legislative information system)',
            'Directorate of Committees system']).count(),8)
        self.assertEqual(Project.objects.get(name='Bunema billing system').ref,'PRJ-046')
        self.assertEqual(Project.objects.get(name='Expresscarpets').ref,'PRJ-042')
        historical.name='Approved project title'
        historical.stage='Delivery'
        historical.save()
        call_command('setup_workspace',verbosity=0)
        historical.refresh_from_db()
        self.assertEqual((historical.name,historical.stage),('Approved project title','Delivery'))

    def test_bunema_has_its_own_stable_ref_and_legacy_portal_is_archived(self):
        from django.core.management import call_command
        history=Project.objects.create(ref="PRJ-030",name="AN-PBO Data Portal",contract_value=12345,is_archived=True)
        old_task=Task.objects.create(project=history,assignee=self.employee,text="Existing portal task")
        call_command("setup_workspace",verbosity=0)
        history.refresh_from_db()
        bunema=Project.objects.get(ref="PRJ-046")
        self.assertEqual((bunema.name,bunema.contract_value),("Bunema billing system",0))
        self.assertTrue(history.is_archived)
        self.assertEqual((history.name,history.contract_value),("AN-PBO Data Portal",12345))
        self.assertEqual(Task.objects.get(pk=old_task.pk).project_id,history.pk)
        self.login_as(self.ceo)
        response=self.client.get("/api/workspace/")
        self.assertNotIn("AN-PBO Data Portal",[row["name"] for row in response.data["projects"]])
        self.assertEqual(self.client.get(f"/api/projects/{history.pk}/").status_code,404)
        self.assertEqual(self.client.get(f"/api/projects/{bunema.pk}/").status_code,200)

    def test_fresh_install_bootstraps_one_secure_ceo_interactively(self):
        from django.core.management import call_command
        from io import StringIO
        from unittest.mock import patch
        from apps.workforce.management.commands import bootstrap_ceo
        self.ceo.delete()
        output=StringIO()
        with patch('sys.stdin.isatty',return_value=True), patch('builtins.input',return_value='first-ceo@example.com'), patch.object(bootstrap_ceo,'getpass',side_effect=['Secure-first-company-pass-738','Secure-first-company-pass-738']):
            call_command('bootstrap_ceo',stdout=output)
        owner=User.objects.get(email='first-ceo@example.com')
        self.assertTrue(owner.is_superuser)
        self.assertTrue(owner.role.is_director)
        self.assertTrue(owner.check_password('Secure-first-company-pass-738'))
        self.assertRegex(owner.employee_number,r'^EN-P\d{3,}$')
        with patch('builtins.input',side_effect=AssertionError('must not prompt again')):
            call_command('bootstrap_ceo',stdout=output)
        self.assertEqual(User.objects.filter(role__is_director=True).count(),1)

class CollaborationTests(TestCase):
    setUp = WorkspaceTests.setUp
    login_as = WorkspaceTests.login_as
    def test_board_state_filters_and_legacy_completion(self):
        self.login_as(self.hod)
        response=self.client.post('/api/workspace/',{'text':'Review release','project':str(self.project.pk),'assignee':str(self.employee.pk),'priority':'high','due_date':'2026-10-02'},format='json')
        self.assertEqual(response.status_code,201,response.data)
        path=f"/api/workspace/tasks/{response.data['id']}/"
        self.login_as(self.employee)
        response=self.client.patch(path,{'status':'in_progress'},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['status'],'in_progress')
        self.assertFalse(response.data['done'])
        self.assertEqual(self.client.get('/api/workspace/tasks/?priority=low').data['count'],0)
        self.assertEqual(self.client.get('/api/workspace/tasks/?priority=high').data['count'],1)
        self.assertEqual(self.client.patch(path,{'status':'invented'},format='json').status_code,400)
        self.client.patch(path,{'done':True},format='json')
        self.assertEqual(self.client.get('/api/workspace/tasks/').data['results'][0]['status'],'done')
        self.login_as(self.other)
        self.assertEqual(self.client.patch(path,{'status':'blocked'},format='json').status_code,404)

    def test_department_channel_scope_search_pins_and_archive(self):
        self.login_as(self.employee)
        rows=self.client.get('/api/workspace/threads/').data['threads']
        channels=[t for t in rows if str(t.get('department'))==str(self.department.pk)]
        self.assertEqual(len(channels),1)
        channel=channels[0];path=f"/api/workspace/threads/{channel['id']}/messages/"
        sent=self.client.post(path,{'body':'Decision: use Django'},format='json')
        self.assertEqual(sent.status_code,201,sent.data)
        message_path=f"/api/workspace/messages/{sent.data['id']}/"
        self.assertEqual(self.client.patch(message_path,{'pinned':True},format='json').status_code,403)
        self.login_as(self.hod)
        self.assertEqual(self.client.patch(message_path,{'pinned':True},format='json').status_code,200)
        found=self.client.get(path+'?page=1&q=Django').data
        self.assertEqual(found['count'],1)
        self.assertTrue(found['results'][0]['pinned'])
        self.assertEqual(self.client.get(path+'?page=1&q=missing').data['count'],0)
        self.login_as(self.other)
        self.assertEqual(self.client.get(path+'?page=1').status_code,404)
        self.login_as(self.ceo)
        self.assertEqual(self.client.delete(path).status_code,204)
        self.assertEqual(self.client.get(path+'?page=1').data['count'],1)
        self.assertEqual(self.client.post(path,{'body':'Closed'},format='json').status_code,400)

    def test_report_upsert_no_project_required_and_department_summary(self):
        self.login_as(self.employee)
        day=str(timezone.localdate())
        payload={'date':day,'completed':'Shipped form','tomorrow':'Review feedback','blockers':'Waiting for access'}
        first=self.client.post('/api/workspace/reports/',payload,format='json')
        self.assertEqual(first.status_code,201,first.data)
        payload['completed']='Shipped and tested form'
        second=self.client.post('/api/workspace/reports/',payload,format='json')
        self.assertEqual(second.status_code,200,second.data)
        self.assertEqual(first.data['id'],second.data['id'])
        self.login_as(self.hod)
        summary=self.client.get('/api/workspace/reports/?date='+day).data
        self.assertEqual(summary['submitted'],1)
        self.assertEqual(summary['blocker_count'],1)
        self.assertIn(str(self.hod.pk),[str(p['id']) for p in summary['missing']])
        self.assertNotIn(str(self.other.pk),[str(p['id']) for p in summary['missing']])
        self.login_as(self.other)
        self.assertEqual(self.client.get('/api/workspace/reports/?date='+day).data['count'],0)
        self.assertEqual(self.client.post('/api/workspace/reports/',{**payload,'date':'2999-01-01'},format='json').status_code,400)

    def test_attachment_download_requires_channel_access(self):
        import tempfile
        from django.test import override_settings
        from django.core.files.uploadedfile import SimpleUploadedFile
        with tempfile.TemporaryDirectory() as media, override_settings(PRIVATE_CHAT_ROOT=media):
            self.login_as(self.employee)
            channel=next(t for t in self.client.get('/api/workspace/threads/').data['threads'] if t.get('department'))
            path=f"/api/workspace/threads/{channel['id']}/messages/"
            response=self.client.post(path,{'body':'Notes','file':SimpleUploadedFile('notes.txt',b'Project notes',content_type='text/plain')},format='multipart')
            self.assertEqual(response.status_code,201,response.data)
            attachment=f"/api/workspace/messages/{response.data['id']}/attachment/"
            download=self.client.get(attachment)
            self.assertEqual(download.status_code,200)
            self.assertEqual(b''.join(download.streaming_content),b'Project notes')
            self.login_as(self.other)
            self.assertEqual(self.client.get(attachment).status_code,404)
            self.login_as(self.employee)
            rejected=self.client.post(path,{'file':SimpleUploadedFile('bad.html',b'<script>bad</script>')},format='multipart')
            self.assertEqual(rejected.status_code,400)

    def test_history_pagination_retains_messages_beyond_old_limit(self):
        self.login_as(self.employee)
        channel=next(t for t in self.client.get('/api/workspace/threads/').data['threads'] if t.get('department'))
        thread=Thread.objects.get(pk=channel['id'])
        Message.objects.bulk_create([Message(thread=thread,author=self.employee,body=f'History {i}') for i in range(205)])
        path=f'/api/workspace/threads/{thread.pk}/messages/'
        ids=[]
        for page in range(1,6):
            response=self.client.get(path,{'page':page})
            self.assertEqual(response.data['count'],205)
            ids.extend(str(m['id']) for m in response.data['results'])
        self.assertEqual(len(set(ids)),205)
        self.assertFalse(response.data['has_next'])
        self.assertEqual(self.client.get(path,{'page':0}).status_code,400)

    def test_department_changes_revoke_channel_access_and_suspended_accounts_blocked(self):
        self.login_as(self.employee)
        engineering=next(t for t in self.client.get('/api/workspace/threads/').data['threads'] if t.get('department'))
        path=f"/api/workspace/threads/{engineering['id']}/messages/"
        self.employee.department=self.other_department;self.employee.save(update_fields=['department'])
        self.assertEqual(self.client.get(path).status_code,404)
        rows=self.client.get('/api/workspace/threads/').data['threads']
        self.assertIn(str(self.other_department.pk),[str(t['department']) for t in rows])
        self.employee.state='suspended';self.employee.save(update_fields=['state'])
        for endpoint in ['/api/workspace/tasks/','/api/workspace/reports/','/api/workspace/threads/']:
            self.assertEqual(self.client.get(endpoint).status_code,403)

    def test_task_pages_deadlines_and_priority_permissions(self):
        Task.objects.bulk_create([Task(ref=f'TASK-{i:03}',project=self.project,assignee=self.employee,text=f'Task {i}',due_date='2026-10-01',priority='high') for i in range(1,56)])
        self.login_as(self.employee)
        first=self.client.get('/api/workspace/tasks/',{'due_before':'2026-10-01','department':str(self.department.pk)}).data
        self.assertEqual(first['count'],55);self.assertEqual(len(first['results']),50);self.assertTrue(first['has_next'])
        self.assertEqual(len(self.client.get('/api/workspace/tasks/',{'page':2}).data['results']),5)
        self.assertEqual(self.client.get('/api/workspace/tasks/',{'department':str(self.other_department.pk)}).data['count'],0)
        path=f"/api/workspace/tasks/{first['results'][0]['id']}/"
        self.assertEqual(self.client.patch(path,{'priority':'urgent'},format='json').status_code,403)
        self.login_as(self.hod)
        self.assertEqual(self.client.patch(path,{'priority':'urgent','due_date':None},format='json').status_code,200)
        self.assertEqual(self.client.patch(path,{'done':False,'status':'done'},format='json').status_code,400)
        self.assertEqual(self.client.get('/api/workspace/tasks/',{'project':'bad-uuid'}).status_code,400)

    def test_legacy_completion_updates_keep_task_status_consistent(self):
        task=Task.objects.create(project=self.project,assignee=self.employee,text='Legacy',done=True)
        self.assertEqual(task.status,'done')
        task.done=False;task.save(update_fields=['done','updated_at']);task.refresh_from_db()
        self.assertEqual(task.status,'todo')
        task.status='blocked';task.save(update_fields=['status','updated_at']);task.refresh_from_db()
        self.assertFalse(task.done)
        task.done=True;task.save();task.refresh_from_db()
        self.assertEqual(task.status,'done')

    def test_report_reminders_use_nairobi_weekdays_and_stop_after_submission(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from unittest.mock import patch
        self.login_as(self.employee)
        with patch('apps.workforce.collaboration.local_now',return_value=datetime(2026,10,1,16,0,tzinfo=ZoneInfo('Africa/Nairobi'))):
            data=self.client.get('/api/workspace/reports/').data
            self.assertTrue(data['reminder'])
            response=self.client.post('/api/workspace/reports/',{'date':'2026-10-01','completed':'Released form'},format='json')
            self.assertEqual(response.status_code,201)
            self.assertFalse(self.client.get('/api/workspace/reports/').data['reminder'])
        with patch('apps.workforce.collaboration.local_now',return_value=datetime(2026,10,3,16,0,tzinfo=ZoneInfo('Africa/Nairobi'))):
            data=self.client.get('/api/workspace/reports/').data
            self.assertFalse(data['reminder']);self.assertEqual(data['expected'],0);self.assertEqual(data['missing'],[])

    def test_report_links_and_client_access_are_scoped(self):
        foreign=Task.objects.create(project=self.project,assignee=self.other,text='Foreign task')
        self.login_as(self.employee)
        payload={'date':str(timezone.localdate()),'completed':'Updated documentation','tasks':[str(foreign.pk)]}
        self.assertEqual(self.client.post('/api/workspace/reports/',payload,format='json').status_code,400)
        role=Role.objects.create(slug='client_portal',label='Client')
        self.employee.role=role;self.employee.save(update_fields=['role'])
        for endpoint in ['/api/workspace/tasks/','/api/workspace/reports/','/api/workspace/threads/']:
            self.assertEqual(self.client.get(endpoint).status_code,403)

    def test_attachment_limits_and_magic_are_checked(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.login_as(self.employee)
        channel=next(t for t in self.client.get('/api/workspace/threads/').data['threads'] if t.get('department'))
        path=f"/api/workspace/threads/{channel['id']}/messages/"
        self.assertEqual(self.client.post(path,{'file':SimpleUploadedFile('fake.pdf',b'not a PDF')},format='multipart').status_code,400)
        self.assertEqual(self.client.post(path,{'file':SimpleUploadedFile('big.txt',b'x'*(10*1024*1024+1))},format='multipart').status_code,400)
        self.assertEqual(self.client.post(path,{'body':'   '},format='json').status_code,400)


from django.test import TransactionTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

class TaskStatusMigrationTests(TransactionTestCase):
    def test_existing_completed_tasks_are_backfilled(self):
        executor=MigrationExecutor(connection)
        latest=executor.loader.graph.leaf_nodes()
        previous=[('delivery','0005_archive_demo_data_portal')]
        try:
            executor.migrate(previous)
            old_apps=executor.loader.project_state(previous).apps
            project=old_apps.get_model('delivery','Project').objects.create(ref='PRJ-999',name='Migration fixture')
            tasks=old_apps.get_model('delivery','Task')
            complete=tasks.objects.create(ref='TASK-999',project=project,text='Completed before upgrade',done=True)
            pending=tasks.objects.create(ref='TASK-998',project=project,text='Pending before upgrade',done=False)
            executor=MigrationExecutor(connection);executor.migrate(latest)
            self.assertEqual(Task.objects.get(pk=complete.pk).status,'done')
            self.assertEqual(Task.objects.get(pk=pending.pk).status,'todo')
        finally:
            MigrationExecutor(connection).migrate(latest)
