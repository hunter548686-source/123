# 部署说明（本轮）

## 新增配置项
- Vast.ai:
  - `STABLEGPU_VAST_AI_BASE_URL`
  - `STABLEGPU_VAST_AI_API_KEY`
  - `STABLEGPU_VAST_AI_*_PATH*`
- Runpod:
  - `STABLEGPU_RUNPOD_BASE_URL`
  - `STABLEGPU_RUNPOD_API_KEY`
  - `STABLEGPU_RUNPOD_*_PATH*`

## 推荐 adapter
- 生产建议：`STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER=multi_provider_live`
- 开发回归可用：`database_mock`

## 发布检查
1. 执行 DB 迁移至 `008`。
2. 校验 provider API key 已注入。
3. 后台账号初始化：首个注册用户为 `admin`，用于访问 `/api/admin/*` 与后台页面。
4. 校验 CORS 包含 Web 端口：
   - `http://localhost:3000`
   - `http://127.0.0.1:3000`
   - `http://localhost:3010`
   - `http://127.0.0.1:3010`
5. 健康检查：
   - `GET /api/admin/monitoring/overview`
   - `GET /api/admin/tasks`
   - `GET /api/admin/users`
   - `GET /api/home/metrics`
   - 创建任务并验证产物下载入口。
