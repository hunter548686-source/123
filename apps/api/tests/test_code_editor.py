from __future__ import annotations

import json
from pathlib import Path

from apps.api.app.config import get_settings
from apps.api.app.database import init_db, reset_database, session_scope
from apps.api.app.models import CodeEditExecution
from apps.api.app.services.code_editor import CodeEditor


def test_code_editor_preview_does_not_write_file(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "sample.txt"
    target.write_text("hello world", encoding="utf-8")

    monkeypatch.setenv("STABLEGPU_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("STABLEGPU_ENABLE_LOCAL_EXECUTOR", "true")
    get_settings.cache_clear()

    def fake_run_prompt(self, prompt: str, model: str | None = None):
        return {
            "mode": "test-local-model",
            "note": json.dumps(
                {
                    "summary": "preview sample file",
                    "operations": [
                        {"path": "sample.txt", "old": "hello world", "new": "hello stablegpu"}
                    ],
                }
            ),
        }

    monkeypatch.setattr("apps.worker.worker.local_executor.LocalExecutor.run_prompt", fake_run_prompt)

    editor = CodeEditor()
    result = editor.preview_code_edit("update greeting", ["sample.txt"])

    assert result["operations_count"] == 1
    assert "hello stablegpu" in result["diff_preview"]
    assert target.read_text(encoding="utf-8") == "hello world"
    get_settings.cache_clear()


def test_code_editor_apply_writes_file_and_runs_tests(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "sample.txt"
    target.write_text("hello world", encoding="utf-8")
    db_path = tmp_path / "code-edit.db"

    monkeypatch.setenv("STABLEGPU_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("STABLEGPU_ENABLE_LOCAL_EXECUTOR", "true")
    reset_database(f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    init_db()

    def fake_run_prompt(self, prompt: str, model: str | None = None):
        return {
            "mode": "test-local-model",
            "note": json.dumps(
                {
                    "summary": "updated sample file",
                    "operations": [
                        {"path": "sample.txt", "old": "hello world", "new": "hello stablegpu"}
                    ],
                }
            ),
        }

    monkeypatch.setattr("apps.worker.worker.local_executor.LocalExecutor.run_prompt", fake_run_prompt)

    editor = CodeEditor()
    result = editor.apply_code_edit(
        "update greeting",
        ["sample.txt"],
        ["python -c \"print('ok')\""],
        actor_user_id=1,
        actor_email="admin@example.com",
    )

    assert result["operations_count"] == 1
    assert result["changed_files"] == ["sample.txt"]
    assert result["test_results"][0]["returncode"] == 0
    assert "ok" in result["test_results"][0]["stdout"]
    assert target.read_text(encoding="utf-8") == "hello stablegpu"
    assert result["execution_id"] is not None

    with session_scope() as db:
        execution = db.get(CodeEditExecution, result["execution_id"])
        assert execution is not None
        assert execution.actor_email == "admin@example.com"
        assert execution.rollback_status == "available"
        assert len(execution.files) == 1
        assert execution.files[0].before_content == "hello world"
        assert execution.files[0].after_content == "hello stablegpu"
    get_settings.cache_clear()


def test_code_editor_rollback_restores_previous_file(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "sample.txt"
    target.write_text("hello world", encoding="utf-8")
    db_path = tmp_path / "rollback.db"

    monkeypatch.setenv("STABLEGPU_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("STABLEGPU_ENABLE_LOCAL_EXECUTOR", "true")
    reset_database(f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    init_db()

    def fake_run_prompt(self, prompt: str, model: str | None = None):
        return {
            "mode": "test-local-model",
            "note": json.dumps(
                {
                    "summary": "updated sample file",
                    "operations": [
                        {"path": "sample.txt", "old": "hello world", "new": "hello stablegpu"}
                    ],
                }
            ),
        }

    monkeypatch.setattr("apps.worker.worker.local_executor.LocalExecutor.run_prompt", fake_run_prompt)

    editor = CodeEditor()
    result = editor.apply_code_edit(
        "update greeting",
        ["sample.txt"],
        [],
        actor_user_id=1,
        actor_email="admin@example.com",
    )
    rollback = editor.rollback_execution(
        result["execution_id"],
        actor_user_id=2,
        actor_email="reviewer@example.com",
    )

    assert rollback["rollback_status"] == "completed"
    assert rollback["restored_files"] == ["sample.txt"]
    assert target.read_text(encoding="utf-8") == "hello world"

    with session_scope() as db:
        execution = db.get(CodeEditExecution, result["execution_id"])
        assert execution is not None
        assert execution.status == "rolled_back"
        assert execution.rollback_status == "completed"
        assert execution.rollback_actor_email == "reviewer@example.com"
        assert execution.rolled_back_at is not None
    get_settings.cache_clear()
