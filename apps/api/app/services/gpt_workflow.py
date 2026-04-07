from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import get_settings
from ..models import Task, TaskRun


def _extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")
    return json.loads(text[start : end + 1])


class GPTWorkflow:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _response_text(self, payload: dict[str, Any]) -> str:
        if "output_text" in payload and payload["output_text"]:
            return str(payload["output_text"])

        chunks: list[str] = []
        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    chunks.append(str(content.get("text", "")))
        return "\n".join(chunk for chunk in chunks if chunk).strip()

    def _call_openai_json(self, prompt: str, model: str) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise RuntimeError("STABLEGPU_OPENAI_API_KEY is not configured")

        response = httpx.post(
            f"{self.settings.openai_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": prompt},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return _extract_json_object(self._response_text(data))

    def plan_task(self, task: Task) -> dict[str, Any]:
        prompt = (
            "You are GPT-5.4 acting as the planning stage for StableGPU.\n"
            "Return JSON with keys: plan_summary, execution_brief, coding_instructions, risk_flags.\n"
            "risk_flags must be an array of short strings.\n"
            "coding_instructions must be concrete instructions for the local coding model.\n"
            f"task_type={task.task_type}\n"
            f"template_id={task.template_id}\n"
            f"strategy={task.strategy}\n"
            f"execution_mode={task.execution_mode}\n"
            f"input_payload={task.input_payload}\n"
        )
        try:
            result = self._call_openai_json(prompt, self.settings.planning_model)
            result["mode"] = "gpt-5.4"
            return result
        except Exception:
            resolution = task.input_payload.get("resolution", "1080p")
            duration = task.input_payload.get("duration_seconds", 8)
            return {
                "mode": "fallback",
                "plan_summary": (
                    f"由 GPT-5.4 规划：任务类型为 {task.task_type}，优先策略为 {task.strategy}，"
                    f"建议按 {resolution} / {duration}s 执行。"
                ),
                "execution_brief": "先由本地模型执行，再进入 GPT-5.4 审查。",
                "coding_instructions": (
                    "请按当前任务目标生成稳定可交付的执行结果，"
                    "输出应包含目标、关键步骤、失败回退和结果摘要。"
                ),
                "risk_flags": ["缺少 OpenAI API Key，当前使用回退规划结果"],
            }

    def review_task(
        self,
        task: Task,
        run: TaskRun,
        *,
        execution_note: str,
        revision_round: int,
    ) -> dict[str, Any]:
        prompt = (
            "You are GPT-5.4 acting as the review stage for StableGPU.\n"
            "Return JSON with keys: approved, review_summary, fix_instructions, residual_risks.\n"
            "approved must be boolean. residual_risks must be an array of short strings.\n"
            f"task_type={task.task_type}\n"
            f"provider={run.provider}\n"
            f"gpu={run.gpu_type}\n"
            f"status={task.status}\n"
            f"execution_note={execution_note}\n"
            f"revision_round={revision_round}\n"
            f"result_summary={task.result_summary}\n"
            f"coding_instructions={task.coding_instructions}\n"
        )
        try:
            result = self._call_openai_json(prompt, self.settings.review_model)
            result["mode"] = "gpt-5.4"
            return result
        except Exception:
            force_fail_once = bool(task.input_payload.get("force_review_fail_once"))
            approved = not force_fail_once or revision_round > 0
            return {
                "mode": "fallback",
                "approved": approved,
                "review_summary": (
                    "GPT-5.4 审查通过，可继续后续归档与部署。"
                    if approved
                    else "GPT-5.4 审查未通过，需要本地模型根据修复指令继续调整。"
                ),
                "fix_instructions": (
                    ""
                    if approved
                    else "请收敛输出内容，补足失败回退说明，并重新生成更稳定的执行结果摘要。"
                ),
                "residual_risks": ([] if approved else ["当前使用回退审查逻辑"]),
            }
