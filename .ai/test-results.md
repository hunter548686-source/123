# 测试结果（本轮部署验证）

## 1) 服务器服务状态验证
执行（VPS）：
```bash
systemctl status stablegpu-api.service
systemctl status stablegpu-web.service
systemctl status stablegpu-worker.service
```
结果：
- 三个服务均 `active (running)`。

## 2) 服务器本机健康检查
执行（VPS）：
```bash
curl -sSf http://127.0.0.1:8000/api/health
curl -sSf http://127.0.0.1:3010
```
结果：
- API 返回 `{"status":"ok"}`。
- Web 返回首页 HTML（200）。

## 3) nginx 反代验证
执行（VPS）：
```bash
nginx -t
curl -sSf -H "Host: gpu.144.202.58.159.sslip.io" http://127.0.0.1/api/health
```
结果：
- nginx 配置语法通过。
- Host 路由命中成功，返回 `{"status":"ok"}`。

## 4) 外网可访问性验证
执行（本机）：
```powershell
Invoke-WebRequest "http://gpu.144.202.58.159.sslip.io"
Invoke-WebRequest "http://gpu.144.202.58.159.sslip.io/api/health"
Invoke-WebRequest "http://gpu.144.202.58.159.sslip.io/admin"
```
结果：
- 三个入口均 HTTP 200。

## 5) 管理账号初始化验证
执行（VPS 数据库脚本）：
- 创建/更新 `owner@example.com`，角色 `admin`
- 钱包余额初始化 `1000.00`

结果：
- 用户存在并可用于后台登录。

## 6) 已知限制
- 当前使用 HTTP 域名，未配置 TLS 证书。
- 当前 adapter 默认 `database_mock`，真实 provider key 待注入后再切换。

