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

## 代码仓库
- GitHub: `https://github.com/hunter548686-source/123`
- 分支：`main`

## 外网可访问地址（当前会话）
- Web: `https://yesterday-cheque-great-meals.trycloudflare.com`
- API: `https://valid-occurs-algorithm-sleeping.trycloudflare.com`
- API Docs: `https://valid-occurs-algorithm-sleeping.trycloudflare.com/docs`

说明：
- 当前使用 Cloudflare Quick Tunnel，链接是临时地址，进程中断后会变化。
- Web 构建时已注入 `NEXT_PUBLIC_API_BASE_URL` 指向当前 API 外网地址。
- API 启动时已注入 `STABLEGPU_CORS_ORIGINS`，允许当前 Web 外网域名跨域访问。

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
