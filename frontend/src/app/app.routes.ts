import { ActivatedRouteSnapshot, ResolveFn, Routes } from '@angular/router';

import { authGuard, permissionGuard, departmentGuard } from './core/guards';

/** Page titles, copied from TITLES in the reference design. */
export const VIEW_TITLES: Record<string, string> = {
  command: 'Command Centre', risks: 'Risk register', project: 'LIMS · PRJ-041',
  cause: 'LIMS · margin cause', lifecycle: 'Lifecycle trace · AN-PBO',
  finance: 'Finance desk', tech: 'Engineering desk', rnd: 'Research desk',
  admin: 'Day desk', docs: 'Document storage', orgs: 'Organisations',
  org: 'AN-PBO · ORG-006', opportunities: 'Opportunities',
  opportunity: 'OPP-114 · discovery', proposals: 'Proposals', contracts: 'Contracts',
  contract: 'CTR-041', projects: 'Projects', requirements: 'Requirements register',
  milestones: 'Milestones', milestonesAll: 'Milestones', changes: 'Change requests',
  change: 'CR-014', closure: 'Project closure', support: 'Support',
  knowledge: 'Knowledge base', people: 'People', users: 'Users and permissions',
  audit: 'Audit trail', profitability: 'Profitability', profile: 'My profile',
  intelligence: 'Ask Prolithica', notifications: 'Notifications', search: 'Search',
  login: 'Sign in',
};

