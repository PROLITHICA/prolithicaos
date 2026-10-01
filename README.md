# Prolithica OS

The company as one connected record. Opportunities become proposals, proposals become contracts,
contracts become projects, and delivery becomes cash — with role-based access so each person sees
the part of it they are responsible for.

Built from the reference design in `_design/Prolithica OS v2.dc.html`.
The build contract lives in [SPEC.md](SPEC.md).

See [Company workspace](docs/company-workspace.md) for CEO account management, department assignments, daily logs, chat and the local setup changes. Startup preserves existing accounts and passwords; it does not rerun demo seeding.

## Stack

| | |
|---|---|
| Backend | Django 5.0 · Django REST Framework · SimpleJWT · SQLite (dev) |
| Frontend | Angular 18 · standalone components · signals · plain CSS |

## Running it

Both halves, from the repository root:

```bash
./dev.sh
```

It applies migrations, ensures the eight-project catalogue is present, and on a fresh database
securely prompts for a CEO email and password before serving the API on :8000 and the app on :4200. The script
prints both addresses when it starts:

```
    On this machine   http://localhost:4200
    On this network   http://192.168.100.27:4200
```

Other devices need **only port 4200**: the app proxies `/api` to the API itself, so
phones and tablets never talk to :8000 directly.

Or run the halves separately:

```bash
# API
backend_venv/bin/python backend/manage.py migrate
backend_venv/bin/python backend/manage.py setup_workspace
backend_venv/bin/python backend/manage.py bootstrap_ceo
backend_venv/bin/python backend/manage.py runserver 0.0.0.0:8000

# App  (node lives in /opt/homebrew/bin on this machine)
export PATH=/opt/homebrew/bin:$PATH
cd frontend && npm start          # binds 0.0.0.0:4200, proxies /api to :8000
```

`ALLOWED_HOSTS` defaults to `*` for development. Set `PROLITHICA_ALLOWED_HOSTS`,
`PROLITHICA_TRUSTED_ORIGINS`, `PROLITHICA_SECRET_KEY` and `PROLITHICA_DEBUG=0`
before putting this anywhere beyond a trusted network.

## Responsive

The interface works from a 390px phone up to a wide desktop. Above 1080px the
sidebar is a fixed column; below it, it becomes an off-canvas drawer opened from
the topbar and closed by choosing a destination or tapping the backdrop. Wide
tables and charts scroll inside their own containers, so the page itself never
scrolls sideways at any width.

## Signing in

| Role | Email | Password |
|---|---|---|
| **Director** (full access) | `newtvnbrian@gmail.com` | `12428newton` |
| Executive | `newton.brian@prolithica.com` | `12428newton` |
| Head of Finance | `franklin.karanja@prolithica.com` | `12428newton` |
| Lead Technical | `edwin.ndiritu@prolithica.com` | `12428newton` |
| Head of R&D | `milele.faith@prolithica.com` | `12428newton` |
| Secretariat Lead | `grace.mwende@prolithica.com` | `12428newton` |
| Project Manager | `jude.angedu@prolithica.com` | `12428newton` |
| Client portal | `secretariat@an-pbo.org` | `12428newton` |

Each account lands on its own home desk with its own navigation, its own scope of records, and
money hidden where the role has no financial permission.

## Role-based access

Permission is enforced in three layers, all server-side:

1. **Endpoint** — `HasAreaPermission` checks the role's level for the area a view declares.
2. **Scope** — `company`, `assigned_projects` or `own_records` narrows every queryset.
3. **Field** — amounts render as `R ••••` for roles below `restricted` on `financials`.

Levels run `none < read < contribute < restricted < full < approve < administer`.
The Angular client mirrors the same map for hiding UI, but the server is the authority.

Every write and every sensitive read lands in the audit trail, which is append-only — the API
exposes no way to edit or delete an event, and neither does the Django admin.

## Layout

```
backend/
  prolithica/          settings, root URLs, the API router
  apps/core/           shared model base, money, audit, search, Ask Prolithica,
                       Command Centre, notifications, the seed command
  apps/accounts/       users, departments, roles, permissions, sessions, audit
  apps/crm/            organisations, opportunities, proposals, contracts, change requests
  apps/delivery/       projects, milestones, requirements, tasks, risks, support, closure
  apps/finance/        invoices, payments, expenses, billing, profitability
  apps/knowledge/      research, patterns, lessons, knowledge base
  apps/secretariat/    meetings, signatures, correspondence
  apps/documents/      folders, documents, exports
frontend/src/app/
  core/                api, auth, permissions, guards, interceptor, toasts
  shared/ui/           the design system as components
  layout/              shell (sidebar, topbar), boot screen
  features/            one folder per screen
```

## Tests

```bash
backend_venv/bin/python backend/manage.py test apps.workforce apps.accounts apps.delivery apps.core apps.crm apps.finance apps.knowledge apps.secretariat apps.documents --noinput
export PATH=/opt/homebrew/bin:$PATH && cd frontend && npm run build
```
