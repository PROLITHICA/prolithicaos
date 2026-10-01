# Company workspace

The interface uses the company website's local Space Grotesk fonts, wordmark, paper/sage colours, black primary actions and shared rounded cards. Login, navigation, profile and department screens use the same theme.

## Local startup

Dependencies: Python 3.12, Node 20 or 22, backend requirements and frontend npm dependencies.

```sh
python3 -m venv backend_venv
backend_venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
npm ci
cd ..
./dev.sh
```

The existing local database has been migrated. On this machine a fresh Python runtime was used to avoid slow imports in the old virtual environment:

```sh
PROLITHICA_PYTHON=/private/tmp/prolithica-os-runtime/bin/python ./dev.sh
```

The temporary runtime can be recreated using the standard setup above. The app runs at http://localhost:4200 and proxies API requests to Django on port 8000. Startup ensures missing catalogue entries exist and securely prompts for the first CEO account only when no CEO or superuser exists. It never runs the demo seed or overwrites passwords, account details, project edits or linked project records.

## Accounts and work

- The existing CEO account can create or edit employees in **Users and permissions**. Initial passwords are required, validated and hashed. State “Suspended” blocks sign-in and authenticated API access. Password changes invalidate old access tokens.
- Employee numbers are assigned once from a database sequence: EN-P001, EN-P002, and onward. Numbers are not reused.
- Set a department and the **Head of department** checkbox to authorize team assignments. Existing seeded department heads have been designated in a migration.
- **My work & daily logs** lets the CEO add project members and assign tasks. Heads can assign within their department and project scope. Assigning work also creates project membership.
- Employees can complete their tasks and save dated work summaries and minutes. Profiles show current memberships, managed projects and assigned-task projects.
- **Company chat** persists messages in Django. Every group includes active CEOs as administrators. CEOs can edit group names and membership. Direct messages remain visible only to the two participants, including when the CEO is not a participant. The UI refreshes every eight seconds and shows the latest 200 messages.

## Project catalogue

`manage.py setup_workspace` idempotently ensures all eight requested project names, retaining PRJ-041, PRJ-018 and PRJ-038 for established links, and assigning stable references to the other five. Legacy PRJ-030 “AN-PBO Data Portal” is preserved with its financial and delivery records, then archived so those records remain attributed to AN-PBO rather than Bunema. New Bunema work starts at PRJ-046. Later company project edits are preserved. Startup runs this command automatically. **Existing seeded financial amounts, task descriptions and progress remain demonstration data, not verified facts about these projects.** Newly added projects begin at Discovery with no invented delivery history. Do not run the demo seed against company-managed accounts.

A fresh database bootstraps through `dev.sh`, which prompts for the initial CEO email and a validated password without putting the password in shell history or arguments. The prompt is skipped once a CEO or superuser exists.

## Checks

```sh
backend_venv/bin/python backend/manage.py test apps.workforce apps.accounts apps.delivery --noinput
cd frontend
npm run build
node e2e/company-workspace.mjs
```

The browser check uses the existing local demo CEO account and exercises responsive screens without creating employee or message records. API tests use an isolated temporary database.

Email password-reset delivery is not configured. The UI directs employees to their administrator; it does not claim an email was sent. Existing MFA/session interface scaffolding is not a substitute for a completed MFA provider integration.

## Team collaboration workspace

**Work board** (`/work`) provides four task states: To do, In progress, Blocked and Done. Switch between board and list views, filter by department/project/owner/priority/deadline, and search task titles. Department heads and the CEO assign tasks and edit priorities/deadlines. Employees update their own task status. Every card has a status dropdown for keyboard and touch use, in addition to desktop drag and drop. Lists load 50 records at a time with explicit totals and load-more controls. After a task changes, pagination restarts so reordered records are not skipped. Existing project completion controls stay synchronized with the new task status; the migration preserves previously completed tasks.

