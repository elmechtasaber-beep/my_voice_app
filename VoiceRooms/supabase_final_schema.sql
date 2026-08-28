-- =========================================================
-- SUPABASE FINAL SCHEMA
-- Virtual coins only: recharge / gifts / games.
-- NO cash-out / withdrawal.
-- Run this script in Supabase SQL Editor on a new/clean project.
-- =========================================================

create extension if not exists pgcrypto;

-- -------------------------
-- 1) Profiles
-- -------------------------
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text,
  avatar_url text,
  level int not null default 1 check (level >= 1),
  followers int not null default 0 check (followers >= 0),
  following int not null default 0 check (following >= 0),
  visitors int not null default 0 check (visitors >= 0),
  updated_at timestamptz not null default now()
);

-- -------------------------
-- 2) Wallet
-- One official balance only: wallets.balance
-- -------------------------
create table if not exists public.wallets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  balance bigint not null default 0 check (balance >= 0),
  updated_at timestamptz not null default now()
);

-- -------------------------
-- 3) Transactions
-- -------------------------
create table if not exists public.transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  amount bigint not null,
  type text not null check (
    type in (
      'recharge',
      'gift_sent',
      'gift_received',
      'game_bet',
      'game_win',
      'admin_adjustment'
    )
  ),
  reference_id uuid,
  counterparty_id uuid references auth.users(id) on delete set null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists transactions_user_created_idx
on public.transactions(user_id, created_at desc);

-- -------------------------
-- 4) Gifts
-- -------------------------
create table if not exists public.gifts (
  id uuid primary key default gen_random_uuid(),
  sender_id uuid not null references auth.users(id) on delete cascade,
  receiver_id uuid not null references auth.users(id) on delete cascade,
  gift_name text not null,
  coin_cost bigint not null check (coin_cost > 0),
  receiver_percent numeric(5,2) not null default 33.00,
  receiver_reward bigint not null check (receiver_reward >= 0),
  created_at timestamptz not null default now(),
  check (sender_id <> receiver_id)
);

create index if not exists gifts_sender_created_idx
on public.gifts(sender_id, created_at desc);

create index if not exists gifts_receiver_created_idx
on public.gifts(receiver_id, created_at desc);

-- -------------------------
-- 5) Followers
-- -------------------------
create table if not exists public.followers (
  id uuid primary key default gen_random_uuid(),
  follower_id uuid not null references auth.users(id) on delete cascade,
  following_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique(follower_id, following_id),
  check (follower_id <> following_id)
);

create index if not exists followers_following_idx
on public.followers(following_id);

create index if not exists followers_follower_idx
on public.followers(follower_id);

-- -------------------------
-- 6) Visitors
-- -------------------------
create table if not exists public.visitors (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references auth.users(id) on delete cascade,
  visitor_id uuid not null references auth.users(id) on delete cascade,
  visited_at timestamptz not null default now(),
  check (profile_id <> visitor_id)
);

create index if not exists visitors_profile_time_idx
on public.visitors(profile_id, visited_at desc);

-- -------------------------
-- 7) Rooms
-- -------------------------
create table if not exists public.rooms (
  id uuid primary key default gen_random_uuid(),
  room_name text not null,
  host_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

create index if not exists rooms_host_idx
on public.rooms(host_id);

-- -------------------------
-- 8) Room participants
-- -------------------------
create table if not exists public.room_participants (
  id uuid primary key default gen_random_uuid(),
  room_id uuid not null references public.rooms(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  joined_at timestamptz not null default now(),
  unique(room_id, user_id)
);

create index if not exists room_participants_room_idx
on public.room_participants(room_id);

-- -------------------------
-- 9) Recharge requests
-- Payment verification must happen server-side.
-- This table is for virtual coin recharge records.
-- -------------------------
create table if not exists public.recharge_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  usd_amount numeric(12,2) not null check (usd_amount > 0),
  coin_amount bigint not null check (coin_amount > 0),
  status text not null default 'pending'
    check (status in ('pending','approved','rejected')),
  provider text,
  provider_reference text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  processed_at timestamptz
);

