-- Row Level Security and Policies for LMS
-- APPLY SECOND (after schema.sql, before storage_buckets.sql)
-- Idempotency: Policies use DROP POLICY IF EXISTS then CREATE to allow safe re-runs.
-- Behavior alignment:
--   - Backend reads/writes via Supabase client; RLS must allow:
--       * Admin/HR: full CRUD on lessons, quizzes, assignments; read all submissions; update/delete submissions.
--       * Employees: read only items assigned to them; create/select own quiz_submissions; read own assignments.
--   - Profiles:
--       * Users can read their own profile.
--       * Admin/HR can read all; admin can update others.
--       * Non-admins updating profile must not escalate role.
-- Notes on role resolution:
--   - We consistently resolve caller role via public.profiles using auth.uid().
--   - If you store role in JWT claims, you may extend policies to check jwt() as needed.

-- Enable RLS on all tables (safe if already enabled)
alter table public.profiles enable row level security;
alter table public.lessons enable row level security;
alter table public.quizzes enable row level security;
alter table public.assignments enable row level security;
alter table public.quiz_submissions enable row level security;

-- PROFILES
-- Select: user can see own profile; admins and HR can see all
drop policy if exists profiles_select_self_or_admin on public.profiles;
create policy profiles_select_self_or_admin
on public.profiles
for select
to authenticated
using (
  auth.uid() = user_id
  or coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr')
);

-- Update: users can update their own non-role fields; only admins can update role
drop policy if exists profiles_update_self_fields on public.profiles;
create policy profiles_update_self_fields
on public.profiles
for update
to authenticated
using (auth.uid() = user_id)
with check (
  -- Prevent role escalation by regular users by requiring role remains unchanged if not admin
  (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin'))
  or (role is not distinct from (select role from public.profiles p2 where p2.user_id = user_id))
);

drop policy if exists profiles_admin_update_any on public.profiles;
create policy profiles_admin_update_any
on public.profiles
for update
to authenticated
using (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') = 'admin')
with check (true);

-- Insert/Delete: generally managed by backend/service role only; no authenticated insert/delete via anon key
drop policy if exists profiles_block_insert_authenticated on public.profiles;
create policy profiles_block_insert_authenticated
on public.profiles
for insert
to authenticated
with check (false);

drop policy if exists profiles_block_delete_authenticated on public.profiles;
create policy profiles_block_delete_authenticated
on public.profiles
for delete
to authenticated
using (false);

-- LESSONS
-- Admin/HR can CRUD lessons
drop policy if exists lessons_admin_hr_crud on public.lessons;
create policy lessons_admin_hr_crud
on public.lessons
for all
to authenticated
using (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr'))
with check (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr'));

-- Employees can select lessons only if assigned via assignments
drop policy if exists lessons_employee_select_if_assigned on public.lessons;
create policy lessons_employee_select_if_assigned
on public.lessons
for select
to authenticated
using (
  coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') = 'employee'
  and exists (
    select 1 from public.assignments a
    where a.lesson_id = lessons.id
      and a.assignee_user = auth.uid()
  )
);

-- QUIZZES
-- Admin/HR can CRUD quizzes
drop policy if exists quizzes_admin_hr_crud on public.quizzes;
create policy quizzes_admin_hr_crud
on public.quizzes
for all
to authenticated
using (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr'))
with check (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr'));

-- Employees can select quizzes only if assigned via assignments
drop policy if exists quizzes_employee_select_if_assigned on public.quizzes;
create policy quizzes_employee_select_if_assigned
on public.quizzes
for select
to authenticated
using (
  coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') = 'employee'
  and exists (
    select 1 from public.assignments a
    where a.quiz_id = quizzes.id
      and a.assignee_user = auth.uid()
  )
);

-- ASSIGNMENTS
-- Admin/HR can insert/update/delete and select all
drop policy if exists assignments_admin_hr_crud on public.assignments;
create policy assignments_admin_hr_crud
on public.assignments
for all
to authenticated
using (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr'))
with check (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr'));

-- Employees can select their own assignments
drop policy if exists assignments_employee_select_own on public.assignments;
create policy assignments_employee_select_own
on public.assignments
for select
to authenticated
using (assignee_user = auth.uid());

-- QUIZ SUBMISSIONS
-- Insert by owner (user submits their own)
drop policy if exists quiz_submissions_insert_owner on public.quiz_submissions;
create policy quiz_submissions_insert_owner
on public.quiz_submissions
for insert
to authenticated
with check (user_id = auth.uid());

-- Employees can select their own submissions
drop policy if exists quiz_submissions_select_own on public.quiz_submissions;
create policy quiz_submissions_select_own
on public.quiz_submissions
for select
to authenticated
using (user_id = auth.uid());

-- Admin/HR can select all submissions
drop policy if exists quiz_submissions_admin_hr_select_all on public.quiz_submissions;
create policy quiz_submissions_admin_hr_select_all
on public.quiz_submissions
for select
to authenticated
using (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr'));

-- Update/Delete generally restricted; allow admins/HR
drop policy if exists quiz_submissions_admin_hr_update_delete on public.quiz_submissions;
create policy quiz_submissions_admin_hr_update_delete
on public.quiz_submissions
for update
to authenticated
using (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr'))
with check (true);

drop policy if exists quiz_submissions_admin_hr_delete on public.quiz_submissions;
create policy quiz_submissions_admin_hr_delete
on public.quiz_submissions
for delete
to authenticated
using (coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr'));
