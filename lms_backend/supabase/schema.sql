-- Supabase Schema for LMS Backend
-- APPLY FIRST
-- Idempotency: Uses IF NOT EXISTS for extension, tables, and indexes so it is safe to re-run.
-- Prerequisites:
--   - Supabase project exists; this SQL runs in the target project's Postgres.
--   - pgcrypto extension is available (managed by Supabase).
--   - auth.users schema exists (managed by Supabase).
-- Purpose:
--   - Defines core tables used by the Flask backend endpoints:
--     profiles, lessons, quizzes, assignments, quiz_submissions.
-- Notes:
--   - Quizzes.spec is JSONB; expected format (used by /quizzes and /quizzes/{id}/submit):
--     {
--       "questions": [
--         {"id":"q1","type":"single","prompt":"...","choices":[...],"answer":0},
--         {"id":"q2","type":"boolean","prompt":"...","answer":true}
--       ],
--       "scoring": {"q1":1,"q2":1}
--     }
--     The backend looks up questions[*].answer and optional scoring weights by question id.

-- Enable pgcrypto for gen_random_uuid()
create extension if not exists "pgcrypto";

-- profiles table stores user metadata linked to auth.users
create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null check (role in ('admin','hr','employee')),
  onboarding_complete boolean not null default false,
  full_name text,
  department text,
  created_at timestamptz not null default now()
);

-- lessons authored by admins/hr
create table if not exists public.lessons (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  content_url text,
  owner uuid references public.profiles(user_id),
  created_at timestamptz not null default now()
);

-- quizzes holding JSON specification (see notes above)
create table if not exists public.quizzes (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  spec jsonb not null,
  created_at timestamptz not null default now()
);

-- assignments link users to lessons/quizzes with status
-- Constraint at_least_one_target ensures either a lesson or a quiz is assigned.
create table if not exists public.assignments (
  id uuid primary key default gen_random_uuid(),
  assignee_user uuid not null references public.profiles(user_id) on delete cascade,
  lesson_id uuid references public.lessons(id),
  quiz_id uuid references public.quizzes(id),
  due_at timestamptz,
  status text not null default 'assigned' check (status in ('assigned','in_progress','completed')),
  created_at timestamptz not null default now(),
  constraint at_least_one_target check (lesson_id is not null or quiz_id is not null)
);

-- quiz submissions by users
create table if not exists public.quiz_submissions (
  id uuid primary key default gen_random_uuid(),
  quiz_id uuid not null references public.quizzes(id) on delete cascade,
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  answers jsonb not null,
  score numeric,
  submitted_at timestamptz not null default now()
);

-- Helpful indexes (safe to re-run)
create index if not exists idx_assignments_assignee_user on public.assignments(assignee_user);
create index if not exists idx_assignments_lesson_id on public.assignments(lesson_id);
create index if not exists idx_assignments_quiz_id on public.assignments(quiz_id);
create index if not exists idx_quiz_submissions_user_id on public.quiz_submissions(user_id);
create index if not exists idx_quiz_submissions_quiz_id on public.quiz_submissions(quiz_id);
create index if not exists idx_lessons_owner on public.lessons(owner);
