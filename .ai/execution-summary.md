# 执行总结（本轮）

## 已完成
- 已将项目部署到自有 VPS（`144.202.58.159`）。
- 已配置公网可访问域名：`http://gpu.144.202.58.159.sslip.io`。
- 已完成 API/Web/Worker 三服务 systemd 化：
  - `stablegpu-api.service`
  - `stablegpu-web.service`
  - `stablegpu-worker.service`
- 已完成 nginx 反代与路由拆分：
  - `/api/*`、`/docs`、`/openapi.json` -> FastAPI
  - 其他路径 -> Next.js
- 已在服务器完成依赖安装与前端生产构建：
  - Python venv + API/Worker requirements
  - `apps/web` `npm install` + `npm run build`
- 已初始化后台管理员账号：
  - `owner@example.com` / `pass1234`（role=`admin`）
- 已同步更新 `.ai/deploy-notes.md` 为自有服务器版本。
- 已新增仓库内自托管部署工具：
  - `infra/deploy/install_linux.sh`（一键部署 API/Web/Worker + nginx + systemd）
  - `infra/deploy/enable_https.sh`（Certbot/Nginx 一键启用 HTTPS）
  - `infra/deploy/switch_to_live_adapter.sh`（一键切换到 `multi_provider_live` 并重启服务）
  - `infra/deploy/README.md`（运维执行手册）

## 当前线上地址
- 网站首页：`http://gpu.144.202.58.159.sslip.io`
- API 健康检查：`http://gpu.144.202.58.159.sslip.io/api/health`
- API 文档：`http://gpu.144.202.58.159.sslip.io/docs`

## 本轮范围外（未改动）
- 未新增业务功能逻辑（本轮聚焦部署）。
- 未切换到真实 `Vast.ai/Runpod` 线上 key（代码已支持，待凭据注入）。
- 未接入正式 HTTPS 证书（当前为 HTTP 可访问版本）。

## 产物与运维状态
- 代码目录：`/opt/stablegpu/repo`
- 环境文件：`/opt/stablegpu/repo/.env`
- nginx 配置：`/etc/nginx/sites-available/stablegpu`
- 服务运行状态：三服务均为 `active (running)`。
