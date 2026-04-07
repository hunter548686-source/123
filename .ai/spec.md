# 当前阶段规格（真实 Provider + 完整状态机 + 交付闭环）

## 阶段目标
1. 接入真实 `Vast.ai` / `Runpod` adapter（保留 mock）。
2. 把取消、失败迁移、重试、cleanup 做成完整状态机链路。
3. 打通真实成本、产物归档、下载入口、后台监控总览。

## 范围
- Web 系统层：
  - 任务详情页支持产物下载动作。
  - 管理后台展示监控总览（adapter、运行中、重试、cleanup、取消、成本）。
- API 层：
  - 新增 `GET /api/tasks/{task_id}/artifacts/{artifact_id}/download`
  - 新增 `GET /api/admin/monitoring/overview`
  - 扩展 artifact 字段（download_url/checksum/metadata_payload）。
- 调度/Agent 层：
  - 状态机新增 `cancelling` / `cleaning_up`。
  - worker 在失败与取消链路上执行 provider cleanup。
  - 失败重试保持 provider 迁移（排除失败 provider）。
- Provider 适配层：
  - 新增 `vast_ai` / `runpod` adapter。
  - 新增 `multi_provider_live` 聚合路由 adapter。
  - 统一支持 `cleanup_task` 契约。

## 非目标
- 不把本地 WSL/Ollama 作为网站生产算力来源。
- 不做无关重构和 UI 大改版。
- 不引入新的云基础设施。

## 关键约束
- 最小正确实现，优先稳定交付闭环。
- 所有改动可测试、可追踪、可审查。
- 保持 `database_mock` / `remote_marketplace` 兼容可用。
