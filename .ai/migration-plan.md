# 迁移计划（本轮）

## SQL 执行顺序
1. 既有迁移 `001` ~ `007`
2. 新增迁移 `008_artifact_delivery_columns.sql`

## 迁移内容
- `artifacts.download_url`
- `artifacts.checksum`
- `artifacts.metadata_payload`

## 风险与回滚
- 风险低（仅新增 nullable 列）。
- 回滚方式：可保留列不使用；若需硬回滚，按 DB 规范 drop 新列。
