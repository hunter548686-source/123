# 测试结果（本轮）

## 后端/Worker
命令：
```powershell
python -m pytest .\apps\api\tests .\apps\worker\tests
```
结果：
- `15 passed`
- 新增/更新的 adapter、取消/cleanup 状态链、下载与监控接口测试均通过。
- 新增后台任务运营接口测试通过（admin tasks detail/retry/cancel + admin users）。

补充验证（首页实时指标 API）：
- `GET /api/home/metrics` 已纳入后端测试断言，验证通过。

## 端到端链路验收
命令：
```powershell
@'
...（TestClient 脚本：register -> recharge -> quote -> create task -> process_pending_tasks -> task detail -> home metrics）
'@ | python -
```
结果：
- `task_status: completed`
- `run_count: 1`
- `artifact_count: 1`
- `home_success_rate_7d: 100.0`
- `home_provider_count: 3`

## Web
命令：
```powershell
npm run lint
npm run build
```
目录：`apps/web`

结果：
- lint 通过
- build 通过（Next.js 16.2.2）

## 可视化验证
命令：
```powershell
playwright.exe screenshot --device="Desktop Chrome" --wait-for-timeout=2500 --full-page http://localhost:3010 "apps/web/homepage-live-metrics.png"
```
结果：
- 首页可访问（`http://localhost:3010`，HTTP 200）
- 首页指标卡已显示实时 API 值（`15m 00s / 100.0% / 3 / 100.0%`）。
- 生成实拍截图：`apps/web/homepage-live-metrics.png`

后台页面补充：
- `apps/web/admin-tasks-final.png`
- `apps/web/admin-users-final.png`
- 未登录访问后台时返回 `Not authenticated`（符合权限边界预期）。

补充：
- 生产构建启动验证：`http://localhost:3010`（`npm run start -- --hostname 0.0.0.0 --port 3010`）
- API 服务启动验证：`http://127.0.0.1:8000`（`python -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000`）
