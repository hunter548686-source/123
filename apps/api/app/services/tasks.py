from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..enums import (
    EventLevel,
    StageStatus,
    TaskRunStatus,
    TaskStatus,
    WalletLedgerType,
    WorkflowStage,
)
from ..models import (
    Artifact,
    CodeEditExecution,
    CodeEditReviewChain,
    Project,
    ProviderOfferSnapshot,
    Task,
    TaskEvent,
    TaskRun,
    User,
    Wallet,
    WalletLedger,
)
from .provider_marketplace import ProviderMarketplaceService


def record_event(
    db: Session,
    task: Task,
    *,
    source: str,
    stage: str,
    level: str,
    message: str,
    detail_payload: dict[str, Any] | None = None,
) -> TaskEvent:
    event = TaskEvent(
        task_id=task.id,
        source=source,
        stage=stage,
        level=level,
        message=message,
        detail_payload=detail_payload,
    )
    db.add(event)
    db.flush()
    return event


def get_task_query(user: User, status_filter: str | None = None) -> Select[tuple[Task]]:
    query = select(Task).where(Task.user_id == user.id).order_by(Task.created_at.desc())
    if status_filter:
        query = query.where(Task.status == status_filter)
    return query


def get_task_or_404(db: Session, task_id: int, user: User | None = None) -> Task:
    query = select(Task).where(Task.id == task_id)
    if user is not None:
        query = query.where(Task.user_id == user.id)
    task = db.scalar(query.limit(1))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def get_wallet_or_404(db: Session, user: User) -> Wallet:
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id).limit(1))
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return wallet


def ensure_project_access(db: Session, user: User, project_id: int) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id, Project.user_id == user.id)
        .limit(1)
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def create_task(
    db: Session,
    *,
    user: User,
    project_id: int,
    task_type: str,
    template_id: str,
    strategy: str,
    execution_mode: str,
    input_payload: dict[str, Any],
    quote_snapshot: dict[str, Any] | None,
) -> Task:
    ensure_project_access(db, user, project_id)
    wallet = get_wallet_or_404(db, user)

    quote_price = (
        Decimal(str(quote_snapshot.get("estimated_price", 0)))
        if quote_snapshot
        else Decimal("0")
    )
    if wallet.balance < quote_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance. Recharge wallet before creating this task.",
        )

    task = Task(
        project_id=project_id,
        user_id=user.id,
        task_type=task_type,
        template_id=template_id,
        strategy=strategy,
        execution_mode=execution_mode,
        status=TaskStatus.QUEUED.value,
        workflow_stage=WorkflowStage.PLANNING.value,
        planning_status=StageStatus.PENDING.value,
        execution_status=StageStatus.PENDING.value,
        review_status=StageStatus.PENDING.value,
        input_payload=input_payload,
        quote_snapshot=quote_snapshot,
        quoted_price=quote_price if quote_price > 0 else None,
        retry_limit=int(input_payload.get("retry_limit", 2)),
        progress=5,
    )
    db.add(task)
    db.flush()

    record_event(
        db,
        task,
        source="system",
        stage=WorkflowStage.PLANNING.value,
        level=EventLevel.INFO.value,
        message="Task queued and waiting for planning/execution.",
        detail_payload={"strategy": strategy, "execution_mode": execution_mode},
    )
    db.commit()
    db.refresh(task)
    return task


def retry_task(db: Session, task: Task) -> Task:
    if task.status in {
        TaskStatus.COMPLETED.value,
        TaskStatus.CANCELLED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is already finalized",
        )
    task.status = TaskStatus.RETRYING.value
    task.workflow_stage = WorkflowStage.EXECUTION.value
    task.execution_status = StageStatus.PENDING.value
    task.review_status = StageStatus.PENDING.value
    task.last_error = None
    task.progress = 20
    record_event(
        db,
        task,
        source="system",
        stage=WorkflowStage.EXECUTION.value,
        level=EventLevel.WARN.value,
        message="Task manually moved to retry queue.",
    )
    db.commit()
    db.refresh(task)
    return task


