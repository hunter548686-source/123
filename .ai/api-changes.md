# API 变更

## 新增接口

### 1) 产物下载入口
- `GET /api/tasks/{task_id}/artifacts/{artifact_id}/download`
- 作用：返回可下载 URL（由 API 统一解析）。
- 返回示例：
```json
{
  "artifact_id": 12,
  "download_url": "https://download.example.com/task-12.mp4",
  "source": "download_url"
}
```

### 2) 监控总览
- `GET /api/admin/monitoring/overview`
- 作用：后台展示状态分布、运行态、重试/cleanup/取消队列、成本汇总、最近失败任务。

### 3) 首页实时指标（公开）
- `GET /api/home/metrics`
- 作用：为首页提供真实业务指标（无需登录），用于替代静态展示值。
- 返回字段：
  - `average_delivery_seconds`
  - `success_rate_7d`
  - `provider_count`
  - `cost_visibility_coverage`
  - `sample_size_7d`
  - `completed_tasks_7d`
  - `updated_at`

### 4) 后台任务运营接口
- `GET /api/admin/tasks`
  - 返回全量任务列表 + 后台汇总统计。
- `GET /api/admin/tasks/{task_id}`
  - 返回后台任务详情（run/events/artifacts/review chain）。
- `POST /api/admin/tasks/{task_id}/retry`
  - 后台手动重试任务。
- `POST /api/admin/tasks/{task_id}/cancel`
  - 后台手动取消任务。

### 5) 后台用户概览接口
- `GET /api/admin/users`
- 作用：后台查看用户角色、钱包余额、任务统计（total/running/completed/failed）。

## 现有接口响应扩展
- `GET /api/tasks/{task_id}` 的 `artifacts[]` 新增：
  - `download_url`
  - `checksum`
  - `metadata_payload`
