-- Seed data for LMS
-- APPLY FOURTH (optional)
-- Idempotency: This file contains example INSERTs commented out by default.
--   - Copy, replace UUID placeholders with your actual auth.users.id UUIDs and created record ids, then run.
--   - If you need idempotent seeds, wrap inserts with ON CONFLICT (...) DO NOTHING where applicable.
-- Prerequisites:
--   - Users exist in Supabase Authentication; use their UUIDs in profiles.user_id.
-- Quiz spec reminder:
--   - spec JSONB must include questions[*].id and answer, and optionally "scoring" map keyed by question id.

-- Example: create initial admin profile (replace '00000000-0000-0000-0000-000000000000')
-- insert into public.profiles (user_id, role, onboarding_complete, full_name, department)
-- values ('00000000-0000-0000-0000-000000000000', 'admin', true, 'System Admin', 'IT');

-- Sample lessons & quizzes (owners should be admin/hr user ids; replace owner UUID)
-- insert into public.lessons (title, content_url, owner)
-- values
--   ('Welcome to the Company', 'lesson-content/welcome.pdf', '00000000-0000-0000-0000-000000000000'),
--   ('Security Basics', 'lesson-content/security-basics.pdf', '00000000-0000-0000-0000-000000000000');

-- Sample quiz spec structure (aligns with /quizzes/{id}/submit scoring logic)
-- insert into public.quizzes (title, spec)
-- values
-- ('Security Basics Quiz', '{
--   "questions": [
--     {"id": "q1", "type": "single", "prompt": "What is phishing?", "choices": ["A","B","C","D"], "answer": 0},
--     {"id": "q2", "type": "boolean", "prompt": "Use strong passwords.", "answer": true}
--   ],
--   "scoring": {"q1": 1, "q2": 1}
-- }'::jsonb);

-- Assignments (replace assignee_user, lesson_id, quiz_id with actual IDs)
-- insert into public.assignments (assignee_user, lesson_id, status)
-- values ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'assigned');

-- insert into public.assignments (assignee_user, quiz_id, status)
-- values ('11111111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333', 'assigned');

-- A sample employee profile (replace user_id)
-- insert into public.profiles (user_id, role, onboarding_complete, full_name, department)
-- values ('11111111-1111-1111-1111-111111111111', 'employee', false, 'Jane Employee', 'Engineering');

-- Note: To test quiz_submissions, after creating a quiz and employee, run:
-- insert into public.quiz_submissions (quiz_id, user_id, answers, score)
-- values ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', '{"q1":0,"q2":true}', 2);
