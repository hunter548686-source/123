from __future__ import annotations

import json
import subprocess

import httpx

from apps.api.app.config import get_settings
from apps.api.app.models import Task, TaskRun


class LocalExecutor:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _run_wsl(self, script: str, timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["wsl", "-d", self.settings.wsl_distro, "bash", "-lc", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def healthcheck(self) -> dict[str, str]:
        if not self.settings.enable_local_executor:
            return {"mode": "simulated", "status": "disabled"}

        try:
            probe = self._run_wsl(
                f"curl -sS {self.settings.ollama_base_url.rstrip('/')}/api/tags >/dev/null",
                timeout=10,
            )
            if probe.returncode == 0:
                return {"mode": "wsl-to-windows-ollama", "status": "ready"}
            return {"mode": "wsl-to-windows-ollama", "status": "degraded"}
        except Exception:
            return {"mode": "wsl-to-windows-ollama", "status": "degraded"}

    def _run_wsl_http_prompt(self, prompt: str, model: str) -> dict[str, str]:
        body = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            ensure_ascii=True,
        )
        escaped_body = body.replace("'", "'\"'\"'")
        script = (
            "curl -sS "
            f"{self.settings.ollama_base_url.rstrip('/')}/api/chat "
            "-H 'Content-Type: application/json' "
            f"-d '{escaped_body}'"
        )
        result = self._run_wsl(script, timeout=int(self.settings.ollama_request_timeout_seconds))
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "WSL curl call failed")

        payload = json.loads(result.stdout)
        message = payload.get("message", {})
        content = message.get("content") or payload.get("response") or ""
        return {
            "mode": "wsl-to-windows-ollama",
            "model": model,
            "note": content.strip()[:1000] or "Ollama returned an empty response.",
        }

    def _run_windows_http_fallback(self, prompt: str, model: str) -> dict[str, str]:
        response = httpx.post(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=self.settings.ollama_request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        message = payload.get("message", {})
        content = message.get("content") or payload.get("response") or ""
        return {
            "mode": "windows-ollama-fallback",
            "model": model,
            "note": content.strip()[:1000] or "Ollama returned an empty response.",
        }

    def run_prompt(self, prompt: str, *, model: str | None = None) -> dict[str, str]:
        active_model = model or self.settings.ollama_model
        if not self.settings.enable_local_executor:
            return {
                "mode": "simulated",
                "model": active_model,
                "note": f"Simulated WSL -> Windows Ollama execution for prompt: {prompt[:96]}",
            }

        try:
            return self._run_wsl_http_prompt(prompt, active_model)
        except Exception as exc:
            try:
                fallback = self._run_windows_http_fallback(prompt, active_model)
                fallback["fallback_reason"] = str(exc)
                return fallback
            except Exception as fallback_exc:
                return {
                    "mode": "wsl-to-windows-ollama",
                    "model": active_model,
                    "note": f"Local executor failed: {fallback_exc}",
                    "fallback_reason": str(exc),
                }

    def prepare_bundle(self, prompt: str) -> dict[str, str]:
        bundle_prompt = (
            "Turn the following task input into a short execution bundle. "
            "Respond in 3 lines max with goal, risks, and fallback.\n"
            f"{prompt}"
        )
        return self.run_prompt(bundle_prompt, model=self.settings.ollama_model)

    def plan_task(self, task: Task) -> dict[str, str]:
        prompt = (
            "You are the StableGPU local planning node. "
            "Return a concise Chinese plan with risks and retry guidance.\n"
            f"Task type: {task.task_type}\n"
            f"Template: {task.template_id}\n"
            f"Strategy: {task.strategy}\n"
            f"Execution mode: {task.execution_mode}\n"
            f"Input: {task.input_payload}\n"
        )
        return self.run_prompt(
            prompt,
            model=self.settings.ollama_planner_model or self.settings.ollama_model,
        )

    def review_task(self, task: Task, run: TaskRun) -> dict[str, str]:
        prompt = (
            "You are the StableGPU local review node. "
            "Return a concise Chinese review covering delivery readiness and residual risk.\n"
            f"Task type: {task.task_type}\n"
            f"Provider: {run.provider}\n"
            f"GPU: {run.gpu_type}\n"
            f"Runtime seconds: {run.runtime_seconds}\n"
            f"Task status: {task.status}\n"
            f"Result summary: {task.result_summary}\n"
        )
        return self.run_prompt(
            prompt,
            model=self.settings.ollama_reviewer_model or self.settings.ollama_model,
        )
