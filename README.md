# Project Repository

This repository contains the LMS backend (Flask) and integrates with Supabase for authentication, database, and storage.

## Required Environment Variables (Backend)

Copy lms_backend/.env.example to lms_backend/.env and populate:

- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_ROLE_KEY
- SUPABASE_JWT_SECRET
- FRONTEND_URL (e.g., http://localhost:3000)
- CORS_ORIGINS (comma-separated list of allowed frontend origins)
- DOCS_FRAME_ANCESTORS (space-separated list for frame-ancestors CSP)
- PORT (default 3001)

Conventions and usage:
- Backend reads SUPABASE_* for auth and DB operations.
- CORS and Docs:
  - CORS_ORIGINS controls allowed origins for API.
  - DOCS_FRAME_ANCESTORS controls which origins can embed /docs.
- JWT:
  - Backend validates Authorization: Bearer <supabase_jwt> using SUPABASE_JWT_SECRET.
  - If missing in development, it may fall back to unverified decode, but set it for realistic E2E.

## Integration Matrix

- Frontend → Backend API: uses REACT_APP_API_BASE_URL (or runtime public/env.js override) and sends Authorization: Bearer <supabase_jwt>. Default backend dev port is http://localhost:3001.
- Backend → Supabase:
  - SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY for server operations (profile auto-create, RLS-aware queries).
  - Validates JWTs using SUPABASE_JWT_SECRET.
- CORS:
  - FRONTEND_URL must match a value in CORS_ORIGINS.
  - Include all origins (localhost and preview URLs) that will access the backend.
- Docs embedding:
  - Set DOCS_FRAME_ANCESTORS to 'self' and the specific frontend origins to allow embedding /docs.

## Supabase Setup (Backend)

1) Create a Supabase project
- Sign in to Supabase and create a new project.
- Do NOT commit any actual keys in git.

2) Configure environment variables
- Populate lms_backend/.env as listed above.

3) Apply SQL in order
Run in Supabase SQL editor or CLI:

- lms_backend/supabase/schema.sql    (APPLY FIRST)
- lms_backend/supabase/policies.sql  (APPLY SECOND)
- lms_backend/supabase/storage_buckets.sql (APPLY THIRD)
- lms_backend/supabase/seed.sql (APPLY FOURTH, optional; update UUIDs before running)

Prerequisites and Idempotency:
- pgcrypto extension enabled in schema.sql (safe re-run).
- Tables/indexes guarded by IF NOT EXISTS.
- Policies drop/recreate (safe).
- Buckets upsert and policy drop/create (safe).
- seed.sql contains examples; replace placeholder UUIDs.

Notes:
- policies.sql aligns with backend routes and roles.
- Buckets are private; serve via backend-signed URLs.

4) Create initial admin user
- Create a Supabase Auth user.
- Insert a row into public.profiles with role='admin' for that user_id.
- Repeat for HR and Employee users.

Auto-create profiles on first login
- With SUPABASE_SERVICE_ROLE_KEY set, backend creates a default profile (role=employee, onboarding_complete=false) for new users on first request.

5) Security
- Keep .env out of version control.
- Never commit real Supabase keys or JWT secrets.

## CORS and Auth Integration

- FRONTEND_URL and CORS_ORIGINS must include your frontend origin(s).
  - Local: FRONTEND_URL=http://localhost:3000
  - Multiple origins allowed via comma-separated CORS_ORIGINS.
  - For Kavia preview/E2E (update numeric id accordingly):
    - https://vscode-internal-12349-beta.beta01.cloud.kavia.ai:3000 (frontend)
    - https://vscode-internal-12349-beta.beta01.cloud.kavia.ai:3001 (backend)
    - https://beta.kavia.ai (if applicable)
  Example:
    CORS_ORIGINS=http://localhost:3000,https://beta.kavia.ai,https://vscode-internal-12349-beta.beta01.cloud.kavia.ai:3000

- Allow embedding /docs:
  DOCS_FRAME_ANCESTORS='self' https://beta.kavia.ai https://vscode-internal-12349-beta.beta01.cloud.kavia.ai:3000

- Frontend forwards Authorization: Bearer <supabase_jwt> for every API call.
- Backend validates JWT with SUPABASE_JWT_SECRET.

## Development

Backend location: corporate-learning-hub-225521/lms_backend

Run backend locally:
- python -m venv .venv && source .venv/bin/activate
- pip install -r requirements.txt
- python run.py  # http://localhost:${PORT:-3001}

Port already in use?
- If you see "Port 3001 is in use", either stop the other process or set a different PORT in lms_backend/.env (e.g., PORT=3012).
- Prod: `gunicorn -w 2 -b 0.0.0.0:${PORT:-3001} wsgi:application`

API docs at /docs, OpenAPI JSON at /openapi.json, health at GET / (returns 200 OK).

OpenAPI regeneration:
- From lms_backend: `python generate_openapi.py` to update interfaces/openapi.json.

Analytics summary response (admin/hr):
- GET /analytics/summary → { users, lessons, quizzes, assignments, quiz_submissions }.

## End-to-End Verification Steps

1) Start backend (http://localhost:3001) and frontend (http://localhost:3000).
   - Frontend must have REACT_APP_API_BASE_URL=http://localhost:3001 via .env or public/env.js.
2) Login: use Supabase email/password for a user that exists in auth.
3) Onboarding: fill full_name and department; POST /auth/onboarding/complete.
4) Role routing:
   - Admin → DashboardAdmin
   - HR → DashboardHR
   - Employee → DashboardEmployee
5) Admin/HR:
   - Lessons: create/list via UI → verifies /lessons POST/GET.
   - Quizzes: create/list via UI → verifies /quizzes POST/GET.
   - Assignments: create via /assignments (UI or via API client).
6) Employee:
   - View assigned items; take quiz; submit to /quizzes/{id}/submit.
7) Analytics:
   - HR/Admin open Analytics page; verify /analytics/summary returns counts.

## Troubleshooting

- 401/403 from API:
  - Ensure frontend sends Authorization header (user is logged in).
  - Check SUPABASE_JWT_SECRET matches your Supabase JWT secret.
- CORS error in browser:
  - Add your frontend origin to CORS_ORIGINS and restart backend.
  - Verify protocol, host, and port match exactly.
- /docs not visible in iframe:
  - Ensure DOCS_FRAME_ANCESTORS includes the embedding origin.
- Profile not found after login:
  - Confirm SUPABASE_SERVICE_ROLE_KEY is set for auto-create, or manually insert profile row.
- 500 errors on Supabase calls:
  - Verify SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are populated and valid.
