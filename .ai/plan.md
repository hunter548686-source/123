# 当前阶段执行计划（落地版）

## P1 适配层
- [x] 扩展 provider marketplace 契约：增加 `cleanup_task`。
- [x] 新增 `vast_ai` adapter。
- [x] 新增 `runpod` adapter。
- [x] 新增 `multi_provider_live` 聚合 adapter（按 provider 路由下发与状态查询）。
- [x] 扩展配置项与 `.env.example`。

## P2 状态机与 worker
- [x] `TaskStatus` 新增 `cancelling` / `cleaning_up`。
- [x] `TaskRunStatus` 新增 `cancelling` / `cleaning_up` / `cancelled`。
- [x] 失败链路：cleanup -> fail_or_retry -> 迁移重试。
- [x] 取消链路：cancel provider -> cleanup -> cancelled。
- [x] 成功链路：结果回收后执行 post-result cleanup。

## P3 API 与数据
- [x] Artifact 模型扩展 `download_url/checksum/metadata_payload`。
- [x] 新增下载解析接口：`/api/tasks/{task_id}/artifacts/{artifact_id}/download`。
- [x] 新增监控总览接口：`/api/admin/monitoring/overview`。
- [x] SQL：新增产物字段迁移脚本 `008_artifact_delivery_columns.sql`。

## P4 Web 层
- [x] 任务详情页新增“下载”按钮，走 API 获取下载 URL。
- [x] 后台页新增监控总览展示（adapter、运行、重试、cleanup、取消、成本）。

## P5 验证
- [x] `pytest`（api + worker）全绿。
- [x] web `npm run lint` 通过。
- [x] web `npm run build` 通过。
