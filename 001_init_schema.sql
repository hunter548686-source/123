create table users (
  id bigserial primary key,
  email text unique not null,
  phone text,
  password_hash text not null,
  role text not null default 'user',
  status text not null default 'active',
  created_at timestamptz not null default now()
);

create table wallets (
  id bigserial primary key,
  user_id bigint not null references users(id),
  balance numeric(18,4) not null default 0,
  frozen_balance numeric(18,4) not null default 0,
  currency text not null default 'CNY',
  created_at timestamptz not null default now()
);

create table wallet_ledger (
  id bigserial primary key,
  wallet_id bigint not null references wallets(id),
  type text not null,
  amount numeric(18,4) not null,
  balance_after numeric(18,4) not null,
  ref_type text,
  ref_id text,
  created_at timestamptz not null default now()
);

create table projects (
  id bigserial primary key,
  user_id bigint not null references users(id),
  name text not null,
  scene_type text not null,
  created_at timestamptz not null default now()
);

create table tasks (
  id bigserial primary key,
  project_id bigint not null references projects(id),
  user_id bigint not null references users(id),
  task_type text not null,
  template_id text not null,
  strategy text not null,
  status text not null default 'queued',
  input_payload jsonb not null,
  quoted_price numeric(18,4),
  final_cost numeric(18,4),
  final_charge numeric(18,4),
  progress int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table task_runs (
  id bigserial primary key,
  task_id bigint not null references tasks(id),
  provider text not null,
  gpu_type text not null,
  instance_id text,
  region text,
  status text not null,
  runtime_seconds int not null default 0,
  provider_cost numeric(18,4) not null default 0,
  fail_reason text,
  started_at timestamptz,
  ended_at timestamptz,
  created_at timestamptz not null default now()
);

create table checkpoints (
  id bigserial primary key,
  task_id bigint not null references tasks(id),
  task_run_id bigint not null references task_runs(id),
  storage_path text not null,
  progress_percent int not null default 0,
  created_at timestamptz not null default now()
);

create table artifacts (
  id bigserial primary key,
  task_id bigint not null references tasks(id),
  type text not null,
  storage_path text not null,
  file_size bigint not null default 0,
  created_at timestamptz not null default now()
);

create table provider_offers_snapshots (
  id bigserial primary key,
  provider text not null,
  gpu_type text not null,
  region text,
  price_per_hour numeric(18,4) not null,
  reliability_score numeric(8,4) default 0,
  startup_score numeric(8,4) default 0,
  success_rate numeric(8,4) default 0,
  raw_payload jsonb,
  captured_at timestamptz not null default now()
);

create index idx_users_email on users(email);
create index idx_wallets_user_id on wallets(user_id);
create index idx_projects_user_id on projects(user_id);
create index idx_tasks_user_id on tasks(user_id);
create index idx_tasks_project_id on tasks(project_id);
create index idx_tasks_status on tasks(status);
create index idx_task_runs_task_id on task_runs(task_id);
create index idx_task_runs_provider on task_runs(provider);
create index idx_checkpoints_task_id on checkpoints(task_id);
create index idx_artifacts_task_id on artifacts(task_id);
create index idx_provider_offers_provider_gpu on provider_offers_snapshots(provider, gpu_type);
create index idx_provider_offers_captured_at on provider_offers_snapshots(captured_at);