def cancel_task(db: Session, task: Task) -> Task:
    if task.status in {
        TaskStatus.COMPLETED.value,
        TaskStatus.FAILED.value,
        TaskStatus.CANCELLED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is already finalized",
        )

    previous_status = task.status
    if task.status in {
        TaskStatus.DRAFT.value,
        TaskStatus.QUEUED.value,
        TaskStatus.RETRYING.value,
    }:
        task.status = TaskStatus.CANCELLED.value
        task.execution_status = StageStatus.SKIPPED.value
        task.review_status = StageStatus.SKIPPED.value
        task.workflow_stage = WorkflowStage.DONE.value
        task.progress = 0
        record_event(
            db,
            task,
            source="system",
            stage=WorkflowStage.EXECUTION.value,
            level=EventLevel.WARN.value,
            message="Task cancelled before remote dispatch.",
            detail_payload={"previous_status": previous_status},
        )
    else:
        task.status = TaskStatus.CANCELLING.value
        task.execution_status = StageStatus.IN_PROGRESS.value
        task.review_status = StageStatus.SKIPPED.value
        task.workflow_stage = WorkflowStage.EXECUTION.value
        record_event(
            db,
            task,
            source="system",
            stage=WorkflowStage.EXECUTION.value,
            level=EventLevel.WARN.value,
            message="Task cancellation requested and queued for worker cleanup.",
            detail_payload={"previous_status": previous_status},
        )

    db.commit()
    db.refresh(task)
    return task


def apply_wallet_charge(db: Session, task: Task) -> None:
    if task.final_charge is None:
        return
    wallet = get_wallet_or_404(db, task.user)
    wallet.balance = Decimal(wallet.balance) - Decimal(task.final_charge)
    ledger = WalletLedger(
        wallet_id=wallet.id,
        type=WalletLedgerType.CONSUME.value,
        amount=Decimal(task.final_charge),
        balance_after=Decimal(wallet.balance),
        ref_type="task",
        ref_id=str(task.id),
    )
    db.add(ledger)


def build_admin_summary(db: Session) -> dict[str, int]:
    return {
        "total": db.scalar(select(func.count()).select_from(Task)) or 0,
        "running": db.scalar(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.RUNNING.value)
        )
        or 0,
        "failed": db.scalar(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.FAILED.value)
        )
        or 0,
        "completed": db.scalar(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.COMPLETED.value)
        )
        or 0,
    }


