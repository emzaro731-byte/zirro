-- Persistent per-client daily quotas for ZIRRO media generation.
create table if not exists public.zirro_generation_usage (
  day date not null,
  kind text not null check (kind in ('image', 'video', 'music')),
  client_key text not null check (length(client_key) = 64),
  used integer not null default 0 check (used >= 0),
  updated_at timestamptz not null default now(),
  primary key (day, kind, client_key)
);

alter table public.zirro_generation_usage enable row level security;
revoke all on public.zirro_generation_usage from anon, authenticated;
grant all on public.zirro_generation_usage to service_role;

create or replace function public.check_zirro_generation_limit(
  p_day date,
  p_kind text,
  p_client_key text,
  p_limit integer default 3
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_new_used integer;
  v_used integer;
  v_allowed boolean;
  v_limit integer := greatest(1, least(coalesce(p_limit, 3), 100));
begin
  if p_day is null
     or p_kind not in ('image', 'video', 'music')
     or p_client_key is null
     or length(p_client_key) <> 64 then
    raise exception 'Invalid generation quota parameters';
  end if;

  insert into public.zirro_generation_usage (day, kind, client_key, used, updated_at)
  values (p_day, p_kind, p_client_key, 1, now())
  on conflict (day, kind, client_key)
  do update set
    used = public.zirro_generation_usage.used + 1,
    updated_at = now()
  where public.zirro_generation_usage.used < v_limit
  returning used into v_new_used;

  if v_new_used is not null then
    v_allowed := true;
    v_used := v_new_used;
  else
    v_allowed := false;
    select used into v_used
    from public.zirro_generation_usage
    where day = p_day and kind = p_kind and client_key = p_client_key;
  end if;

  return jsonb_build_object(
    'allowed', v_allowed,
    'used', coalesce(v_used, 0),
    'limit', v_limit,
    'remaining', greatest(0, v_limit - coalesce(v_used, 0))
  );
end;
$$;

revoke all on function public.check_zirro_generation_limit(date, text, text, integer) from public, anon, authenticated;
grant execute on function public.check_zirro_generation_limit(date, text, text, integer) to service_role;
