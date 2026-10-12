-- ZIRRO AI: run this script once in Supabase Dashboard > SQL Editor.
-- Each signed-in user can read and modify only their own saved conversations.
create table if not exists public.zirro_conversations (
  id text primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'New conversation',
  messages jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now(),
  constraint zirro_conversations_messages_is_array check (jsonb_typeof(messages) = 'array')
);

create index if not exists zirro_conversations_user_updated_idx
  on public.zirro_conversations (user_id, updated_at desc);

alter table public.zirro_conversations enable row level security;

drop policy if exists "Users can read their own ZIRRO conversations" on public.zirro_conversations;
create policy "Users can read their own ZIRRO conversations"
  on public.zirro_conversations for select
  to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "Users can create their own ZIRRO conversations" on public.zirro_conversations;
create policy "Users can create their own ZIRRO conversations"
  on public.zirro_conversations for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update their own ZIRRO conversations" on public.zirro_conversations;
create policy "Users can update their own ZIRRO conversations"
  on public.zirro_conversations for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete their own ZIRRO conversations" on public.zirro_conversations;
create policy "Users can delete their own ZIRRO conversations"
  on public.zirro_conversations for delete
  to authenticated
  using ((select auth.uid()) = user_id);

grant select, insert, update, delete on public.zirro_conversations to authenticated;
