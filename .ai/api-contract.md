# API 契约（本轮增量）

## 1. 任务产物下载 URL
### Request
- `GET /api/tasks/{task_id}/artifacts/{artifact_id}/download`

### Response 200
```json
{
  "artifact_id": 1,
  "download_url": "https://download.example.com/task-1.mp4",
  "source": "download_url"
}
```

### Error
- `404`：artifact 不存在或不属于该任务。
- `409`：产物尚无可下载 URL。

## 2. 后台监控总览
### Request
- `GET /api/admin/monitoring/overview`

### Response 200（示例）
```json
{
  "status_breakdown": {
    "queued": 2,
    "running": 3,
    "retrying": 1,
    "cancelling": 0,
    "cleaning_up": 1,
    "failed": 4,
    "completed": 8,
    "cancelled": 1
  },
  "active_runs": 3,
  "queued_for_retry": 1,
  "pending_cleanup": 1,
  "open_cancellations": 0,
  "recent_provider_cost": 123.45,
  "recent_runtime_seconds": 9876,
  "adapter_key": "multi_provider_live",
  "marketplace_name": "vast-runpod-live",
  "recent_failures": []
}
```

## 3. 任务详情产物字段扩展
`GET /api/tasks/{task_id}` 中的 `artifacts[]` 新增：
- `download_url: string | null`
- `checksum: string | null`
- `metadata_payload: object | null`

## 4. 首页实时指标（公开接口）
### Request
- `GET /api/home/metrics`

### Response 200（示例）
```json
{
  "average_delivery_seconds": 520,
  "success_rate_7d": 97.6,
  "provider_count": 3,
  "cost_visibility_coverage": 100.0,
  "sample_size_7d": 42,
  "completed_tasks_7d": 41,
  "updated_at": "2026-04-08T01:12:00+00:00"
}
```

## 5. 后台任务运营接口
### Request
- `GET /api/admin/tasks`
- `GET /api/admin/tasks/{task_id}`
- `POST /api/admin/tasks/{task_id}/retry`
- `POST /api/admin/tasks/{task_id}/cancel`

### Response（`GET /api/admin/tasks` 示例）
```json
{
  "items": [
    {
      "id": 1024,
      "status": "running",
      "workflow_stage": "execution"
    }
  ],
  "summary": {
    "total": 30,
    "running": 4,
    "failed": 2,
    "completed": 20
  }
}
```

## 6. 后台用户概览接口
### Request
- `GET /api/admin/users`

### Response 200（示例）
```json
[
  {
    "id": 1,
    "email": "owner@example.com",
    "role": "admin",
    "status": "active",
    "wallet_balance": 328.4,
    "frozen_balance": 36.0,
    "total_tasks": 12,
    "running_tasks": 1,
    "completed_tasks": 10,
    "failed_tasks": 1,
    "created_at": "2026-04-06T10:00:00+08:00"
  }
]
```
