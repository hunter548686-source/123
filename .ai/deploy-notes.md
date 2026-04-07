# 部署说明（自有服务器正式版）

## 部署目标
- 将项目部署到自有 VPS：`144.202.58.159`
- 使用公网域名：`http://gpu.144.202.58.159.sslip.io`
- 保持现有线上业务（harbourstep/chinacare）不受影响

## 本次落地架构
- `nginx`：公网入口与反向代理
- `systemd`：托管 API/Web/Worker 三个服务
- `FastAPI`：`127.0.0.1:8000`
- `Next.js`：`127.0.0.1:3010`
- `Worker`：循环执行 `python -m apps.worker.worker.main --limit 5`
- `SQLite`：`/opt/stablegpu/repo/data/stablegpu.db`

## 部署目录
- 代码目录：`/opt/stablegpu/repo`
- Python venv：`/opt/stablegpu/venv`
- 环境文件：`/opt/stablegpu/repo/.env`

## 域名与路由
- 首页与后台：`http://gpu.144.202.58.159.sslip.io/`
- API 健康检查：`http://gpu.144.202.58.159.sslip.io/api/health`
- API 文档：`http://gpu.144.202.58.159.sslip.io/docs`

`nginx` 路由策略：
- `/api/*` -> `127.0.0.1:8000`
- `/docs` 与 `/openapi.json` -> `127.0.0.1:8000`
- 其他路径 -> `127.0.0.1:3010`

## systemd 服务
- `stablegpu-api.service`
- `stablegpu-web.service`
- `stablegpu-worker.service`

常用命令：
```bash
systemctl status stablegpu-api.service
systemctl status stablegpu-web.service
systemctl status stablegpu-worker.service
systemctl restart stablegpu-api.service stablegpu-web.service stablegpu-worker.service
journalctl -u stablegpu-api.service -n 200 --no-pager
```

## 默认管理账号（已初始化）
- Email：`owner@example.com`
- Password：`pass1234`
- Role：`admin`

## 当前关键配置
- `STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER=database_mock`
- `STABLEGPU_ENABLE_LOCAL_EXECUTOR=false`
- `NEXT_PUBLIC_API_BASE_URL=http://gpu.144.202.58.159.sslip.io`

说明：
- 代码层已支持 `vast_ai` / `runpod` / `multi_provider_live`。
- 切到真实聚合平台只需要补齐 API Key 并修改 `.env` 中 adapter 与对应凭据。

## 回滚与恢复
1. 回滚代码：
```bash
cd /opt/stablegpu/repo
git log --oneline -n 10
git checkout <commit>
```
2. 重新构建前端：
```bash
cd /opt/stablegpu/repo/apps/web
NEXT_PUBLIC_API_BASE_URL=http://gpu.144.202.58.159.sslip.io npm run build
```
3. 重启服务：
```bash
systemctl restart stablegpu-api.service stablegpu-web.service stablegpu-worker.service
```

## 仓库内可复用部署脚本（新增）
- `infra/deploy/install_linux.sh`
- `infra/deploy/enable_https.sh`
- `infra/deploy/README.md`

推荐方式：
1. 服务器拉取最新代码。
2. 运行 `bash infra/deploy/install_linux.sh` 完成依赖、构建、systemd、nginx 全链路安装。
3. 在有正式域名时运行 `bash infra/deploy/enable_https.sh` 打开 HTTPS。
