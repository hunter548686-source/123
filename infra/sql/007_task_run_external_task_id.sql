alter table task_runs add column if not exists external_task_id text;

create index if not exists idx_task_runs_external_task_id on task_runs(external_task_id);
