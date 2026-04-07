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
  workflow_stage text not null default 'planning',
  planning_status text not null default 'pending',
  execution_status text not null default 'pending',
  review_status text not null default 'pending',
  execution_mode text not null default 'hybrid',
  input_payload jsonb not null,
  quote_snapshot jsonb,
  quoted_price numeric(18,4),
  final_cost numeric(18,4),
  final_charge numeric(18,4),
  selected_provider text,
  selected_gpu_type text,
  retry_limit int not null default 2,
  retry_count int not null default 0,
  progress int not null default 0,
  last_error text,
  plan_summary text,
  execution_brief text,
  coding_instructions text,
  review_summary text,
  latest_fix_instructions text,
  result_summary text,
  review_round int not null default 0,
  review_approved boolean,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table task_runs (
  id bigserial primary key,
  task_id bigint not null references tasks(id),
  attempt_no int not null default 1,
  provider text not null,
  gpu_type text not null,
  instance_id text,
  external_task_id text,
  region text,
  runtime_target text not null default 'hybrid',
  status text not null,
  runtime_seconds int not null default 0,
  provider_cost numeric(18,4) not null default 0,
  scheduler_score numeric(10,4),
  fail_reason text,
  local_executor_note text,
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
  download_url text,
  file_size bigint not null default 0,
  checksum text,
  metadata_payload jsonb,
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

create table task_events (
  id bigserial primary key,
  task_id bigint not null references tasks(id),
  source text not null,
  stage text not null,
  level text not null,
  message text not null,
  detail_payload jsonb,
  created_at timestamptz not null default now()
);

create table code_edit_executions (
  id bigserial primary key,
  task_id bigint references tasks(id),
  review_chain_id bigint,
  actor_user_id bigint references users(id),
  actor_email text,
  chain_step_no int,
  review_chain_status text,
  workflow_stage text,
  review_round int,
  review_approved boolean,
  status text not null default 'applied',
  summary text,
  instructions text not null,
  requested_files jsonb not null default '[]'::jsonb,
  changed_files jsonb not null default '[]'::jsonb,
  operations_count int not null default 0,
  diff_preview text,
  test_commands jsonb not null default '[]'::jsonb,
  test_results jsonb not null default '[]'::jsonb,
  model_mode text,
  raw_model_note text,
  rollback_status text not null default 'not_requested',
  rollback_error text,
  rollback_actor_user_id bigint references users(id),
  rollback_actor_email text,
  rolled_back_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table code_edit_review_chains (
  id bigserial primary key,
  task_id bigint not null references tasks(id),
  status text not null default 'awaiting_review',
  started_review_round int not null default 0,
  current_review_round int not null default 0,
  total_executions int not null default 0,
  latest_review_summary text,
  latest_fix_instructions text,
  final_review_approved boolean,
  final_review_summary text,
  opened_at timestamptz not null default now(),
  closed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table code_edit_executions
  add constraint fk_code_edit_review_chain
  foreign key (review_chain_id) references code_edit_review_chains(id);

create table code_edit_execution_files (
  id bigserial primary key,
  execution_id bigint not null references code_edit_executions(id) on delete cascade,
  path text not null,
  before_content text not null,
  after_content text not null,
  created_at timestamptz not null default now()
);
