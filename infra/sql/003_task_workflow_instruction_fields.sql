alter table tasks add column if not exists execution_brief text;
alter table tasks add column if not exists coding_instructions text;
alter table tasks add column if not exists latest_fix_instructions text;
alter table tasks add column if not exists review_round int not null default 0;
alter table tasks add column if not exists review_approved boolean;