create index if not exists recharge_user_created_idx
on public.recharge_requests(user_id, created_at desc);

-- =========================================================
-- RLS
-- =========================================================

alter table public.profiles enable row level security;
alter table public.wallets enable row level security;
alter table public.transactions enable row level security;
alter table public.gifts enable row level security;
alter table public.followers enable row level security;
alter table public.visitors enable row level security;
alter table public.rooms enable row level security;
alter table public.room_participants enable row level security;
alter table public.recharge_requests enable row level security;

-- Remove old policies if they already exist.
drop policy if exists "profiles_public_read" on public.profiles;
drop policy if exists "profiles_owner_update" on public.profiles;
drop policy if exists "wallet_owner_read" on public.wallets;
drop policy if exists "transactions_owner_read" on public.transactions;
drop policy if exists "gifts_participant_read" on public.gifts;
drop policy if exists "followers_read" on public.followers;
drop policy if exists "followers_insert" on public.followers;
drop policy if exists "followers_delete" on public.followers;
drop policy if exists "visitors_profile_read" on public.visitors;
drop policy if exists "rooms_public_read" on public.rooms;
drop policy if exists "rooms_host_insert" on public.rooms;
drop policy if exists "rooms_host_delete" on public.rooms;
drop policy if exists "room_participants_read" on public.room_participants;
drop policy if exists "room_participants_insert_self" on public.room_participants;
drop policy if exists "room_participants_delete_self" on public.room_participants;
drop policy if exists "recharge_owner_read" on public.recharge_requests;
drop policy if exists "recharge_owner_insert" on public.recharge_requests;

-- Profiles
create policy "profiles_public_read"
on public.profiles for select
using (true);

create policy "profiles_owner_update"
on public.profiles for update
using (auth.uid() = id)
with check (auth.uid() = id);

-- Wallet: READ ONLY for owner.
-- No direct client INSERT/UPDATE/DELETE.
create policy "wallet_owner_read"
on public.wallets for select
using (auth.uid() = user_id);

-- Transactions: owner can read, client cannot insert/update/delete.
create policy "transactions_owner_read"
on public.transactions for select
using (auth.uid() = user_id);

-- Gifts: sender and receiver can read.
-- Client cannot directly create/edit/delete gifts.
create policy "gifts_participant_read"
on public.gifts for select
using (auth.uid() = sender_id or auth.uid() = receiver_id);

-- Followers
create policy "followers_read"
on public.followers for select
using (true);

create policy "followers_insert"
on public.followers for insert
with check (auth.uid() = follower_id);

create policy "followers_delete"
on public.followers for delete
using (auth.uid() = follower_id);

-- Visitors: profile owner can read their visitors; visitor can create their own visit.
create policy "visitors_profile_read"
on public.visitors for select
using (auth.uid() = profile_id or auth.uid() = visitor_id);

-- We do NOT allow direct visitor INSERT from client in this schema.
-- Use the record_profile_visit RPC below.

-- Rooms
create policy "rooms_public_read"
on public.rooms for select
using (true);

create policy "rooms_host_insert"
on public.rooms for insert
with check (auth.uid() = host_id);

create policy "rooms_host_delete"
on public.rooms for delete
using (auth.uid() = host_id);

-- Room participants
create policy "room_participants_read"
on public.room_participants for select
using (true);

create policy "room_participants_insert_self"
on public.room_participants for insert
with check (auth.uid() = user_id);

create policy "room_participants_delete_self"
on public.room_participants for delete
using (auth.uid() = user_id);

-- Recharge requests
create policy "recharge_owner_read"
on public.recharge_requests for select
using (auth.uid() = user_id);

create policy "recharge_owner_insert"
on public.recharge_requests for insert
with check (auth.uid() = user_id);

