alter table code_edit_executions add column if not exists task_id bigint references tasks(id);
alter table code_edit_executions add column if not exists workflow_stage text;
alter table code_edit_executions add column if not exists review_round int;
alter table code_edit_executions add column if not exists review_approved boolean;

create index if not exists idx_code_edit_executions_task_id on code_edit_executions(task_id);
