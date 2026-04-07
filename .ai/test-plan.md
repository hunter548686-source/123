# 当前阶段测试计划

## 1. Adapter 契约测试
- `test_provider_marketplace.py`
  - database mock 五动作 + cleanup。
  - remote marketplace 五动作 + cleanup。
  - vast/runpod payload 归一化。
  - base URL 缺失错误路径。

## 2. 端到端任务流测试
- `test_auth_wallet_tasks.py`
  - 注册/充值/报价/创建任务/worker 执行。
  - 产物下载入口可返回 download_url。
  - 后台监控接口可返回有效结构。

## 3. Worker 状态流测试
- `test_worker_flow.py`
  - 失败后迁移重试并最终完成。
  - cancelling 任务可走 cancel+cleanup 后终态 cancelled。

## 4. Web 验证
- `npm run lint`
- `npm run build`

## 5. 回归关注点
- 旧 adapter（database_mock/remote_marketplace）兼容性。
- 任务详情与后台页在新字段下不崩溃。
