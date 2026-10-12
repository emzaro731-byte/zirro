-- ZIRRO AI persistent daily image/video/music generation limits.
-- Run this file in Supabase Dashboard -> SQL Editor -> New query.
-- Counts are stored by UTC day, media type, and a SHA-256 browser/client key.

create table if not exists public.zirro_generation_daily_usage (
    usage_day date not null,
    generation_kind text not null check (generation_kind in ('image', 'video', 'music')),
    client_key text not null check (length(client_key) = 64),
    used integer not null default 0 check (used >= 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (usage_day, generation_kind, client_key)
);

alter table public.zirro_generation_daily_usage enable row level security;

-- No direct client access; the Flask backend uses the server-side service role key.
revoke all on table public.zirro_generation_daily_usage from public, anon, authenticated;

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
    v_used integer;
begin
    if p_kind not in ('image', 'video', 'music') then
        raise exception 'Invalid generation kind';
    end if;
    if length(p_client_key) <> 64 then
        raise exception 'Invalid client key';
    end if;
    if p_limit < 1 or p_limit > 10 then
        raise exception 'Invalid generation limit';
    end if;

    insert into public.zirro_generation_daily_usage
        (usage_day, generation_kind, client_key, used, updated_at)
    values
        (p_day, p_kind, p_client_key, 1, now())
    on conflict (usage_day, generation_kind, client_key)
    do update set
        used = public.zirro_generation_daily_usage.used + 1,
        updated_at = now()
    where public.zirro_generation_daily_usage.used < p_limit
    returning used into v_used;

    if found then
        return jsonb_build_object(
            'allowed', true,
            'limit', p_limit,
            'used', v_used,
            'remaining', greatest(p_limit - v_used, 0),
            'resets_at', '00:00 UTC'
        );
    end if;

    select used into v_used
    from public.zirro_generation_daily_usage
    where usage_day = p_day
      and generation_kind = p_kind
      and client_key = p_client_key;

    return jsonb_build_object(
        'allowed', false,
        'limit', p_limit,
        'used', coalesce(v_used, p_limit),
        'remaining', 0,
        'resets_at', '00:00 UTC'
    );
end;
$$;

revoke all on function public.check_zirro_generation_limit(date, text, text, integer) from public, anon, authenticated;
grant execute on function public.check_zirro_generation_limit(date, text, text, integer) to service_role;
