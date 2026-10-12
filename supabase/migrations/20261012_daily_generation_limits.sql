-- ZIRRO AI: persistent daily media-generation quotas.
-- Run this migration in the Supabase SQL Editor for project vihbsfrwnslnmheowkhy.
-- Each browser/client may generate up to 3 images, videos, and music tracks per UTC day.

create table if not exists public.zirro_generation_daily_usage (
  usage_day date not null,
  kind text not null check (kind in ('image', 'video', 'music')),
  client_key text not null check (length(client_key) = 64),
  used integer not null default 0 check (used >= 0),
  updated_at timestamptz not null default now(),
  primary key (usage_day, kind, client_key)
);

alter table public.zirro_generation_daily_usage enable row level security;

revoke all on table public.zirro_generation_daily_usage from anon, authenticated;
grant all on table public.zirro_generation_daily_usage to service_role;

create or replace function public.check_zirro_generation_limit(
  p_day date,
  p_kind text,
  p_client_key text,
  p_limit integer default 3
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_used integer;
  v_limit integer := greatest(1, least(coalesce(p_limit, 3), 100));
  v_day date := coalesce(p_day, (now() at time zone 'utc')::date);
begin
  if p_kind not in ('image', 'video', 'music') then
    raise exception 'Invalid generation kind';
  end if;
  if p_client_key is null or length(p_client_key) <> 64 then
    raise exception 'Invalid client key';
  end if;

  insert into public.zirro_generation_daily_usage
    (usage_day, kind, client_key, used, updated_at)
  values (v_day, p_kind, p_client_key, 1, now())
  on conflict (usage_day, kind, client_key) do update
    set used = public.zirro_generation_daily_usage.used + 1,
        updated_at = now()
    where public.zirro_generation_daily_usage.used < v_limit
  returning used into v_used;

  if v_used is not null then
    return jsonb_build_object(
      'allowed', true,
      'limit', v_limit,
      'used', v_used,
      'remaining', greatest(0, v_limit - v_used)
    );
  end if;

  select usage.used into v_used
    from public.zirro_generation_daily_usage as usage
   where usage.usage_day = v_day
     and usage.kind = p_kind
     and usage.client_key = p_client_key;

  return jsonb_build_object(
    'allowed', false,
    'limit', v_limit,
    'used', coalesce(v_used, v_limit),
    'remaining', 0
  );
end;
$$;

revoke all on function public.check_zirro_generation_limit(date, text, text, integer) from public, anon, authenticated;
grant execute on function public.check_zirro_generation_limit(date, text, text, integer) to service_role;
