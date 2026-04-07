# StableGPU / 算力共享网站

## 项目定义

这是一个网站系统。

网站正式对外提供服务时，调用的是外部聚合算力平台/provider，而不是开发者本地机器。

本地 `WSL + Ollama` 只用于开发辅助，不是网站正式运行架构。

## 系统结构

- `apps/web`：用户站点、任务页面、后台管理
- `apps/api`：认证、任务、钱包、报价、后台接口
- `apps/worker`：provider 调度、重试迁移、状态回写
- 外部 provider：提供真实 GPU 算力

## 本地运行

### API

```powershell
python -m pip install -r .\apps\api\requirements.txt
python -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Worker

```powershell
python -m apps.worker.worker.main --limit 5
```

### Web

```powershell
cd .\apps\web
npm install
npm run dev
```

## 当前主线目标

- 真实 provider adapter
- 实时报价与调度
- 自动重试与失败迁移
- 成本可视化
- 结果归档与交付
