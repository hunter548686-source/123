from __future__ import annotations

from pathlib import Path

from apps.api.app.database import init_db, reset_database, session_scope
from apps.api.app.models import Artifact, Project, Task, TaskRun, User, Wallet
from apps.api.app.services.bootstrap import seed_provider_offers
from apps.api.app.services.security import hash_password
from apps.worker.worker.scheduler import process_pending_tasks


def test_worker_retries_and_completes(tmp_path: Path):
    db_path = tmp_path / "worker.db"
    reset_database(f"sqlite:///{db_path.as_posix()}")
    init_db()
    with session_scope() as db:
        seed_provider_offers(db)
        user = User(
            email="worker@example.com",
            password_hash=hash_password("pass1234"),
            role="admin",
        )
        db.add(user)
        db.flush()
        db.add(Wallet(user_id=user.id, balance=100))
        project = Project(user_id=user.id, name="worker", scene_type="video_generation")
        db.add(project)
        db.flush()
        db.add(
            Task(
                project_id=project.id,
                user_id=user.id,
                task_type="text_to_video",
                template_id="wanx-v1",
                strategy="cheap",
                input_payload={"prompt": "night city", "duration_seconds": 8, "force_failure_once": True},
                quote_snapshot={"estimated_runtime_minutes": 12},
                quoted_price=10,
            )
        )

    result = process_pending_tasks(limit=5)
    assert result
    assert result[0]["status"] == "completed"
    assert result[0]["retry_count"] == 1

    with session_scope() as db:
        latest_run = db.query(TaskRun).order_by(TaskRun.id.desc()).first()
        latest_task = db.query(Task).order_by(Task.id.desc()).first()
        artifacts = db.query(Artifact).order_by(Artifact.id.asc()).all()
        assert latest_run is not None
        assert latest_task is not None
        assert latest_run.external_task_id is not None
        assert latest_task.result_summary
        assert artifacts
        assert artifacts[0].storage_path.endswith(".mp4")
        assert artifacts[0].download_url is not None


def test_worker_processes_cancelling_tasks(tmp_path: Path):
    db_path = tmp_path / "worker-cancel.db"
    reset_database(f"sqlite:///{db_path.as_posix()}")
    init_db()
    with session_scope() as db:
        seed_provider_offers(db)
        user = User(
            email="cancel@example.com",
            password_hash=hash_password("pass1234"),
            role="admin",
        )
        db.add(user)
        db.flush()
        db.add(Wallet(user_id=user.id, balance=100))
        project = Project(user_id=user.id, name="worker-cancel", scene_type="video_generation")
        db.add(project)
        db.flush()

        task = Task(
            project_id=project.id,
            user_id=user.id,
            task_type="text_to_video",
            template_id="wanx-v1",
            strategy="stable",
            status="cancelling",
            workflow_stage="execution",
            execution_status="in_progress",
            review_status="skipped",
            input_payload={"prompt": "cancel flow"},
            quote_snapshot={"estimated_runtime_minutes": 8},
            quoted_price=8,
        )
        db.add(task)
        db.flush()
        db.add(
            TaskRun(
                task_id=task.id,
                attempt_no=1,
                provider="runpod",
                gpu_type="RTX 4090",
                runtime_target="hybrid",
                status="executing",
                external_task_id="database_mock-task-cancel-1",
            )
        )

    result = process_pending_tasks(limit=5)
    assert result
    assert result[0]["status"] == "cancelled"

    with session_scope() as db:
        latest_run = db.query(TaskRun).order_by(TaskRun.id.desc()).first()
        latest_task = db.query(Task).order_by(Task.id.desc()).first()
        assert latest_run is not None
        assert latest_task is not None
        assert latest_task.status == "cancelled"
        assert latest_run.status == "cancelled"
