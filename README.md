# Project Repository

This repository contains the LMS backend (Flask) and integrates with Supabase for authentication, database, and storage.

## Supabase Setup (Backend)

The backend expects a Supabase instance for auth, database, and private storage. Follow these steps to initialize:

1) Create a Supabase project
- Sign in to Supabase and create a new project.
- Do NOT commit any actual keys in git.

2) Configure environment variables
- Copy lms_backend/.env.example to lms_backend/.env and populate:
  - SUPABASE_URL
  - SUPABASE_ANON_KEY
  - SUPABASE_SERVICE_ROLE_KEY
  - SUPABASE_JWT_SECRET
  - FRONTEND_URL
  - CORS_ORIGINS
  - PORT (default 3011)

3) Apply SQL in order
Open the Supabase SQL editor (or use Supabase CLI) and run the SQL files in this exact order:

- lms_backend/supabase/schema.sql    (APPLY FIRST)
- lms_backend/supabase/policies.sql  (APPLY SECOND)
- lms_backend/supabase/storage_buckets.sql (APPLY THIRD)
- lms_backend/supabase/seed.sql (APPLY FOURTH, optional; update UUIDs before running)

Prerequisites and Idempotency:
- pgcrypto extension: schema.sql enables it via "create extension if not exists pgcrypto;" (safe re-run).
- Tables and indexes are created with IF NOT EXISTS (safe re-run).
- Policies are applied by dropping if exists and recreating (safe re-run).
- Storage buckets use ON CONFLICT DO NOTHING and policy drop/create (safe re-run).
- seed.sql is commented examples; copy, replace UUID placeholders with actual auth.users.id values, then run as needed.

Notes:
- schema.sql sets up tables and indexes. Quizzes.spec uses a JSONB format with "questions" and optional "scoring" map; /quizzes/{id}/submit depends on "answer" entries per question.
- policies.sql enables RLS and defines policies for admin, hr, and employee roles aligned with backend routes:
  * Admin/HR: CRUD lessons, quizzes, assignments; list all; manage submissions.
  * Employees: read only assigned lessons/quizzes; read own assignments; insert/select own quiz_submissions.
- storage_buckets.sql creates private buckets (lesson-content, quiz-assets) and policies so only admin/hr can manage; employees should access via signed URLs issued by the backend.
- seed.sql includes examples; adjust IDs to match users created in your Supabase auth. If you need repeatable seeds, wrap with ON CONFLICT DO NOTHING where appropriate.

4) Create initial admin user
- Create a user in Supabase Authentication (Dashboard or CLI).
- Insert a corresponding row in public.profiles with role='admin' using the user_id from auth.users.
- After that, create HR and Employee users similarly and insert their profile rows.

Auto-create profiles on first login
- If SUPABASE_SERVICE_ROLE_KEY is set, the backend will automatically create a default profile (role=employee, onboarding_complete=false) for any authenticated user missing a profile on their first request. This unblocks onboarding for first-time users.
- For admin/HR, you should still promote their role via /users endpoints or manual SQL.

5) Security
- Keep .env out of version control.
- Never commit real Supabase keys or JWT secrets.
- Buckets are private; serve content through signed URLs.

## CORS and Auth Integration

- Ensure FRONTEND_URL and CORS_ORIGINS are set to your frontend origin(s).
  - Local: FRONTEND_URL=http://localhost:3000
  - Multiple origins allowed via CORS_ORIGINS comma-separated list.
  - Include both localhost and your preview host/port.
  - For Kavia preview/E2E, include (update the numeric id to match your preview):
    - https://vscode-internal-12349-beta.beta01.cloud.kavia.ai:3000 (frontend)
    - https://vscode-internal-12349-beta.beta01.cloud.kavia.ai:3001 (backend)
    - https://beta.kavia.ai (if applicable)
  Example:
    CORS_ORIGINS=http://localhost:3000,https://beta.kavia.ai,https://vscode-internal-12349-beta.beta01.cloud.kavia.ai:3000

- To allow embedding /docs in an iframe from those hosts, set:
  DOCS_FRAME_ANCESTORS='self' https://beta.kavia.ai https://vscode-internal-12349-beta.beta01.cloud.kavia.ai:3000
- The frontend forwards Authorization: Bearer <supabase_jwt> on every API call.
- Backend validates JWT using SUPABASE_JWT_SECRET when set, or falls back to unverified decode in dev.

## Development

Backend location: corporate-learning-hub-225521/lms_backend

Run backend locally (example):
- Create and populate lms_backend/.env (see .env.example)
- python -m venv .venv && source .venv/bin/activate
- pip install -r requirements.txt
- python run.py  # serves on http://localhost:${PORT:-3011}

Port already in use?
- If you see "Port 3011 is in use", another instance is already running (e.g., container or prior process).
  - Either stop the other process or set a different PORT in lms_backend/.env (e.g., PORT=3012) before running.
  - In production, use a WSGI server: e.g., `gunicorn -w 2 -b 0.0.0.0:${PORT:-3011} wsgi:application`

API docs (Swagger UI) are served under /docs.
OpenAPI JSON is available at /openapi.json.
Health check remains at GET / returning {"message":"Healthy"}.
Default dev port: 3011 (override via PORT environment variable).

OpenAPI regeneration:
- The spec is generated from the Flask-Smorest setup. To update the interfaces/openapi.json file locally, run:
  python generate_openapi.py from the lms_backend directory. This writes the refreshed spec to lms_backend/interfaces/openapi.json.

Analytics summary response:
- GET /analytics/summary (admin/hr) returns:
  { "users": <int>, "lessons": <int>, "quizzes": <int>, "assignments": <int>, "quiz_submissions": <int> }

## Quick E2E sanity (manual)

1) Start backend on http://localhost:3011 and frontend on http://localhost:3000 (ensure frontend uses REACT_APP_API_BASE_URL=http://localhost:3011)
2) Login via frontend (Supabase email/password)
3) Onboarding page: submit full_name and department
4) Role dashboard loads (admin/hr/employee)
5) As admin/hr, create a lesson (Lessons page) and an assignment via API (Assignments endpoint) if needed
6) As employee, open assigned lesson and take a quiz; submit to /quizzes/{id}/submit
7) As hr/admin, open Analytics page; verify /analytics/summary responds
