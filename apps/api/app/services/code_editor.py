from __future__ import annotations

import difflib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.worker.worker.local_executor import LocalExecutor

from ..config import get_settings
from ..database import session_scope
from ..models import (
    CodeEditExecution,
    CodeEditExecutionFile,
    CodeEditReviewChain,
    Task,
    TaskEvent,
)


class CodeEditError(RuntimeError):
    pass


def _extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise CodeEditError("Local model did not return JSON")
    return json.loads(text[start : end + 1])


class CodeEditor:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.executor = LocalExecutor()
        self.workspace_root = Path(self.settings.workspace_root).resolve()

    def _resolve_path(self, relative_path: str) -> Path:
        candidate = (self.workspace_root / relative_path).resolve()
        if self.workspace_root not in candidate.parents and candidate != self.workspace_root:
            raise CodeEditError(f"Path escapes workspace: {relative_path}")
        return candidate

    def _collect_context(self, files: list[str]) -> list[dict[str, str]]:
        selected = files[: self.settings.code_edit_max_files]
        contexts: list[dict[str, str]] = []
        for relative_path in selected:
            path = self._resolve_path(relative_path)
            if not path.exists():
                raise CodeEditError(f"File not found: {relative_path}")
            content = path.read_text(encoding="utf-8")
            contexts.append(
                {
                    "path": relative_path,
                    "content": content[: self.settings.code_edit_max_chars_per_file],
                }
            )
        return contexts

    def _build_prompt(self, instructions: str, files: list[dict[str, str]]) -> str:
        return (
            "You are qwen2.5-coder acting as the StableGPU local code executor.\n"
            "Return ONLY valid JSON with keys: summary, operations.\n"
            "operations must be an array of objects with keys: path, old, new.\n"
            "Use exact string replacement operations only. Do not invent files outside the provided list.\n"
            f"Instructions:\n{instructions}\n"
            f"Files:\n{json.dumps(files, ensure_ascii=False)}"
        )

    def _normalize_operations(self, operations: Any) -> list[dict[str, str]]:
        if not isinstance(operations, list) or not operations:
            raise CodeEditError("No valid code edit operations returned")
        normalized_operations: list[dict[str, str]] = []
        for item in operations:
            if not isinstance(item, dict):
                raise CodeEditError("Invalid operation entry")
            path = str(item.get("path", ""))
            old = str(item.get("old", ""))
            new = str(item.get("new", ""))
            if not path or old == "":
                raise CodeEditError("Operation must include path and old")
            normalized_operations.append({"path": path, "old": old, "new": new})
        return normalized_operations

    def _build_plan(
        self, operations: list[dict[str, str]]
    ) -> tuple[list[dict[str, str]], list[str]]:
        plans: list[dict[str, str]] = []
        diffs: list[str] = []
        for operation in operations:
            relative_path = operation["path"]
            old = operation["old"]
            new = operation["new"]
            path = self._resolve_path(relative_path)
            content = path.read_text(encoding="utf-8")
            if old not in content:
                raise CodeEditError(f"Original snippet not found in {relative_path}")
            if content.count(old) > 1:
                raise CodeEditError(f"Original snippet is not unique in {relative_path}")
            updated = content.replace(old, new, 1)
            diff = "\n".join(
                difflib.unified_diff(
                    content.splitlines(),
                    updated.splitlines(),
                    fromfile=relative_path,
                    tofile=relative_path,
                    lineterm="",
                )
            )
            plans.append(
                {
                    "path": relative_path,
                    "before_content": content,
                    "after_content": updated,
                }
            )
            diffs.append(diff)
        return plans, diffs

    def _apply_plans(self, plans: list[dict[str, str]]) -> None:
        for plan in plans:
            path = self._resolve_path(plan["path"])
            path.write_text(plan["after_content"], encoding="utf-8")

    def _run_test_commands(self, test_commands: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for command in test_commands[: self.settings.code_edit_max_test_commands]:
            completed = subprocess.run(
                command,
                cwd=self.workspace_root,
                shell=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
            results.append(
                {
                    "command": command,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout[-4000:],
                    "stderr": completed.stderr[-4000:],
                }
            )
        return results

    def _generate_operations(
        self, instructions: str, files: list[str]
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        list[dict[str, str]],
        list[dict[str, str]],
        list[str],
    ]:
        file_context = self._collect_context(files)
        model_result = self.executor.run_prompt(self._build_prompt(instructions, file_context))
        payload = _extract_json_object(model_result["note"])
        operations = self._normalize_operations(payload.get("operations"))
        plans, diffs = self._build_plan(operations)
        return model_result, payload, operations, plans, diffs

    def _get_or_create_active_chain(
        self, db: Any, task: Task
    ) -> CodeEditReviewChain:
        chain = (
            db.query(CodeEditReviewChain)
            .filter(
                CodeEditReviewChain.task_id == task.id,
                CodeEditReviewChain.status.in_(["awaiting_review", "changes_requested"]),
            )
            .order_by(CodeEditReviewChain.created_at.desc())
            .first()
        )
        if chain is not None:
            return chain
        chain = CodeEditReviewChain(
            task_id=task.id,
            status="awaiting_review",
            started_review_round=task.review_round,
            current_review_round=task.review_round,
        )
        db.add(chain)
        db.flush()
        return chain

    def _record_execution(
        self,
        *,
        task_id: int | None,
        actor_user_id: int | None,
        actor_email: str | None,
        instructions: str,
        requested_files: list[str],
        operations: list[dict[str, str]],
        plans: list[dict[str, str]],
        diff_preview: str,
        test_commands: list[str],
        test_results: list[dict[str, Any]],
        model_mode: str | None,
        raw_model_note: str | None,
        summary: str,
    ) -> dict[str, Any]:
        with session_scope() as db:
            task: Task | None = None
            chain: CodeEditReviewChain | None = None
            workflow_stage: str | None = None
            review_round: int | None = None
            review_approved: bool | None = None

            if task_id is not None:
                task = db.get(Task, task_id)
                if task is None:
                    raise CodeEditError(f"Task not found: {task_id}")
                workflow_stage = task.workflow_stage
                review_round = task.review_round
                review_approved = task.review_approved
                chain = self._get_or_create_active_chain(db, task)
                chain.total_executions += 1
                chain.current_review_round = task.review_round
                chain.status = "awaiting_review"

            execution = CodeEditExecution(
                task_id=task_id,
                review_chain_id=chain.id if chain is not None else None,
                actor_user_id=actor_user_id,
                actor_email=actor_email,
                chain_step_no=chain.total_executions if chain is not None else None,
                review_chain_status=chain.status if chain is not None else None,
                workflow_stage=workflow_stage,
                review_round=review_round,
                review_approved=review_approved,
                status="applied",
                summary=summary,
                instructions=instructions,
                requested_files=requested_files,
                changed_files=[operation["path"] for operation in operations],
                operations_count=len(operations),
                diff_preview=diff_preview,
                test_commands=test_commands,
                test_results=test_results,
                model_mode=model_mode,
                raw_model_note=raw_model_note,
                rollback_status="available",
            )
            db.add(execution)
            db.flush()

            for plan in plans:
                db.add(
                    CodeEditExecutionFile(
                        execution_id=execution.id,
                        path=plan["path"],
                        before_content=plan["before_content"],
                        after_content=plan["after_content"],
                    )
                )

            if task is not None:
                db.add(
                    TaskEvent(
                        task_id=task.id,
                        source="code_editor",
                        stage=workflow_stage or "execution",
                        level="info",
                        message="本地代码执行器已记录一次与任务关联的代码修改。",
                        detail_payload={
                            "execution_id": execution.id,
                            "review_chain_id": chain.id if chain is not None else None,
                            "chain_step_no": execution.chain_step_no,
                            "review_round": review_round,
                            "review_approved": review_approved,
                            "changed_files": [operation["path"] for operation in operations],
                        },
                    )
                )

            db.flush()
            return {
                "execution_id": int(execution.id),
                "review_chain_id": int(chain.id) if chain is not None else None,
                "chain_step_no": execution.chain_step_no,
                "review_chain_status": execution.review_chain_status,
            }

    def preview_code_edit(self, instructions: str, files: list[str]) -> dict[str, Any]:
        model_result, payload, operations, _plans, diffs = self._generate_operations(
            instructions, files
        )
        changed_files = [operation["path"] for operation in operations]
        return {
            "summary": str(payload.get("summary") or "Preview generated."),
            "mode": str(model_result.get("mode") or "unknown"),
            "changed_files": changed_files,
            "operations_count": len(operations),
            "diff_preview": "\n\n".join(diff for diff in diffs if diff),
            "test_results": [],
            "raw_model_note": model_result.get("note"),
        }

    def apply_code_edit(
        self,
        instructions: str,
        files: list[str],
        test_commands: list[str] | None = None,
        *,
        task_id: int | None = None,
        actor_user_id: int | None = None,
        actor_email: str | None = None,
    ) -> dict[str, Any]:
        model_result, payload, operations, plans, diffs = self._generate_operations(
            instructions, files
        )
        self._apply_plans(plans)
        normalized_test_commands = (test_commands or [])[
            : self.settings.code_edit_max_test_commands
        ]
        test_results = self._run_test_commands(normalized_test_commands)
        diff_preview = "\n\n".join(diff for diff in diffs if diff)
        summary = str(payload.get("summary") or "Local code edit applied.")
        execution_record = self._record_execution(
            task_id=task_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            instructions=instructions,
            requested_files=files,
            operations=operations,
            plans=plans,
            diff_preview=diff_preview,
            test_commands=normalized_test_commands,
            test_results=test_results,
            model_mode=str(model_result.get("mode") or "unknown"),
            raw_model_note=model_result.get("note"),
            summary=summary,
        )
        return {
            "summary": summary,
            "mode": str(model_result.get("mode") or "unknown"),
            "changed_files": [operation["path"] for operation in operations],
            "operations_count": len(operations),
            "execution_id": execution_record["execution_id"],
            "task_id": task_id,
            "review_chain_id": execution_record["review_chain_id"],
            "chain_step_no": execution_record["chain_step_no"],
            "review_chain_status": execution_record["review_chain_status"],
            "workflow_stage": self._lookup_task_stage(task_id),
            "review_round": self._lookup_task_review_round(task_id),
            "review_approved": self._lookup_task_review_approved(task_id),
            "diff_preview": diff_preview,
            "test_results": test_results,
            "raw_model_note": model_result.get("note"),
            "rollback_status": "available",
        }

    def _lookup_task_stage(self, task_id: int | None) -> str | None:
        if task_id is None:
            return None
        with session_scope() as db:
            task = db.get(Task, task_id)
            return task.workflow_stage if task is not None else None

    def _lookup_task_review_round(self, task_id: int | None) -> int | None:
        if task_id is None:
            return None
        with session_scope() as db:
            task = db.get(Task, task_id)
            return task.review_round if task is not None else None

    def _lookup_task_review_approved(self, task_id: int | None) -> bool | None:
        if task_id is None:
            return None
        with session_scope() as db:
            task = db.get(Task, task_id)
            return task.review_approved if task is not None else None

    def list_code_edits(
        self, limit: int = 20, task_id: int | None = None
    ) -> list[CodeEditExecution]:
        with session_scope() as db:
            query = db.query(CodeEditExecution)
            if task_id is not None:
                query = query.filter(CodeEditExecution.task_id == task_id)
            rows = query.order_by(CodeEditExecution.created_at.desc()).limit(limit).all()
            for row in rows:
                row.files
            return rows

    def list_code_edit_chains(
        self, task_id: int, limit: int = 10
    ) -> list[CodeEditReviewChain]:
        with session_scope() as db:
            rows = (
                db.query(CodeEditReviewChain)
                .filter(CodeEditReviewChain.task_id == task_id)
                .order_by(CodeEditReviewChain.created_at.desc())
                .limit(limit)
                .all()
            )
            for row in rows:
                row.executions
            return rows

    def sync_task_review_chain(
        self,
        *,
        task_id: int,
        review_round: int,
        approved: bool,
        review_summary: str | None,
        fix_instructions: str | None,
        terminal: bool,
        db: Any | None = None,
    ) -> None:
        if db is not None:
            chain = (
                db.query(CodeEditReviewChain)
                .filter(
                    CodeEditReviewChain.task_id == task_id,
                    CodeEditReviewChain.status.in_(
                        ["awaiting_review", "changes_requested"]
                    ),
                )
                .order_by(CodeEditReviewChain.created_at.desc())
                .first()
            )
            if chain is None:
                return

            chain.current_review_round = review_round
            chain.latest_review_summary = review_summary
            chain.latest_fix_instructions = fix_instructions

            if approved:
                chain.status = "approved"
                chain.final_review_approved = True
                chain.final_review_summary = review_summary
                chain.closed_at = datetime.now(timezone.utc)
            elif terminal:
                chain.status = "failed"
                chain.final_review_approved = False
                chain.final_review_summary = review_summary
                chain.closed_at = datetime.now(timezone.utc)
            else:
                chain.status = "changes_requested"

            for execution in chain.executions:
                execution.review_round = review_round
                execution.review_approved = approved if (approved or terminal) else False
                execution.review_chain_status = chain.status

            db.add(
                TaskEvent(
                    task_id=task_id,
                    source="review_chain",
                    stage="review",
                    level="success" if approved else ("error" if terminal else "warn"),
                    message=(
                        "代码返工链审查已通过。"
                        if approved
                        else "代码返工链审查已失败。"
                        if terminal
                        else "代码返工链收到新的修复要求。"
                    ),
                    detail_payload={
                        "review_chain_id": chain.id,
                        "status": chain.status,
                        "review_round": review_round,
                        "final_review_approved": chain.final_review_approved,
                    },
                )
            )
            db.flush()
            return

        with session_scope() as scoped_db:
            self.sync_task_review_chain(
                task_id=task_id,
                review_round=review_round,
                approved=approved,
                review_summary=review_summary,
                fix_instructions=fix_instructions,
                terminal=terminal,
                db=scoped_db,
            )

    def rollback_execution(
        self,
        execution_id: int,
        *,
        actor_user_id: int | None = None,
        actor_email: str | None = None,
    ) -> dict[str, Any]:
        with session_scope() as db:
            execution = db.get(CodeEditExecution, execution_id)
            if execution is None:
                raise CodeEditError(f"Execution not found: {execution_id}")
            if execution.rollback_status == "completed":
                raise CodeEditError(f"Execution already rolled back: {execution_id}")
            if not execution.files:
                raise CodeEditError(f"Execution has no file snapshots: {execution_id}")

            restored_files: list[str] = []
            for snapshot in execution.files:
                path = self._resolve_path(snapshot.path)
                path.write_text(snapshot.before_content, encoding="utf-8")
                restored_files.append(snapshot.path)

            execution.status = "rolled_back"
            execution.rollback_status = "completed"
            execution.rollback_error = None
            execution.rollback_actor_user_id = actor_user_id
            execution.rollback_actor_email = actor_email
            execution.rolled_back_at = datetime.now(timezone.utc)

            if execution.review_chain is not None and execution.review_chain.status in {
                "awaiting_review",
                "changes_requested",
            }:
                execution.review_chain.status = "changes_requested"
                execution.review_chain.latest_fix_instructions = (
                    execution.review_chain.latest_fix_instructions
                    or "A linked code execution was rolled back and needs a new revision."
                )

            if execution.task_id is not None:
                db.add(
                    TaskEvent(
                        task_id=execution.task_id,
                        source="code_editor",
                        stage=execution.workflow_stage or "execution",
                        level="warn",
                        message="本地代码执行器已按执行快照回滚与任务关联的代码修改。",
                        detail_payload={
                            "execution_id": execution.id,
                            "review_chain_id": execution.review_chain_id,
                            "restored_files": restored_files,
                            "review_round": execution.review_round,
                        },
                    )
                )

            db.flush()
            return {
                "execution_id": execution_id,
                "rollback_status": execution.rollback_status,
                "restored_files": restored_files,
                "message": "Rollback completed.",
            }
