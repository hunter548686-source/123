# 当前阶段验收标准

## A. Provider Adapter
- [x] 可通过配置切换 `vast_ai` / `runpod` / `multi_provider_live`。
- [x] adapter 具备五动作：报价、下发、状态、取消、结果回收，并支持 cleanup。
- [x] `database_mock` 与 `remote_marketplace` 不回归。

## B. 状态机与执行链路
- [x] 状态机包含 `cancelling` 与 `cleaning_up`。
- [x] 用户取消后不直接硬改终态，worker 会完成 cancel+cleanup 再终态。
- [x] 失败会触发 cleanup，并进入 retry/fail 判定。
- [x] 失败迁移时会排除已失败 provider。

## C. 交付闭环
- [x] 任务产物落库包含下载地址/校验信息。
- [x] 任务详情可触发下载 URL 获取并下载。
- [x] 成本字段可回写（run.provider_cost, task.final_cost/final_charge）。

## D. 监控可见性
- [x] 后台可查看状态分布、运行中、重试队列、cleanup 队列、取消中数量。
- [x] 后台可查看 adapter 标识与成本运行汇总。

## E. 可验证性
- [x] 自动化测试通过。
- [x] 前端 lint/build 通过。
