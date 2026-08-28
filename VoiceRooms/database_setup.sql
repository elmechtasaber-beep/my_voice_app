-- شغّل هذا الملف في Supabase SQL Editor.
-- ملاحظة: إذا كانت الجداول القديمة موجودة، الأوامر هنا تحافظ عليها قدر الإمكان.

create extension if not exists pgcrypto;

create table if not exists public.rooms (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    host_id uuid references auth.users(id) on delete set null,
    agora_channel text not null unique,
    is_active boolean not null default true,
    participant_count integer not null default 0,
    created_at timestamptz not null default now()
);

create table if not exists public.room_participants (
    id uuid primary key default gen_random_uuid(),
    room_id uuid not null references public.rooms(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    display_name text,
    joined_at timestamptz not null default now(),
    unique (room_id, user_id)
);

alter table public.rooms enable row level security;
alter table public.room_participants enable row level security;

-- إعادة إنشاء السياسات بدون تكرار.
drop policy if exists "rooms are viewable by everyone" on public.rooms;
drop policy if exists "authenticated users can create rooms" on public.rooms;
drop policy if exists "participants viewable by everyone" on public.room_participants;
drop policy if exists "users can join rooms" on public.room_participants;
drop policy if exists "users can leave rooms" on public.room_participants;

create policy "rooms are viewable by everyone"
on public.rooms for select
using (true);

create policy "authenticated users can create rooms"
on public.rooms for insert to authenticated
with check (auth.uid() = host_id);

create policy "participants viewable by everyone"
on public.room_participants for select
using (true);

create policy "users can join rooms"
on public.room_participants for insert to authenticated
with check (auth.uid() = user_id);

create policy "users can leave rooms"
on public.room_participants for delete to authenticated
using (auth.uid() = user_id);

-- تحديث عدد المشاركين تلقائياً؛ المستخدم لا يحتاج صلاحية UPDATE على rooms.
create or replace function public.sync_room_participant_count()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    if tg_op = 'INSERT' then
        update public.rooms
        set participant_count = (
            select count(*) from public.room_participants rp where rp.room_id = new.room_id
        )
        where id = new.room_id;
        return new;
    elsif tg_op = 'DELETE' then
        update public.rooms
        set participant_count = (
            select count(*) from public.room_participants rp where rp.room_id = old.room_id
        )
        where id = old.room_id;
        return old;
    end if;
    return null;
end;
$$;

drop trigger if exists room_participant_count_trigger on public.room_participants;
create trigger room_participant_count_trigger
after insert or delete on public.room_participants
for each row execute function public.sync_room_participant_count();

-- إصلاح العدّاد للبيانات القديمة إن وجدت.
update public.rooms r
set participant_count = (
    select count(*) from public.room_participants rp where rp.room_id = r.id
);

-- تفعيل Postgres Changes للـRealtime.
do $$
begin
    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'rooms'
    ) then
        alter publication supabase_realtime add table public.rooms;
    end if;

    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'room_participants'
    ) then
        alter publication supabase_realtime add table public.room_participants;
    end if;
end $$;

alter table public.rooms replica identity full;
alter table public.room_participants replica identity full;

-- =========================
-- نظام الكوينز والشحن والهدايا
-- =========================
create table if not exists public.wallets (
    user_id uuid primary key references auth.users(id) on delete cascade,
    balance bigint not null default 0 check (balance >= 0),
    updated_at timestamptz not null default now()
);

create table if not exists public.transactions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    type text not null check (type in ('recharge','gift_sent','gift_received','game_bet','game_win','admin_adjustment')),
    amount bigint not null,
    balance_after bigint,
    reference_id uuid,
    counterparty_id uuid references auth.users(id) on delete set null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.gifts (
    id uuid primary key default gen_random_uuid(),
    sender_id uuid not null references auth.users(id) on delete cascade,
    receiver_id uuid not null references auth.users(id) on delete cascade,
    gift_name text not null,
    gift_value bigint not null check (gift_value > 0),
    receiver_percent numeric(5,2) not null default 33.00,
    receiver_reward bigint not null,
    created_at timestamptz not null default now()
);

create table if not exists public.recharge_requests (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    usd_amount numeric(12,2) not null check (usd_amount > 0),
    coin_amount bigint not null check (coin_amount > 0),
    payment_reference text not null,
    status text not null default 'pending' check (status in ('pending','approved','rejected')),
    created_at timestamptz not null default now(),
    reviewed_at timestamptz,
    reviewer_id uuid references auth.users(id) on delete set null
);

alter table public.wallets enable row level security;
alter table public.transactions enable row level security;
alter table public.gifts enable row level security;
alter table public.recharge_requests enable row level security;

drop policy if exists "wallet owner read" on public.wallets;
create policy "wallet owner read" on public.wallets for select to authenticated using (auth.uid() = user_id);
drop policy if exists "transactions owner read" on public.transactions;
create policy "transactions owner read" on public.transactions for select to authenticated using (auth.uid() = user_id);
drop policy if exists "gift participants read" on public.gifts;
create policy "gift participants read" on public.gifts for select to authenticated using (auth.uid() = sender_id or auth.uid() = receiver_id);
drop policy if exists "recharge owner read" on public.recharge_requests;
create policy "recharge owner read" on public.recharge_requests for select to authenticated using (auth.uid() = user_id);
drop policy if exists "recharge owner insert" on public.recharge_requests;
create policy "recharge owner insert" on public.recharge_requests for insert to authenticated with check (auth.uid() = user_id);

-- Atomic gift: sender loses 100%; receiver gets 33%.
create or replace function public.send_gift(p_receiver uuid, p_gift_name text, p_gift_value bigint)
returns jsonb language plpgsql security definer set search_path=public as $$
declare v_sender uuid := auth.uid(); v_reward bigint; v_gid uuid; v_sb bigint; v_rb bigint;
begin
 if v_sender is null then raise exception 'not_authenticated'; end if;
 if p_receiver is null or p_receiver = v_sender then raise exception 'invalid_receiver'; end if;
 if p_gift_value <= 0 then raise exception 'invalid_gift_value'; end if;
 v_reward := floor(p_gift_value * 0.33);
 insert into wallets(user_id) values(v_sender) on conflict do nothing;
 insert into wallets(user_id) values(p_receiver) on conflict do nothing;
 update wallets set balance=balance-p_gift_value,updated_at=now() where user_id=v_sender and balance>=p_gift_value returning balance into v_sb;
 if not found then raise exception 'insufficient_balance'; end if;
 update wallets set balance=balance+v_reward,updated_at=now() where user_id=p_receiver returning balance into v_rb;
 insert into gifts(sender_id,receiver_id,gift_name,gift_value,receiver_reward) values(v_sender,p_receiver,p_gift_name,p_gift_value,v_reward) returning id into v_gid;
 insert into transactions(user_id,type,amount,balance_after,reference_id,counterparty_id,metadata) values(v_sender,'gift_sent',-p_gift_value,v_sb,v_gid,p_receiver,jsonb_build_object('gift_name',p_gift_name));
 insert into transactions(user_id,type,amount,balance_after,reference_id,counterparty_id,metadata) values(p_receiver,'gift_received',v_reward,v_rb,v_gid,v_sender,jsonb_build_object('gift_name',p_gift_name,'gift_value',p_gift_value,'percent',33));
 return jsonb_build_object('gift_id',v_gid,'sender_balance',v_sb,'receiver_reward',v_reward,'receiver_balance',v_rb);
end; $$;
revoke all on function public.send_gift(uuid,text,bigint) from public;
grant execute on function public.send_gift(uuid,text,bigint) to authenticated;