**Daily reports** (`/reports`, also available under Work board → Daily reports) use completed work, tomorrow's plan and blockers. Each employee has one editable report per date, with optional linked work items; a project assignment is not required to report. Existing project time logs remain under Work board → Project time logs. Department heads see department reports, missing active employees, and blocker counts; the CEO sees company-wide summaries. Employees see their own reports. The workspace prompts for an unsubmitted report from 16:00 on weekdays in Africa/Nairobi time, checking every minute while the app is open. Saving a report removes the prompt. Weekends are excluded from missing-report counts; leave and public holidays require a future calendar integration. External email or push reminders are not configured.

**Company chat** (`/chat`) includes automatically provisioned department channels, existing company groups, and private direct messages. Channel access follows current active department membership, with CEO access to department/company groups; a CEO cannot read a direct message without being a participant. Heads can pin decisions in their own department channel; CEOs can pin group/channel messages. Search message text and attachment filenames, filter pinned decisions, and load older history beyond the former 200-message limit. The latest page refreshes every eight seconds; older loaded history remains stable until refreshed. This uses polling, not websocket delivery.

The CEO can archive/reopen company groups and department channels. Archived conversations remain readable and searchable, and attachments remain downloadable, but posting and pin changes are blocked. The former conversation-delete endpoint now archives instead of deleting records. Department channel membership is derived from employee department assignments and cannot be edited as a group member list.

### Private chat files

Attach PDF, UTF-8 text/CSV, PNG/JPEG, DOCX or XLSX files up to 10 MB. The API checks size, extension and basic file signatures. Downloads are forced attachments and require current conversation access. Signature checks are not a malware-scanning service. Search indexes message text and filenames, not the contents of uploaded documents.

Chat files live outside public `MEDIA_ROOT`, in `backend/private_uploads` by default. Set `PROLITHICA_PRIVATE_CHAT_ROOT` to a persistent private volume when hosting. Back up this directory together with the database; do not publish it through a static web server. Existing document uploads retain their separate storage behavior.

### Upgrade and validation

Install the existing requirements and npm lockfile dependencies, then apply migrations:

```sh
backend_venv/bin/python backend/manage.py migrate --noinput
cd frontend
npm ci
npm run build
cd ..
./dev.sh
```

Fresh installations prompt for the first CEO account; existing accounts and passwords are preserved. Do not run demo seeding on a company database.

Backend verification explicitly names app packages so running from the repository root discovers the suite:

```sh
backend_venv/bin/python backend/manage.py test apps.workforce apps.accounts apps.delivery apps.core apps.crm apps.finance apps.knowledge apps.secretariat apps.documents --noinput
backend_venv/bin/python backend/manage.py makemigrations --check --dry-run
```

`frontend/e2e/collaboration-workspace.mjs` exercises actual task assignment/status persistence, report upsert, paginated chat search/pins/uploads/downloads/archive, employee permissions and 1440/768/390px layouts. `frontend/e2e/collaboration-reliability.mjs` injects page/date/polling failures to verify safe retries and retained drafts. Run them only against an isolated database with fixture accounts. Provide `WORKSPACE_SESSION_FILE` pointing to JSON with `ceo`, `employee` and `finance` access/refresh token pairs, and `WORKSPACE_BASE_URL` pointing to the frontend that proxies that database's API. `WORKSPACE_BROWSER_CHANNEL=chrome` uses installed Chrome; otherwise install Playwright Chromium. `WORKSPACE_SCREENSHOTS` optionally captures the main flow.

To prepare the browser fixture safely from the repository root:

```sh
mkdir -p work
export DATABASE_URL="sqlite:///$PWD/work/workspace-e2e.sqlite3"
export WORKSPACE_SESSION_FILE="$PWD/work/e2e-session.json"
PROLITHICA_E2E=1 backend_venv/bin/python backend/manage.py shell < frontend/e2e/setup-collaboration.py
```

Keep that `DATABASE_URL` in the terminal running the test API. Use a frontend proxy targeting it. After starting the frontend, run the two `.mjs` checks with the session path and frontend URL above. The fixture command refuses the ordinary company database and writes its tokens into an ignored local file. It is separate from ordinary startup and is never invoked by `dev.sh`.
