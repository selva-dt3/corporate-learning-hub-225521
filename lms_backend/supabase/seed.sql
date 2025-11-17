-- Seed data for LMS
-- APPLY FOURTH (optional)
-- Execution order reminder:
--   1) lms_backend/supabase/schema.sql
--   2) lms_backend/supabase/policies.sql
--   3) lms_backend/supabase/storage_buckets.sql
--   4) lms_backend/supabase/seed.sql (optional; update placeholders)
--
-- Idempotency:
--   - This file contains example INSERTs commented out by default.
--   - Replace placeholders with your actual values and uncomment to run.
--   - Where possible, use ON CONFLICT DO NOTHING to make re-runs safe.
-- Placeholders:
--   - {ADMIN_USER_UUID}: UUID from auth.users.id that should be admin
--   - {EMPLOYEE_USER_UUID}: UUID from auth.users.id that should be employee
--   - {LESSON_ID}, {QUIZ_ID}: Use returned IDs from inserts, or select them
--
-- Prerequisites:
--   - Users exist in Supabase Authentication; use their UUIDs in profiles.user_id.
--
-- Quiz spec reminder:
--   - spec JSONB must include questions[*].id and answer, and optionally "scoring" map keyed by question id.

-- Example: create initial admin profile
-- insert into public.profiles (user_id, role, onboarding_complete, full_name, department)
-- values ('{ADMIN_USER_UUID}', 'admin', true, 'System Admin', 'IT')
-- on conflict (user_id) do update
-- set role = excluded.role,
--     onboarding_complete = excluded.onboarding_complete,
--     full_name = excluded.full_name,
--     department = excluded.department;

-- A sample employee profile
-- insert into public.profiles (user_id, role, onboarding_complete, full_name, department)
-- values ('{EMPLOYEE_USER_UUID}', 'employee', false, 'Jane Employee', 'Engineering')
-- on conflict (user_id) do update
-- set role = excluded.role,
--     onboarding_complete = excluded.onboarding_complete,
--     full_name = excluded.full_name,
--     department = excluded.department;

-- Sample lessons (owners should be admin/hr user ids)
-- insert into public.lessons (title, content_url, owner)
-- values
--   ('Welcome to the Company', 'lesson-content/welcome.pdf', '{ADMIN_USER_UUID}'),
--   ('Security Basics', 'lesson-content/security-basics.pdf', '{ADMIN_USER_UUID}')
-- on conflict do nothing;

-- Sample quiz spec structure (aligns with /quizzes/{id}/submit scoring logic)
-- insert into public.quizzes (title, spec)
-- values
-- ('Security Basics Quiz', '{
--   "questions": [
--     {"id": "q1", "type": "single", "prompt": "What is phishing?", "choices": ["A","B","C","D"], "answer": 0},
--     {"id": "q2", "type": "boolean", "prompt": "Use strong passwords.", "answer": true}
--   ],
--   "scoring": {"q1": 1, "q2": 1}
-- }'::jsonb)
-- on conflict do nothing;

-- Assignments (replace assignee_user, lesson_id, quiz_id with actual IDs)
-- insert into public.assignments (assignee_user, lesson_id, status)
-- values ('{EMPLOYEE_USER_UUID}', '{LESSON_ID}', 'assigned')
-- on conflict do nothing;

-- insert into public.assignments (assignee_user, quiz_id, status)
-- values ('{EMPLOYEE_USER_UUID}', '{QUIZ_ID}', 'assigned')
-- on conflict do nothing;

-- To quickly get IDs after inserts, you may run:
--   select id from public.lessons where title = 'Security Basics';
--   select id from public.quizzes where title = 'Security Basics Quiz';

-- Example quiz submission (for testing scoring/analytics)
-- insert into public.quiz_submissions (quiz_id, user_id, answers, score)
-- values ('{QUIZ_ID}', '{EMPLOYEE_USER_UUID}', '{"q1":0,"q2":true}', 2)
-- on conflict do nothing;
