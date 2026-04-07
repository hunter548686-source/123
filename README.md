# StableGPU / 算力共享网站

## 项目定义

这是一个网站系统。

网站正式对外提供服务时，调用的是外部聚合算力平台 / provider，而不是开发者本地机器。

本地 `WSL + Ollama` 只用于开发这个网站时的辅助执行，不是网站正式运行架构。

## 正式产品架构

- `apps/web`：用户站点、任务页、后台
- `apps/api`：认证、任务、钱包、报价、后台接口
- `apps/worker`：调度外部 provider、处理任务状态、重试、迁移、回写结果
- 外部 provider / 聚合平台：提供真实 GPU 算力

## 本地开发运行

### 1. API

```powershell
python -m pip install -r .\apps\api\requirements.txt
python -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Worker

```powershell
python -m apps.worker.worker.main --limit 5
```

### 3. Web

```powershell
cd .\apps\web
npm install
npm run dev
```

## 本地开发辅助工具

如果你要在开发网站时启用本地模型辅助，可配置：

```env
STABLEGPU_ENABLE_LOCAL_EXECUTOR=true
STABLEGPU_WSL_DISTRO=Ubuntu-24.04
STABLEGPU_OLLAMA_MODEL=qwen2.5-coder:7b
STABLEGPU_OLLAMA_BASE_URL=http://host.docker.internal:11434
```

这部分仅用于开发辅助，不是网站生产运行依赖。

## 当前正式主线

后续应优先推进：

- 真实 provider adapter
- 实时报价与调度
- 自动重试与失败迁移
- 成本可视化
- 结果归档与交付
