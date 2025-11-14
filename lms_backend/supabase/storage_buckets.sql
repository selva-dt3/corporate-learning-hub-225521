-- Storage setup for LMS
-- NOTE: Run after policies if desired; bucket policies are separate.

-- Create buckets (private)
insert into storage.buckets (id, name, public)
values
  ('lesson-content', 'lesson-content', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values
  ('quiz-assets', 'quiz-assets', false)
on conflict (id) do nothing;

-- Policies for lesson-content
-- Allow admin/hr to manage objects
drop policy if exists "lesson-content admin hr full access" on storage.objects;
create policy "lesson-content admin hr full access"
on storage.objects for all
to authenticated
using (
  bucket_id = 'lesson-content'
  and coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr')
)
with check (
  bucket_id = 'lesson-content'
  and coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr')
);

-- No public read for employees; they should use signed URLs only.
-- To reinforce, block generic read by employees (authenticated but not admin/hr)
drop policy if exists "lesson-content block employee direct read" on storage.objects;
create policy "lesson-content block employee direct read"
on storage.objects for select
to authenticated
using (
  bucket_id = 'lesson-content'
  and coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') not in ('admin','hr')
  and false
);

-- Policies for quiz-assets
drop policy if exists "quiz-assets admin hr full access" on storage.objects;
create policy "quiz-assets admin hr full access"
on storage.objects for all
to authenticated
using (
  bucket_id = 'quiz-assets'
  and coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr')
)
with check (
  bucket_id = 'quiz-assets'
  and coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') in ('admin','hr')
);

drop policy if exists "quiz-assets block employee direct read" on storage.objects;
create policy "quiz-assets block employee direct read"
on storage.objects for select
to authenticated
using (
  bucket_id = 'quiz-assets'
  and coalesce((select role from public.profiles p where p.user_id = auth.uid()), '') not in ('admin','hr')
  and false
);