def build_monitoring_overview(db: Session) -> dict[str, Any]:
    marketplace = ProviderMarketplaceService()
    status_breakdown = {
        status_value: db.scalar(
            select(func.count()).select_from(Task).where(Task.status == status_value)
        )
        or 0
        for status_value in [
            TaskStatus.QUEUED.value,
            TaskStatus.DISPATCHING.value,
            TaskStatus.PROVISIONING.value,
            TaskStatus.RUNNING.value,
            TaskStatus.RETRYING.value,
            TaskStatus.CANCELLING.value,
            TaskStatus.CLEANING_UP.value,
            TaskStatus.FAILED.value,
            TaskStatus.COMPLETED.value,
            TaskStatus.CANCELLED.value,
        ]
    }

    active_runs = db.scalar(
        select(func.count())
        .select_from(TaskRun)
        .where(
            TaskRun.ended_at.is_(None),
            TaskRun.status.in_(
                [
                    "instance_creating",
                    "executing",
                    "uploading",
                    "cancelling",
                    "cleaning_up",
                ]
            ),
        )
    ) or 0

    recent_provider_cost = float(
        db.scalar(select(func.coalesce(func.sum(TaskRun.provider_cost), 0))) or 0
    )
    recent_runtime_seconds = int(
        db.scalar(select(func.coalesce(func.sum(TaskRun.runtime_seconds), 0))) or 0
    )

    recent_failures = [
        {
            "task_id": task.id,
            "status": task.status,
            "provider": task.selected_provider,
            "retry_count": task.retry_count,
            "last_error": task.last_error,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
        for task in db.scalars(
            select(Task)
            .where(Task.status == TaskStatus.FAILED.value)
            .order_by(Task.updated_at.desc())
            .limit(10)
        )
    ]

    return {
        "status_breakdown": status_breakdown,
        "active_runs": int(active_runs),
        "queued_for_retry": int(status_breakdown[TaskStatus.RETRYING.value]),
        "pending_cleanup": int(status_breakdown[TaskStatus.CLEANING_UP.value]),
        "open_cancellations": int(status_breakdown[TaskStatus.CANCELLING.value]),
        "recent_provider_cost": round(recent_provider_cost, 4),
        "recent_runtime_seconds": recent_runtime_seconds,
        "adapter_key": marketplace.adapter_key,
        "marketplace_name": marketplace.marketplace_name,
        "recent_failures": recent_failures,
    }


def build_home_metrics(db: Session) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    average_delivery_seconds = float(
        db.scalar(
            select(func.avg(TaskRun.runtime_seconds)).where(
                TaskRun.status == TaskRunStatus.FINISHED.value,
                TaskRun.runtime_seconds > 0,
            )
        )
        or 0
    )

    if average_delivery_seconds <= 0:
        completed_tasks = list(
            db.scalars(
                select(Task).where(Task.status == TaskStatus.COMPLETED.value).limit(200)
            )
        )
        estimated_seconds: list[float] = []
        for task in completed_tasks:
            quote = task.quote_snapshot or {}
            if not isinstance(quote, dict):
                continue
            minutes = quote.get("estimated_runtime_minutes")
            if minutes is None:
                continue
            try:
                parsed_minutes = float(minutes)
            except (TypeError, ValueError):
                continue
            if parsed_minutes > 0:
                estimated_seconds.append(parsed_minutes * 60)
        if estimated_seconds:
            average_delivery_seconds = sum(estimated_seconds) / len(estimated_seconds)

    provider_count = int(
        db.scalar(select(func.count(func.distinct(ProviderOfferSnapshot.provider)))) or 0
    )

    final_status_rows = db.execute(
        select(Task.status, func.count(Task.id))
        .where(
            Task.updated_at >= seven_days_ago,
            Task.status.in_(
                [
                    TaskStatus.COMPLETED.value,
                    TaskStatus.FAILED.value,
                    TaskStatus.CANCELLED.value,
                ]
            ),
        )
        .group_by(Task.status)
    ).all()
    seven_day_status_counts = {str(row[0]): int(row[1]) for row in final_status_rows}
    completed_tasks_7d = seven_day_status_counts.get(TaskStatus.COMPLETED.value, 0)
    sample_size_7d = int(sum(seven_day_status_counts.values()))
    success_rate_7d = (
        round((completed_tasks_7d / sample_size_7d) * 100, 1) if sample_size_7d else 0.0
    )

    completed_total = int(
        db.scalar(
            select(func.count(Task.id)).where(Task.status == TaskStatus.COMPLETED.value)
        )
        or 0
    )
    cost_visible_total = int(
        db.scalar(
            select(func.count(Task.id)).where(
                Task.status == TaskStatus.COMPLETED.value,
                Task.final_cost.is_not(None),
                Task.final_charge.is_not(None),
            )
        )
        or 0
    )
    cost_visibility_coverage = (
        round((cost_visible_total / completed_total) * 100, 1)
        if completed_total
        else 0.0
    )

    return {
        "average_delivery_seconds": int(round(average_delivery_seconds)),
        "success_rate_7d": success_rate_7d,
        "provider_count": provider_count,
        "cost_visibility_coverage": cost_visibility_coverage,
        "sample_size_7d": sample_size_7d,
        "completed_tasks_7d": completed_tasks_7d,
        "updated_at": now,
    }


def resolve_artifact_download_url(artifact: Artifact) -> str | None:
    if artifact.download_url:
        return artifact.download_url
    if artifact.storage_path.startswith("http://") or artifact.storage_path.startswith("https://"):
        return artifact.storage_path
    return None


def serialize_artifacts(task: Task) -> list[Artifact]:
    return sorted(
        task.artifacts,
        key=lambda item: item.created_at or task.created_at,
        reverse=True,
    )


def serialize_runs(task: Task) -> list[TaskRun]:
    return sorted(task.runs, key=lambda item: item.attempt_no, reverse=True)


def serialize_events(task: Task) -> list[TaskEvent]:
    return sorted(
        task.events,
        key=lambda item: item.created_at or task.created_at,
        reverse=True,
    )


def serialize_code_edits(task: Task) -> list[CodeEditExecution]:
    return sorted(
        task.code_edit_executions,
        key=lambda item: item.created_at or task.created_at,
        reverse=True,
    )


def serialize_code_edit_chains(task: Task) -> list[CodeEditReviewChain]:
    return sorted(
        task.code_edit_review_chains,
        key=lambda item: item.created_at or task.created_at,
        reverse=True,
    )
