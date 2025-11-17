# Supabase SQL Execution Order and Notes

Apply these files in the Supabase SQL editor or CLI in this exact order:

1. schema.sql          (creates tables, extensions, indexes; idempotent with IF NOT EXISTS)
2. policies.sql        (enables RLS and creates policies; idempotent via DROP POLICY IF EXISTS then CREATE)
3. storage_buckets.sql (creates private buckets and object policies; idempotent via ON CONFLICT and DROP/CREATE)
4. seed.sql            (optional examples; replace placeholders and use ON CONFLICT for idempotency)

Role alignment (matches backend):
- Admin/HR: full CRUD on lessons, quizzes, assignments; view and manage quiz_submissions
- Employees: read only items assigned to them, read own assignments, submit/select own quiz_submissions
- Profiles: anyone reads own; admin/hr read all; only admin may change others' roles

Idempotency highlights:
- schema.sql uses IF NOT EXISTS for extension, tables, and indexes
- policies.sql drops and recreates policies safely
- storage_buckets.sql uses ON CONFLICT DO NOTHING and drops/recreates policies
- seed.sql examples show ON CONFLICT to prevent duplicates when re-run

Placeholders in seed.sql:
- {ADMIN_USER_UUID}, {EMPLOYEE_USER_UUID}, {LESSON_ID}, {QUIZ_ID}
Replace with actual UUIDs from your environment (auth.users.id and created IDs).