-- =========================================================
-- Helper: create profile + wallet automatically for new users
-- =========================================================

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles(id, username)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'username', 'زائر')
  )
  on conflict (id) do nothing;

  insert into public.wallets(user_id, balance)
  values (new.id, 0)
  on conflict (user_id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

-- =========================================================
-- Follow / unfollow
-- Counters are updated server-side.
-- =========================================================

create or replace function public.follow_user(p_following uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_me uuid := auth.uid();
  v_rows int;
begin
  if v_me is null then raise exception 'not_authenticated'; end if;
  if p_following is null or p_following = v_me then
    raise exception 'invalid_target';
  end if;

  if not exists (select 1 from auth.users where id = p_following) then
    raise exception 'user_not_found';
  end if;

  insert into public.followers(follower_id, following_id)
  values(v_me, p_following)
  on conflict (follower_id, following_id) do nothing;

  get diagnostics v_rows = ROW_COUNT;
  if v_rows > 0 then
    update public.profiles set following = following + 1, updated_at = now()
    where id = v_me;

    update public.profiles set followers = followers + 1, updated_at = now()
    where id = p_following;
  end if;

  return jsonb_build_object('following', true);
end;
$$;

create or replace function public.unfollow_user(p_following uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_me uuid := auth.uid();
  v_deleted int;
begin
  if v_me is null then raise exception 'not_authenticated'; end if;

  delete from public.followers
  where follower_id = v_me and following_id = p_following;

  get diagnostics v_deleted = ROW_COUNT;

  if v_deleted > 0 then
    update public.profiles
    set following = greatest(following - 1, 0), updated_at = now()
    where id = v_me;

    update public.profiles
    set followers = greatest(followers - 1, 0), updated_at = now()
    where id = p_following;
  end if;

  return jsonb_build_object('following', false);
end;
$$;

-- =========================================================
-- Profile visit
-- =========================================================

create or replace function public.record_profile_visit(p_profile_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.uid() is null then raise exception 'not_authenticated'; end if;
  if p_profile_id is null or p_profile_id = auth.uid() then return; end if;

  insert into public.visitors(profile_id, visitor_id)
  values(p_profile_id, auth.uid());

  update public.profiles
  set visitors = visitors + 1, updated_at = now()
  where id = p_profile_id;
end;
$$;

-- =========================================================
-- Atomic gift:
-- sender loses 100% of gift value.
-- receiver gets 33%.
-- gift + both transactions happen atomically.
-- =========================================================

create or replace function public.send_gift(
  p_receiver uuid,
  p_gift_name text,
  p_coin_cost bigint
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_sender uuid := auth.uid();
  v_reward bigint;
  v_gift_id uuid;
  v_sender_balance bigint;
  v_receiver_balance bigint;
begin
  if v_sender is null then raise exception 'not_authenticated'; end if;
  if p_receiver is null or p_receiver = v_sender then raise exception 'invalid_receiver'; end if;
  if p_gift_name is null or length(trim(p_gift_name)) = 0 then raise exception 'invalid_gift'; end if;
  if p_coin_cost <= 0 then raise exception 'invalid_coin_cost'; end if;

  v_reward := floor(p_coin_cost * 0.33);

  insert into public.wallets(user_id, balance)
  values(v_sender, 0), (p_receiver, 0)
  on conflict (user_id) do nothing;

  update public.wallets
  set balance = balance - p_coin_cost,
      updated_at = now()
  where user_id = v_sender
    and balance >= p_coin_cost
  returning balance into v_sender_balance;

  if not found then raise exception 'insufficient_balance'; end if;

  update public.wallets
  set balance = balance + v_reward,
      updated_at = now()
  where user_id = p_receiver
  returning balance into v_receiver_balance;

  insert into public.gifts(
    sender_id, receiver_id, gift_name, coin_cost,
    receiver_percent, receiver_reward
  )
  values(v_sender, p_receiver, trim(p_gift_name), p_coin_cost, 33.00, v_reward)
  returning id into v_gift_id;

  insert into public.transactions(
    user_id, amount, type, reference_id,
    counterparty_id, metadata
  )
  values(
    v_sender, -p_coin_cost, 'gift_sent', v_gift_id,
    p_receiver,
    jsonb_build_object('gift_name', trim(p_gift_name))
  );

  insert into public.transactions(
    user_id, amount, type, reference_id,
    counterparty_id, metadata
  )
  values(
    p_receiver, v_reward, 'gift_received', v_gift_id,
    v_sender,
    jsonb_build_object(
      'gift_name', trim(p_gift_name),
      'gift_cost', p_coin_cost,
      'receiver_percent', 33
    )
  );

  return jsonb_build_object(
    'gift_id', v_gift_id,
    'sender_balance', v_sender_balance,
    'receiver_reward', v_reward,
    'receiver_balance', v_receiver_balance
  );
end;
$$;

-- =========================================================
-- Recharge request
-- 1 USD = 3,500,000 coins.
-- IMPORTANT: this creates a pending request only.
-- A trusted backend/payment webhook must approve it.
-- =========================================================

create or replace function public.create_recharge_request(
  p_usd numeric,
  p_metadata jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user uuid := auth.uid();
  v_coin_amount bigint;
  v_id uuid;
begin
  if v_user is null then raise exception 'not_authenticated'; end if;
  if p_usd <= 0 then raise exception 'invalid_amount'; end if;

  v_coin_amount := floor(p_usd * 3500000);

  insert into public.recharge_requests(user_id, usd_amount, coin_amount, metadata)
  values(v_user, p_usd, v_coin_amount, coalesce(p_metadata, '{}'::jsonb))
  returning id into v_id;

  return jsonb_build_object(
    'request_id', v_id,
    'usd_amount', p_usd,
    'coin_amount', v_coin_amount,
    'status', 'pending'
  );
end;
$$;

-- Only a trusted backend should call this approval function.
-- Do NOT expose it to the anon/authenticated client.
create or replace function public.approve_recharge(
  p_request_id uuid,
  p_provider text,
  p_provider_reference text
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_request public.recharge_requests%rowtype;
  v_balance bigint;
begin
  if auth.role() <> 'service_role' then
    raise exception 'forbidden';
  end if;

  select *
  into v_request
  from public.recharge_requests
  where id = p_request_id
  for update;

  if not found then raise exception 'recharge_not_found'; end if;
  if v_request.status <> 'pending' then
    raise exception 'recharge_already_processed';
  end if;

  update public.wallets
  set balance = balance + v_request.coin_amount,
      updated_at = now()
  where user_id = v_request.user_id
  returning balance into v_balance;

  if not found then
    insert into public.wallets(user_id, balance)
    values(v_request.user_id, v_request.coin_amount)
    returning balance into v_balance;
  end if;

  update public.recharge_requests
  set status = 'approved',
      provider = p_provider,
      provider_reference = p_provider_reference,
      processed_at = now()
  where id = p_request_id;

  insert into public.transactions(
    user_id, amount, type, reference_id, metadata
  )
  values(
    v_request.user_id,
    v_request.coin_amount,
    'recharge',
    p_request_id,
    jsonb_build_object(
      'usd_amount', v_request.usd_amount,
      'provider', p_provider,
      'provider_reference', p_provider_reference
    )
  );

  return jsonb_build_object(
    'request_id', p_request_id,
    'status', 'approved',
    'coin_amount', v_request.coin_amount,
    'balance', v_balance
  );
end;
$$;

-- Restrict RPC execution.
revoke all on function public.approve_recharge(uuid,text,text) from public, anon, authenticated;

grant execute on function public.follow_user(uuid) to authenticated;
grant execute on function public.unfollow_user(uuid) to authenticated;
grant execute on function public.record_profile_visit(uuid) to authenticated;
grant execute on function public.send_gift(uuid,text,bigint) to authenticated;
grant execute on function public.create_recharge_request(numeric, jsonb) to authenticated;
grant execute on function public.approve_recharge(uuid,text,text) to service_role;

-- =========================================================
-- Notes:
-- 1) Games should use separate SECURITY DEFINER RPCs for bets/wins.
-- 2) Never let the APK update wallets.balance directly.
-- 3) For real payment, verify the provider transaction server-side
--    before calling approve_recharge.
-- =========================================================

-- =========================================================
-- 10) Fruit game: room-scoped, server-authoritative
-- =========================================================
create table if not exists public.fruit_rounds (
  id uuid primary key default gen_random_uuid(),
  room_id uuid not null references public.rooms(id) on delete cascade,
  round_no bigint not null,
  starts_at timestamptz not null default now(),
  ends_at timestamptz not null,
  status text not null default 'open' check (status in ('open','resolved')),
  winning_fruit text,
  resolved_at timestamptz,
  unique(room_id, round_no)
);

create table if not exists public.fruit_bets (
  id uuid primary key default gen_random_uuid(),
  round_id uuid not null references public.fruit_rounds(id) on delete cascade,
  room_id uuid not null references public.rooms(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  fruit text not null check (fruit in ('strawberry','mango','watermelon','apple','cherry','grape','orange','lemon','diamond')),
  coin_amount bigint not null check (coin_amount > 0),
  created_at timestamptz not null default now()
);

create index if not exists fruit_bets_round_idx on public.fruit_bets(round_id, created_at);
create index if not exists fruit_bets_user_idx on public.fruit_bets(user_id, created_at desc);

alter table public.fruit_rounds enable row level security;
alter table public.fruit_bets enable row level security;

-- Clients may read rounds/bets for rooms they can see, but cannot mutate them directly.
drop policy if exists "fruit_rounds_read" on public.fruit_rounds;
drop policy if exists "fruit_bets_read" on public.fruit_bets;
create policy "fruit_rounds_read" on public.fruit_rounds for select using (true);
create policy "fruit_bets_read" on public.fruit_bets for select using (true);

-- Create/open a round. Called by the trusted room/game server only.
create or replace function public.open_fruit_round(p_room_id uuid, p_round_no bigint, p_seconds integer default 30)
returns public.fruit_rounds
language plpgsql security definer set search_path = public
as $$
declare v_round public.fruit_rounds;
begin
  if p_seconds < 5 or p_seconds > 120 then raise exception 'invalid_round_seconds'; end if;
  insert into public.fruit_rounds(room_id, round_no, ends_at)
  values(p_room_id, p_round_no, now() + make_interval(secs => p_seconds))
  returning * into v_round;
  return v_round;
end;
$$;

-- A player can place a bet only through this RPC. The wallet is debited atomically.
create or replace function public.place_fruit_bet(
  p_room_id uuid,
  p_round_id uuid,
  p_fruit text,
  p_coin_amount bigint
)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  v_user uuid := auth.uid();
  v_round public.fruit_rounds;
  v_balance bigint;
begin
  if v_user is null then raise exception 'not_authenticated'; end if;
  if p_coin_amount <= 0 then raise exception 'invalid_coin_amount'; end if;
  if p_fruit not in ('strawberry','mango','watermelon','apple','cherry','grape','orange','lemon','diamond') then
    raise exception 'invalid_fruit';
  end if;

  select * into v_round from public.fruit_rounds
  where id = p_round_id and room_id = p_room_id and status = 'open'
  for update;
  if not found or now() >= v_round.ends_at then raise exception 'round_closed'; end if;

  if not exists (
    select 1 from public.room_participants
    where room_id = p_room_id and user_id = v_user
  ) then raise exception 'not_in_room'; end if;

  update public.wallets
    set balance = balance - p_coin_amount, updated_at = now()
  where user_id = v_user and balance >= p_coin_amount
  returning balance into v_balance;
  if not found then raise exception 'insufficient_balance'; end if;

  insert into public.fruit_bets(round_id, room_id, user_id, fruit, coin_amount)
  values(p_round_id, p_room_id, v_user, p_fruit, p_coin_amount);

  insert into public.transactions(user_id, amount, type, reference_id, metadata)
  values(v_user, -p_coin_amount, 'game_bet', p_round_id,
         jsonb_build_object('fruit', p_fruit, 'room_id', p_room_id));

  return jsonb_build_object('ok', true, 'balance', v_balance);
end;
$$;

-- Resolve a round and pay winning bets. This MUST be called by trusted server/Edge Function only.
-- Top-3 winners published by the trusted resolver for display inside the room.
create table if not exists public.fruit_round_winners (
  id uuid primary key default gen_random_uuid(),
  round_id uuid not null references public.fruit_rounds(id) on delete cascade,
  room_id uuid not null references public.rooms(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  rank smallint not null check (rank between 1 and 3),
  fruit text not null,
  bet_amount bigint not null,
  payout bigint not null,
  balance_after bigint not null,
  created_at timestamptz not null default now(),
  unique(round_id, rank)
);
create index if not exists fruit_round_winners_round_idx on public.fruit_round_winners(round_id, rank);
alter table public.fruit_round_winners enable row level security;
drop policy if exists "fruit_round_winners_read" on public.fruit_round_winners;
create policy "fruit_round_winners_read" on public.fruit_round_winners for select using (true);

do $$ begin
  if not exists (select 1 from pg_publication_tables where pubname='supabase_realtime' and schemaname='public' and tablename='fruit_round_winners') then
    alter publication supabase_realtime add table public.fruit_round_winners;
  end if;
end $$;
alter table public.fruit_round_winners replica identity full;

create or replace function public.resolve_fruit_round(p_round_id uuid, p_winning_fruit text)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  v_round public.fruit_rounds;
  v_multiplier bigint;
  v_total bigint := 0;
begin
  if p_winning_fruit not in ('strawberry','mango','watermelon','apple','cherry','grape','orange','lemon','diamond') then
    raise exception 'invalid_fruit';
  end if;
  select * into v_round from public.fruit_rounds where id=p_round_id for update;
  if not found or v_round.status <> 'open' then raise exception 'round_already_resolved'; end if;
  v_multiplier := case p_winning_fruit
    when 'strawberry' then 45 when 'mango' then 25 when 'watermelon' then 15
    when 'apple' then 10 when 'cherry' then 5 when 'grape' then 5
    when 'orange' then 5 when 'lemon' then 5 when 'diamond' then 60 end;

  update public.wallets w
  set balance = w.balance + (b.coin_amount * v_multiplier), updated_at=now()
  from public.fruit_bets b
  where b.round_id=p_round_id and b.fruit=p_winning_fruit and b.user_id=w.user_id;

  insert into public.transactions(user_id,amount,type,reference_id,metadata)
  select b.user_id,b.coin_amount*v_multiplier,'game_win',p_round_id,
         jsonb_build_object('fruit',p_winning_fruit,'multiplier',v_multiplier,'bet',b.coin_amount)
  from public.fruit_bets b
  where b.round_id=p_round_id and b.fruit=p_winning_fruit;

  -- Aggregate multiple winning bets per player, then publish only the top 3
  -- by resulting wallet balance (ties broken by payout, then user id).
  with agg as (
    select b.user_id, sum(b.coin_amount)::bigint as bet_amount,
           sum(b.coin_amount*v_multiplier)::bigint as payout
    from public.fruit_bets b
    where b.round_id=p_round_id and b.fruit=p_winning_fruit
    group by b.user_id
  ), ranked as (
    select a.*, w.balance as balance_after,
           row_number() over(order by w.balance desc, a.payout desc, a.user_id) as rn
    from agg a join public.wallets w on w.user_id=a.user_id
  )
  insert into public.fruit_round_winners(round_id,room_id,user_id,rank,fruit,bet_amount,payout,balance_after)
  select p_round_id,v_round.room_id,user_id,rn::smallint,p_winning_fruit,bet_amount,payout,balance_after
  from ranked where rn <= 3;

  select coalesce(sum(coin_amount*v_multiplier),0) into v_total
  from public.fruit_bets where round_id=p_round_id and fruit=p_winning_fruit;

  update public.fruit_rounds
  set status='resolved',winning_fruit=p_winning_fruit,resolved_at=now()
  where id=p_round_id;
  return jsonb_build_object('ok',true,'round_id',p_round_id,'winning_fruit',p_winning_fruit,
                            'multiplier',v_multiplier,'total_payout',v_total);
end;
$$;
revoke all on function public.resolve_fruit_round(uuid,text) from public,anon,authenticated;
grant execute on function public.resolve_fruit_round(uuid,text) to service_role;
