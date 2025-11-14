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

## Development

Backend location: corporate-learning-hub-225521/lms_backend

Run backend locally (example):
- Create and populate lms_backend/.env
- Install Python deps (see requirements.txt)
- python run.py

API docs (Swagger UI) are served under /docs per the Flask app config.
