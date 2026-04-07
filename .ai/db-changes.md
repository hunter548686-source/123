# 数据库变更

## Artifact 字段扩展
- 表：`artifacts`
- 新增字段：
  - `download_url text`
  - `checksum text`
  - `metadata_payload jsonb`

## SQL 文件
- 新增：`infra/sql/008_artifact_delivery_columns.sql`
- 同步更新：`infra/sql/001_bootstrap_schema.sql`
