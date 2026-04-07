# 部署说明（自有服务器）

## 当前生产地址
- 主站（HTTPS）：`https://gpu.144.202.58.159.sslip.io`
- 主站（HTTP）：`http://gpu.144.202.58.159.sslip.io`
- API 健康检查：`https://gpu.144.202.58.159.sslip.io/api/health`
- API 文档：`https://gpu.144.202.58.159.sslip.io/docs`

## 服务器与运行形态
- VPS：`144.202.58.159`
- 代码目录：`/opt/stablegpu/repo`
- Python 环境：`/opt/stablegpu/venv`
- 环境文件：`/opt/stablegpu/repo/.env`
- 数据库：`sqlite:///opt/stablegpu/repo/data/stablegpu.db`

服务：
- `stablegpu-api.service`
- `stablegpu-web.service`
- `stablegpu-worker.service`

## Nginx 路由
- `/api/*` -> `127.0.0.1:8000`
- `/docs`、`/openapi.json` -> `127.0.0.1:8000`
- 其他路径 -> `127.0.0.1:3010`

## HTTPS 状态
- 已使用 `certbot + nginx` 成功签发并部署证书
- 证书域名：`gpu.144.202.58.159.sslip.io`
- 到期时间（服务器输出）：`2026-07-06`
- 自动续期任务由 certbot 创建

## 可复用部署脚本
- `infra/deploy/install_linux.sh`
- `infra/deploy/enable_https.sh`
- `infra/deploy/switch_to_live_adapter.sh`
- `infra/deploy/provider_preflight.py`
- `infra/deploy/README.md`

## 真实 Provider 切换说明
默认仍为：
- `STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER=database_mock`

切换到真实多 provider：
1. 配置密钥：
   - `STABLEGPU_VAST_AI_API_KEY`
   - `STABLEGPU_RUNPOD_API_KEY`
2. 执行：
```bash
bash infra/deploy/switch_to_live_adapter.sh
```
3. 预检：
```bash
python3 infra/deploy/provider_preflight.py
```

## 当前阻塞点
- 未在本机/服务器/桌面密码资料中发现可用的 `Vast.ai` 与 `Runpod` 生产 API Key。
- 在缺少密钥前，不建议将线上默认 adapter 从 `database_mock` 强制切为 `multi_provider_live`，否则会导致执行链路不稳定。