/** Titles the generic record list shows in the topbar, keyed by `:view`. */
const recordTitle: ResolveFn<string> = (route: ActivatedRouteSnapshot) => {
  const view = route.paramMap.get('view') ?? '';
  return VIEW_TITLES[view] ?? 'Records';
};

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },

  {
    path: 'login',
    title: 'Sign in · Prolithica OS',
    loadComponent: () => import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },

  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/shell.component').then((m) => m.ShellComponent),
    children: [
      {path: 'work', data:{title:'My work'}, loadComponent:()=>import('./features/workspace/workspace.component').then(m=>m.WorkspaceComponent)},
      {path: 'reports', data:{title:'Daily reports'}, loadComponent:()=>import('./features/workspace/reports.component').then(m=>m.ReportsComponent)},
      {path: 'chat', data:{title:'Company chat'}, loadComponent:()=>import('./features/workspace/chat.component').then(m=>m.ChatComponent)},
      { path: 'dashboard', data: { title: 'Dashboard' }, loadComponent: () => import('./features/my-day/my-day.component').then(m => m.MyDayComponent) },
      // ── company ──────────────────────────────────────────────────────
      {
        path: 'my-day',
        data: { title: 'My day' },
        loadComponent: () =>
          import('./features/my-day/my-day.component').then((m) => m.MyDayComponent),
      },
      {
        path: 'command',
        canActivate: [departmentGuard('ceo')],
        data: { title: VIEW_TITLES['command'] },
        loadComponent: () => import('./features/command/command.component').then((m) => m.CommandComponent),
      },
      {
        path: 'risks',
        data: { title: VIEW_TITLES['risks'], subtitle: 'Three projects carry risk that is now commercial.' },
        loadComponent: () => import('./features/risks/risks.component').then((m) => m.RisksComponent),
      },
      {
        path: 'intelligence',
        data: { title: VIEW_TITLES['intelligence'] },
        loadComponent: () => import('./features/intelligence/intelligence.component').then((m) => m.IntelligenceComponent),
      },

      // ── delivery ─────────────────────────────────────────────────────
      {
        path: 'projects/:ref',
        data: { title: VIEW_TITLES['project'], crumbs: [{ label: 'Projects', route: '/records/projects' }], crumbCurrent: 'Project' },
        loadComponent: () => import('./features/project/project.component').then((m) => m.ProjectComponent),
      },
      {
        path: 'projects/:ref/cause',
        data: { title: VIEW_TITLES['cause'], crumbs: [{ label: 'Projects', route: '/records/projects' }], crumbCurrent: 'Margin cause' },
        loadComponent: () => import('./features/cause/cause.component').then((m) => m.CauseComponent),
      },
      {
        path: 'closure',
        data: { title: VIEW_TITLES['closure'] },
        loadComponent: () => import('./features/closure/closure.component').then((m) => m.ClosureComponent),
      },
      {
        path: 'lifecycle',
        data: { title: VIEW_TITLES['lifecycle'] },
        loadComponent: () => import('./features/lifecycle/lifecycle.component').then((m) => m.LifecycleComponent),
      },
      {
        path: 'lifecycle/:orgRef',
        data: { title: VIEW_TITLES['lifecycle'], crumbs: [{ label: 'Lifecycle', route: '/lifecycle' }], crumbCurrent: 'Trace' },
        loadComponent: () => import('./features/lifecycle/lifecycle.component').then((m) => m.LifecycleComponent),
      },

      // ── departmental desks ───────────────────────────────────────────
      {
        path: 'finance',
        canActivate: [departmentGuard('finance'), permissionGuard('finance', 'read')],
        data: { title: VIEW_TITLES['finance'] },
        loadComponent: () => import('./features/finance/finance.component').then((m) => m.FinanceComponent),
      },
      {
        path: 'tech',
        canActivate: [departmentGuard('tech')],
        data: { title: VIEW_TITLES['tech'] },
        loadComponent: () => import('./features/tech/tech.component').then((m) => m.TechComponent),
      },
      {
        path: 'rnd',
        canActivate: [departmentGuard('rnd')],
        data: { title: VIEW_TITLES['rnd'] },
        loadComponent: () => import('./features/rnd/rnd.component').then((m) => m.RndComponent),
      },
      {
        path: 'admin-desk',
        canActivate: [departmentGuard('admin')],
        data: { title: VIEW_TITLES['admin'] },
        loadComponent: () => import('./features/admin-desk/admin-desk.component').then((m) => m.AdminDeskComponent),
      },

      // ── records and knowledge ────────────────────────────────────────
      {
        path: 'documents',
        data: { title: VIEW_TITLES['docs'] },
        loadComponent: () => import('./features/documents/documents.component').then((m) => m.DocumentsComponent),
      },
      {
        path: 'knowledge',
        data: { title: VIEW_TITLES['knowledge'] },
        loadComponent: () => import('./features/knowledge/knowledge.component').then((m) => m.KnowledgeComponent),
      },
      {
        path: 'organisations/:ref',
        data: { title: VIEW_TITLES['org'], crumbs: [{ label: 'Organisations', route: '/records/orgs' }], crumbCurrent: 'Organisation' },
        loadComponent: () => import('./features/organisation/organisation.component').then((m) => m.OrganisationComponent),
      },
      {
        path: 'opportunities/:ref',
        data: { title: VIEW_TITLES['opportunity'], crumbs: [{ label: 'Opportunities', route: '/records/opportunities' }], crumbCurrent: 'Opportunity' },
        loadComponent: () => import('./features/opportunity/opportunity.component').then((m) => m.OpportunityComponent),
      },
      {
        path: 'contracts/:ref',
        canActivate: [permissionGuard('contracts', 'read')],
        data: { title: VIEW_TITLES['contract'], crumbs: [{ label: 'Contracts', route: '/records/contracts' }], crumbCurrent: 'Contract' },
        loadComponent: () => import('./features/contract/contract.component').then((m) => m.ContractComponent),
      },
      {
        path: 'changes/:ref',
        data: { title: VIEW_TITLES['change'], crumbs: [{ label: 'Change requests', route: '/records/changes' }], crumbCurrent: 'Change request' },
        loadComponent: () => import('./features/change/change.component').then((m) => m.ChangeComponent),
      },

      // ── personal / cross-cutting ─────────────────────────────────────
      {
        path: 'notifications',
        data: { title: VIEW_TITLES['notifications'] },
        loadComponent: () => import('./features/notifications/notifications.component').then((m) => m.NotificationsComponent),
      },
      {
        path: 'search',
        data: { title: VIEW_TITLES['search'] },
        loadComponent: () => import('./features/search/search.component').then((m) => m.SearchComponent),
      },
      {
        path: 'profile',
        data: { title: VIEW_TITLES['profile'] },
        loadComponent: () => import('./features/profile/profile.component').then((m) => m.ProfileComponent),
      },

      // ── the generic record list ──────────────────────────────────────
      {
        path: 'records/users',
        canActivate: [permissionGuard('user_admin', 'read')],
        data: { title: VIEW_TITLES['users'], view: 'users' },
        loadComponent: () => import('./features/users-admin/users-admin.component').then((m) => m.UsersAdminComponent),
      },
      {
        path: 'records/audit',
        canActivate: [permissionGuard('audit', 'read')],
        data: { title: VIEW_TITLES['audit'], view: 'audit' },
        loadComponent: () => import('./features/records/record-list.component').then((m) => m.RecordListComponent),
      },
      {
        path: 'records/profitability',
        canActivate: [permissionGuard('finance', 'read')],
        data: { title: VIEW_TITLES['profitability'], view: 'profitability' },
        loadComponent: () => import('./features/profitability/profitability.component').then((m) => m.ProfitabilityComponent),
      },
      {
        path: 'records/:view',
        resolve: { title: recordTitle },
        loadComponent: () => import('./features/records/record-list.component').then((m) => m.RecordListComponent),
      },
    ],
  },

  { path: '**', redirectTo: 'dashboard' },
];
