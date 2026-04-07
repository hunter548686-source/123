# Agent / 调度流（本轮版本）

## 主流程
1. `planning`：生成 plan_summary / execution_brief / coding_instructions。
2. `execution`：
   - 选 provider（报价评分）
   - 下发任务
   - 轮询状态
   - 失败则 cleanup + retry/fail
   - 成功则收集结果 + post-result cleanup
3. `review`：审查通过则完成，不通过则返工重试。

## 取消链
- 用户取消请求：
  - 非运行态：直接 `cancelled`
  - 运行态：进入 `cancelling`
- worker 执行：
  - provider cancel
  - provider cleanup
  - 终态 `cancelled`

## 失败迁移链
- 失败后进入 cleanup。
- cleanup 后执行 `fail_or_retry`。
- 若 retry：排除失败 provider，重新调度。
- 若无重试预算：终态 `failed`。

## Provider 层
- `vast_ai` adapter
- `runpod` adapter
- `multi_provider_live`：对外统一接口，内部按 provider 路由动作。
