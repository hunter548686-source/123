# 必须修复项（当前轮次）

1. 生产环境尚未注入真实 provider 密钥：
   - `STABLEGPU_VAST_AI_API_KEY`
   - `STABLEGPU_RUNPOD_API_KEY`

影响：
- 无法完成 `multi_provider_live` 的真实执行链路验收（尤其 Runpod 下发与状态查询）。

