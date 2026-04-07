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

create index idx_users_email on users(email);
create index idx_wallets_user_id on wallets(user_id);
create index idx_projects_user_id on projects(user_id);
create index idx_tasks_user_id on tasks(user_id);
create index idx_tasks_project_id on tasks(project_id);
create index idx_tasks_status on tasks(status);
create index idx_tasks_workflow_stage on tasks(workflow_stage);
create index idx_task_runs_task_id on task_runs(task_id);
create index idx_task_runs_provider on task_runs(provider);
create index idx_task_events_task_id on task_events(task_id);
create index idx_artifacts_task_id on artifacts(task_id);
create index idx_provider_offers_provider_gpu on provider_offers_snapshots(provider, gpu_type);
create index idx_provider_offers_captured_at on provider_offers_snapshots(captured_at);
