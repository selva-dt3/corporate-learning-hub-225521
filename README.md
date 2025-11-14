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
  - PORT (default 3001)

3) Apply SQL in order
Open the Supabase SQL editor (or use Supabase CLI) and run the SQL files in this exact order:

- lms_backend/supabase/schema.sql
- lms_backend/supabase/policies.sql
- lms_backend/supabase/storage_buckets.sql
- lms_backend/supabase/seed.sql (optional; update UUIDs before running)

Notes:
- schema.sql sets up tables and indexes.
- policies.sql enables RLS and defines policies for admin, hr, and employee roles.
- storage_buckets.sql creates private buckets (lesson-content, quiz-assets) and policies so only admin/hr can manage; employees should access via signed URLs issued by the backend.
- seed.sql includes examples; adjust IDs to match users created in your Supabase auth.

4) Create initial admin user
- Create a user in Supabase Authentication (Dashboard or CLI).
- Insert a corresponding row in public.profiles with role='admin' using the user_id from auth.users.
- After that, create HR and Employee users similarly and insert their profile rows.

5) Security
- Keep .env out of version control.
- Never commit real Supabase keys or JWT secrets.
- Buckets are private; serve content through signed URLs.

## CORS and Auth Integration

- Ensure FRONTEND_URL and CORS_ORIGINS are set to your frontend origin(s).
  - Local: FRONTEND_URL=http://localhost:3000
  - Multiple origins allowed via CORS_ORIGINS comma-separated list.
- The frontend forwards Authorization: Bearer <supabase_jwt> on every API call.
- Backend validates JWT using SUPABASE_JWT_SECRET when set, or falls back to unverified decode in dev.

## Development

Backend location: corporate-learning-hub-225521/lms_backend

Run backend locally (example):
- Create and populate lms_backend/.env (see .env.example)
- python -m venv .venv && source .venv/bin/activate
- pip install -r requirements.txt
- python run.py  # serves on http://localhost:${PORT:-3001}

Port already in use?
- If you see "Port 3001 is in use", another instance is already running (e.g., container or prior process).
  - Either stop the other process or set a different PORT in lms_backend/.env (e.g., PORT=3010) before running.
  - In production, use a WSGI server: e.g., `gunicorn -w 2 -b 0.0.0.0:${PORT:-3001} wsgi:application`

API docs (Swagger UI) are served under /docs.
OpenAPI JSON is available at /openapi.json.
Health check remains at GET / returning {"message":"Healthy"}.

## Quick E2E sanity (manual)

1) Start backend on http://localhost:3001 and frontend on http://localhost:3000
2) Login via frontend (Supabase email/password)
3) Onboarding page: submit full_name and department
4) Role dashboard loads (admin/hr/employee)
5) As admin/hr, create a lesson (Lessons page) and an assignment via API (Assignments endpoint) if needed
6) As employee, open assigned lesson and take a quiz; submit to /quizzes/{id}/submit
7) As hr/admin, open Analytics page; verify /analytics/summary responds
