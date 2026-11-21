# TrueLog (`digital_logbook`) — Workspace Rules

## Environment & Commands
- **OS / Shell:** Windows PowerShell. Always run Django commands with `.\venv\Scripts\python.exe` (never bare `python` or `python3`).
- **Verification:** After editing Python or template files, run `.\venv\Scripts\python.exe manage.py check` once to verify syntax, imports, and URLs.
- **Scope Discipline:** Never read or search `venv/`, `staticfiles/`, `__pycache__/`, or `db.sqlite3`. Use targeted file reads only.

## Project Architecture
- **Stack:** Django 6.1.2, Tailwind CSS (Dark Mode), SQLite locally (`db.sqlite3`), PostgreSQL on Render (`truelog-ke.onrender.com`).
- **Apps:**
  - `core/` — Project settings, root `urls.py`, and `admin_dashboard` view (`/system-admin/`).
  - `accounts/` — Custom `User` model, profiles, authentication, invite flow, and admin user management.
  - `logbook/` — Student logbook entries, supervisor review workflows, and notifications context processor.
- **Templates:** Stored in root `templates/` (`base.html`, `admin_dashboard.html`, `templates/accounts/`, `templates/logbook/`).

## Models & Domain Constraints
- **`accounts.User` (Custom `AbstractUser`):**
  - Role choices (`User.Role`): `STUDENT`, `UNI_SUPERVISOR`, `FIELD_SUPERVISOR` (never use `UNIVERSITY_SUPERVISOR`, `'UNI'`, or `'FIELD'` in ORM queries).
  - System admins are identified by `is_superuser=True` or `is_staff=True`.
- **Profiles:**
  - `StudentProfile`: `user` (OneToOne, `related_name='student_profile'`), `registration_number`, `course`, `attachment_start_date`, `attachment_end_date`.
  - `UniversitySupervisorProfile`: `user` (OneToOne), `staff_id` (`unique=True`). Always auto-generate `staff_id=f"STF-{uuid.uuid4().hex[:6].upper()}"` when not explicitly supplied so blank strings never trigger `UNIQUE constraint failed`.
  - `FieldSupervisorProfile`: `user` (OneToOne).
  - Note: There is **no** `Department` model in `accounts/models.py`.

## URLs & Routing Conventions
- **Root (`core/urls.py`):** `admin_dashboard` (`/system-admin/`). There is **no** `'home'` URL name—unmatched role fallbacks must redirect to `'accounts:login'`.
- **Accounts (`app_name = 'accounts'`):** `login`, `role_redirect` (`/accounts/redirect/`), `create_user` (`/accounts/create-user/`), `manage_users` (`/accounts/manage-users/`), plus invite/registration routes.
- **Logbook (`app_name = 'logbook'`):** Role-specific dashboards and entry/review routes.

## Frontend & Template Rules
- Extend `base.html` (`{% extends 'base.html' %}`) and place page scripts inside `{% block extra_js %}`.
- **Tailwind Dark Palette:** Main background `bg-[#0a0f1c]`, cards `bg-[#0f172a]`, borders `border-slate-800`, primary actions `bg-brand-500 hover:bg-brand-600`, flat `rounded-md` corners.
- Keep spaces around operators inside Django tags (`{% if role_filter == 'ALL' %}`), never `==""`.
