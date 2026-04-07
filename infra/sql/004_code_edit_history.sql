create table if not exists code_edit_executions (
  id bigserial primary key,
  actor_user_id bigint references users(id),
  actor_email text,
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

create table if not exists code_edit_execution_files (
  id bigserial primary key,
  execution_id bigint not null references code_edit_executions(id) on delete cascade,
  path text not null,
  before_content text not null,
  after_content text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_code_edit_executions_created_at on code_edit_executions(created_at);
create index if not exists idx_code_edit_executions_actor_user_id on code_edit_executions(actor_user_id);
create index if not exists idx_code_edit_execution_files_execution_id on code_edit_execution_files(execution_id);
