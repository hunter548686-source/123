create table if not exists code_edit_review_chains (
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

alter table code_edit_executions add column if not exists review_chain_id bigint references code_edit_review_chains(id);
alter table code_edit_executions add column if not exists chain_step_no int;
alter table code_edit_executions add column if not exists review_chain_status text;

create index if not exists idx_code_edit_review_chains_task_id on code_edit_review_chains(task_id);
create index if not exists idx_code_edit_executions_review_chain_id on code_edit_executions(review_chain_id);
