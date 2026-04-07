# 执行总结（本轮）

## 已完成
- 接入真实 provider adapter：
  - `vast_ai`
  - `runpod`
  - `multi_provider_live`（聚合路由）
- 扩展 marketplace 契约，新增 `cleanup_task`。
- 完整状态机链路落地：
  - 取消链：`cancelling -> cleaning_up -> cancelled`
  - 失败链：`cleaning_up -> retrying/failed`
  - 成功链：结果回收后执行 cleanup。
- 成本与产物闭环：
  - run/provider 成本回写
  - artifact 新增下载地址、校验值与元数据
  - 任务详情支持下载动作
- 监控打通：
  - 新增后台监控总览 API
  - 后台页面展示运行、重试、cleanup、取消、adapter 与成本信息
- 完成成品首页改版（面向用户交付场景）：
  - 移除内部研发流程话术（本地模型/规划执行细节）
  - 突出“任务创建 -> 调度执行 -> 失败迁移 -> 结果归档”闭环
  - 增加任务列表、账单中心、控制台、运维后台入口
- 首页指标动态化：
  - 新增公开接口 `GET /api/home/metrics`
  - 首页四个核心指标改为实时 API 数据驱动（不再依赖静态写死值）
  - 指标覆盖交付时长、7日成功率、可用 provider 数、成本可视化覆盖率
- 后台运营闭环补齐：
  - 新增后台任务接口：`/api/admin/tasks`、`/api/admin/tasks/{task_id}`、`retry/cancel`
  - 新增后台用户概览接口：`/api/admin/users`
  - 新增页面：`/admin/users`、`/admin/tasks/[taskId]`
  - 后台任务台升级为全量任务运营台（筛选 + 手动干预 + 详情入口）

## 关键实现文件
- `apps/api/app/services/provider_marketplace.py`
- `apps/worker/worker/scheduler.py`
- `apps/api/app/enums.py`
- `apps/api/app/models.py`
- `apps/api/app/services/tasks.py`
- `apps/api/app/routes/tasks.py`
- `apps/api/app/routes/admin.py`
- `apps/api/app/routes/providers.py`
- `apps/api/app/schemas/task.py`
- `apps/web/src/lib/api.ts`
- `apps/web/src/lib/mock.ts`
- `apps/web/src/components/console-shell.tsx`
- `apps/web/src/app/tasks/[taskId]/page.tsx`
- `apps/web/src/app/admin/page.tsx`
- `apps/web/src/app/admin/tasks/page.tsx`
- `apps/web/src/app/admin/tasks/[taskId]/page.tsx`
- `apps/web/src/app/admin/users/page.tsx`
- `apps/web/src/app/page.tsx`

## 数据与配置
- 新增 SQL 迁移：`infra/sql/008_artifact_delivery_columns.sql`
- 更新 `.env` 示例，补充 vast/runpod 配置项。
- API 默认 CORS 放开 `3000/3010` 本地端口，支持首页实时指标跨端口读取。
