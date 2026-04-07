from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_admin
from ..enums import TaskStatus
from ..models import ProviderOfferSnapshot, Task, TaskRun, User, Wallet
from ..schemas.task import (
    AdminTaskListResponse,
    AdminMonitoringOverview,
    AdminProviderHealth,
    AdminTaskSummary,
    AdminUserOverview,
    BillingProfitResponse,
    CodeEditExecutionRead,
    CodeEditRequest,
    CodeEditRollbackResponse,
    CodeEditResponse,
    TaskDetailResponse,
    TaskRead,
    TaskRunRead,
    TaskEventRead,
    ArtifactRead,
    CodeEditReviewChainRead,
)
from ..services.code_editor import CodeEditor
from ..services.tasks import (
    build_admin_summary,
    build_monitoring_overview,
    cancel_task,
    get_task_or_404,
    retry_task,
    serialize_artifacts,
    serialize_code_edit_chains,
    serialize_code_edits,
    serialize_events,
    serialize_runs,
)
from apps.worker.worker.local_executor import LocalExecutor
from apps.worker.worker.scheduler import process_pending_tasks


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/tasks", response_model=AdminTaskListResponse)
def admin_tasks(
    _: object = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminTaskListResponse:
    tasks = list(db.scalars(select(Task).order_by(Task.created_at.desc())))
    summary = AdminTaskSummary(**build_admin_summary(db))
    return AdminTaskListResponse(
        items=[TaskRead.model_validate(task) for task in tasks],
        summary=summary,
    )


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def admin_task_detail(
    task_id: int,
    _: object = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> TaskDetailResponse:
    task = get_task_or_404(db, task_id, user=None)
    runs = serialize_runs(task)
    events = serialize_events(task)
    artifacts = serialize_artifacts(task)
    code_edit_chains = serialize_code_edit_chains(task)
    code_edits = serialize_code_edits(task)
    return TaskDetailResponse(
        task=TaskRead.model_validate(task),
        current_run=TaskRunRead.model_validate(runs[0]) if runs else None,
        runs=[TaskRunRead.model_validate(run) for run in runs],
        events=[TaskEventRead.model_validate(event) for event in events],
        artifacts=[ArtifactRead.model_validate(artifact) for artifact in artifacts],
        code_edit_chains=[
            CodeEditReviewChainRead.model_validate(item) for item in code_edit_chains
        ],
        code_edits=[CodeEditExecutionRead.model_validate(item) for item in code_edits],
    )


@router.post("/tasks/{task_id}/retry", response_model=TaskRead)
def admin_retry_task(
    task_id: int,
    _: object = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> TaskRead:
    task = retry_task(db, get_task_or_404(db, task_id, user=None))
    return TaskRead.model_validate(task)


@router.post("/tasks/{task_id}/cancel", response_model=TaskRead)
def admin_cancel_task(
    task_id: int,
    _: object = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> TaskRead:
    task = cancel_task(db, get_task_or_404(db, task_id, user=None))
    return TaskRead.model_validate(task)


@router.get("/users", response_model=list[AdminUserOverview])
def admin_users(
    _: object = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AdminUserOverview]:
    users = list(db.scalars(select(User).order_by(User.created_at.desc())))
    wallet_rows = {
        int(row[0]): row
        for row in db.execute(
            select(Wallet.user_id, Wallet.balance, Wallet.frozen_balance)
        ).all()
    }
    task_rows = db.execute(
        select(
            Task.user_id,
            func.count(Task.id).label("total"),
            func.sum(case((Task.status == TaskStatus.RUNNING.value, 1), else_=0)).label("running"),
            func.sum(case((Task.status == TaskStatus.COMPLETED.value, 1), else_=0)).label("completed"),
            func.sum(case((Task.status == TaskStatus.FAILED.value, 1), else_=0)).label("failed"),
        ).group_by(Task.user_id)
    ).all()
    task_map = {int(row[0]): row for row in task_rows}
    results: list[AdminUserOverview] = []
    for user in users:
        wallet = wallet_rows.get(user.id)
        task = task_map.get(user.id)
        results.append(
            AdminUserOverview(
                id=user.id,
                email=user.email,
                role=user.role,
                status=user.status,
                wallet_balance=float(wallet[1]) if wallet else 0.0,
                frozen_balance=float(wallet[2]) if wallet else 0.0,
                total_tasks=int(task[1]) if task else 0,
                running_tasks=int(task[2]) if task else 0,
                completed_tasks=int(task[3]) if task else 0,
                failed_tasks=int(task[4]) if task else 0,
                created_at=user.created_at,
            )
        )
    return results


@router.get("/providers/health", response_model=list[AdminProviderHealth])
def provider_health(
    _: object = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AdminProviderHealth]:
    rows = db.execute(
        select(
            ProviderOfferSnapshot.provider,
            func.count(ProviderOfferSnapshot.id),
            func.avg(ProviderOfferSnapshot.price_per_hour),
            func.avg(ProviderOfferSnapshot.reliability_score),
            func.avg(ProviderOfferSnapshot.startup_score),
            func.avg(ProviderOfferSnapshot.success_rate),
        ).group_by(ProviderOfferSnapshot.provider)
    ).all()
    return [
        AdminProviderHealth(
            provider=row[0],
            offer_count=int(row[1]),
            average_price_per_hour=float(row[2] or 0),
            average_reliability=float(row[3] or 0),
            average_startup_score=float(row[4] or 0),
            average_success_rate=float(row[5] or 0),
        )
        for row in rows
    ]


@router.get("/billing/profit", response_model=BillingProfitResponse)
def billing_profit(
    _: object = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> BillingProfitResponse:
    revenue = float(db.scalar(select(func.coalesce(func.sum(Task.final_charge), 0))) or 0)
    cost = float(db.scalar(select(func.coalesce(func.sum(Task.final_cost), 0))) or 0)

    provider_rows = db.execute(
        select(
            TaskRun.provider,
            func.coalesce(func.sum(TaskRun.provider_cost), 0),
            func.count(TaskRun.id),
        ).group_by(TaskRun.provider)
    ).all()

    gross_profit = revenue - cost
    margin = (gross_profit / revenue * 100) if revenue else 0
    return BillingProfitResponse(
        revenue=round(revenue, 4),
        cost=round(cost, 4),
        gross_profit=round(gross_profit, 4),
        gross_margin=round(margin, 2),
        by_provider=[
            {
                "provider": row[0],
                "cost": float(row[1] or 0),
                "run_count": int(row[2]),
            }
            for row in provider_rows
        ],
    )


@router.get("/monitoring/overview", response_model=AdminMonitoringOverview)
def monitoring_overview(
    _: object = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminMonitoringOverview:
    return AdminMonitoringOverview(**build_monitoring_overview(db))


@router.get("/execution/health", response_model=dict)
def execution_health(_: object = Depends(get_current_admin)) -> dict:
    executor = LocalExecutor()
    return executor.healthcheck()


@router.post("/execution/run-once", response_model=dict)
def run_execution_once(_: object = Depends(get_current_admin)) -> dict:
    processed = process_pending_tasks(limit=5)
    return {
        "processed_count": len(processed),
        "items": processed,
    }


@router.post("/execution/code-edit", response_model=CodeEditResponse)
def execution_code_edit(
    payload: CodeEditRequest,
    admin: User = Depends(get_current_admin),
) -> CodeEditResponse:
    editor = CodeEditor()
    result = editor.apply_code_edit(
        payload.instructions,
        payload.files,
        payload.test_commands,
        task_id=payload.task_id,
        actor_user_id=admin.id,
        actor_email=admin.email,
    )
    return CodeEditResponse(**result)


@router.post("/execution/code-edit/preview", response_model=CodeEditResponse)
def execution_code_edit_preview(
    payload: CodeEditRequest,
    _: object = Depends(get_current_admin),
) -> CodeEditResponse:
    editor = CodeEditor()
    result = editor.preview_code_edit(payload.instructions, payload.files)
    return CodeEditResponse(**result)


@router.get("/execution/code-edits", response_model=list[CodeEditExecutionRead])
def execution_code_edit_history(
    task_id: int | None = None,
    _: object = Depends(get_current_admin),
) -> list[CodeEditExecutionRead]:
    editor = CodeEditor()
    rows = editor.list_code_edits(task_id=task_id)
    return [CodeEditExecutionRead.model_validate(row) for row in rows]


@router.post(
    "/execution/code-edit/{execution_id}/rollback",
    response_model=CodeEditRollbackResponse,
)
def execution_code_edit_rollback(
    execution_id: int,
    admin: User = Depends(get_current_admin),
) -> CodeEditRollbackResponse:
    editor = CodeEditor()
    result = editor.rollback_execution(
        execution_id,
        actor_user_id=admin.id,
        actor_email=admin.email,
    )
    return CodeEditRollbackResponse(**result)
