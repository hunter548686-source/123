# 线上验收报告（2026-04-08）

## 验收范围
- HTTPS 可用性
- Web/API 可访问性
- 后台入口可访问性
- Provider 切换准备度

## 环境信息
- 服务器：`144.202.58.159`
- 域名：`gpu.144.202.58.159.sslip.io`
- 部署路径：`/opt/stablegpu/repo`

## 验收结果
1. HTTPS：
   - 通过
   - 访问 `https://gpu.144.202.58.159.sslip.io` 正常返回 200
2. API：
   - 通过
   - `https://gpu.144.202.58.159.sslip.io/api/health` 返回 `{"status":"ok"}`
3. 后台入口：
   - 通过
   - `/admin` 可访问，登录接口可用
4. Worker：
   - 通过
   - `stablegpu-worker.service` 运行中
5. 真实 Provider 切换：
   - 部分通过（切换机制完成，生产密钥缺失）
   - `switch_to_live_adapter.sh` 与 `provider_preflight.py` 已就绪
   - Vast 真实报价接口可用（`/bundles/`）
   - Runpod 因缺 API Key 预检返回 401

## 结论
- 网站已达到“HTTPS + 自有服务器可生产访问”标准。
- 真实 Vast/Runpod 全量上线只差最后一步：注入生产 API Key 后执行切换脚本并复验。

## 上线后最终操作清单
1. 在服务器注入：
   - `STABLEGPU_VAST_AI_API_KEY`
   - `STABLEGPU_RUNPOD_API_KEY`
2. 执行：
```bash
bash infra/deploy/switch_to_live_adapter.sh
python3 infra/deploy/provider_preflight.py
```
3. 验证：
   - 后台监控 `adapter_key` 应为 `multi_provider_live`
   - 创建一条真实小任务并确认完成、成本、产物可回收

