# 测试结果（2026-04-08）

## A. HTTPS 验收
命令（本机）：
```powershell
Invoke-WebRequest "https://gpu.144.202.58.159.sslip.io"
Invoke-WebRequest "https://gpu.144.202.58.159.sslip.io/api/health"
```

结果：
- 首页：HTTP 200
- 健康检查：HTTP 200，返回 `{"status":"ok"}`

## B. 服务状态验收（VPS）
命令：
```bash
systemctl status stablegpu-api.service
systemctl status stablegpu-web.service
systemctl status stablegpu-worker.service
```

结果：
- 三个服务均为 `active (running)`。

## C. Provider 连通性预检
脚本：
```bash
python3 infra/deploy/provider_preflight.py
```

本轮验证结果：
- Vast.ai：可连通，`/bundles/` 返回有效 `offers[]`
- Runpod：无 API Key 情况下 `/v1/pods` 返回 `401 Unauthorized`

结论：
- Vast 报价链路具备真实数据来源基础。
- Runpod 真实调用仍需生产 API Key。

## D. 自动化回归（本地）
命令：
```powershell
python -m pytest .\apps\api\tests .\apps\worker\tests
```

结果：
- `15 passed`

