alter table artifacts add column if not exists download_url text;
alter table artifacts add column if not exists checksum text;
alter table artifacts add column if not exists metadata_payload jsonb;
