from __future__ import annotations

import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.config import get_settings
from apps.api.app.database import session_scope
from apps.api.app.enums import (
    EventLevel,
    StageStatus,
    TaskContext,
    TaskRunStatus,
    TaskStateMachine,
    TaskStatus,
    WorkflowStage,
)
from apps.api.app.models import Artifact, Task, TaskRun
from apps.api.app.services.code_editor import CodeEditor
from apps.api.app.services.gpt_workflow import GPTWorkflow
from apps.api.app.services.provider_marketplace import (
    ProviderMarketplaceError,
    ProviderMarketplaceResult,
    ProviderMarketplaceService,
    ProviderMarketplaceTaskStatus,
)
from apps.api.app.services.providers import score_offers
from apps.api.app.services.tasks import apply_wallet_charge, record_event


REMOTE_SUBMITTED_STATUSES = {
    "accepted",
    "booting",
    "pending",
    "provisioning",
    "queued",
    "starting",
    "submitted",
}
REMOTE_RUNNING_STATUSES = {
    "executing",
    "in_progress",
    "processing",
    "rendering",
    "running",
}
REMOTE_UPLOADING_STATUSES = {
    "collecting_result",
    "finalizing",
    "uploading",
}
REMOTE_SUCCESS_STATUSES = {
    "completed",
    "done",
    "finished",
    "succeeded",
    "success",
}
REMOTE_FAILURE_STATUSES = {
    "error",
    "failed",
}
REMOTE_CANCELLED_STATUSES = {
    "canceled",
    "cancelled",
}


class TaskCancellationRequested(RuntimeError):
    pass


def _sync_task_from_context(task: Task, ctx: TaskContext) -> None:
    task.status = ctx.status.value
    task.retry_count = ctx.retry_count


def _normalize_remote_status(value: str | None) -> str:
    return str(value or "").strip().lower()


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _update_remote_progress(task: Task, progress_percent: int) -> None:
    bounded = max(0, min(progress_percent, 99))
    task.progress = max(task.progress, bounded)


def _should_fail(task: Task, provider: str, attempt_no: int) -> bool:
    if bool(task.input_payload.get("force_failure_once")) and attempt_no == 1:
        return True
    if task.strategy == "cheap" and provider == "vast.ai" and attempt_no == 1:
        return True
    return False


def _mark_task_failure(
    db: Session,
    task: Task,
    ctx: TaskContext,
    *,
    stage: WorkflowStage,
    source: str,
    message: str,
    detail_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _sync_task_from_context(task, ctx)
    task.execution_status = StageStatus.FAILED.value
    task.review_status = StageStatus.SKIPPED.value
    task.workflow_stage = WorkflowStage.DONE.value
    record_event(
        db,
        task,
        source=source,
        stage=stage.value,
        level=EventLevel.ERROR.value,
        message=message,
        detail_payload=detail_payload,
    )
    return {"status": task.status, "selected_provider": task.selected_provider}


def _cleanup_remote_resources(
    db: Session,
    task: Task,
    run: TaskRun,
    marketplace: ProviderMarketplaceService,
    *,
    reason: str,
) -> None:
    if not run.external_task_id:
        return
    run.status = TaskRunStatus.CLEANING_UP.value
    record_event(
        db,
        task,
        source="marketplace",
        stage=WorkflowStage.EXECUTION.value,
        level=EventLevel.INFO.value,
        message="Starting provider cleanup.",
        detail_payload={
            "external_task_id": run.external_task_id,
            "provider": run.provider,
            "reason": reason,
        },
    )
    try:
        cleanup_result = marketplace.cleanup_task(db, run.external_task_id)
    except ProviderMarketplaceError as exc:
        record_event(
            db,
            task,
            source="marketplace",
            stage=WorkflowStage.EXECUTION.value,
            level=EventLevel.WARN.value,
            message="Provider cleanup failed.",
            detail_payload={
                "external_task_id": run.external_task_id,
                "provider": run.provider,
                "reason": reason,
                "error": str(exc),
            },
        )
        return

    record_event(
        db,
        task,
        source="marketplace",
        stage=WorkflowStage.EXECUTION.value,
        level=EventLevel.SUCCESS.value if cleanup_result.cleaned else EventLevel.WARN.value,
        message="Provider cleanup finished.",
        detail_payload={
            "external_task_id": cleanup_result.external_task_id,
            "status": cleanup_result.status,
            "provider": cleanup_result.provider or run.provider,
            "cleaned": cleanup_result.cleaned,
            "message": cleanup_result.message,
        },
    )


def _cancel_active_run(
    db: Session,
    task: Task,
    run: TaskRun | None,
    ctx: TaskContext,
    machine: TaskStateMachine,
    marketplace: ProviderMarketplaceService,
) -> dict[str, Any]:
    if ctx.status != TaskStatus.CANCELLING:
        machine.begin_cancelling(ctx)
    _sync_task_from_context(task, ctx)
    task.workflow_stage = WorkflowStage.EXECUTION.value
    task.execution_status = StageStatus.IN_PROGRESS.value
    task.review_status = StageStatus.SKIPPED.value

    if run is not None:
        run.status = TaskRunStatus.CANCELLING.value
        run.fail_reason = "cancel requested by user"
        if run.external_task_id:
            try:
                cancel_result = marketplace.cancel_task(db, run.external_task_id)
                record_event(
                    db,
                    task,
                    source="marketplace",
                    stage=WorkflowStage.EXECUTION.value,
                    level=EventLevel.INFO.value,
                    message="Cancellation sent to provider.",
                    detail_payload={
                        "external_task_id": cancel_result.external_task_id,
                        "provider": cancel_result.provider or run.provider,
                        "status": cancel_result.status,
                        "cancelled": cancel_result.cancelled,
                        "message": cancel_result.message,
                    },
                )
            except ProviderMarketplaceError as exc:
                record_event(
                    db,
                    task,
                    source="marketplace",
                    stage=WorkflowStage.EXECUTION.value,
                    level=EventLevel.WARN.value,
                    message="Provider cancellation request failed; proceeding with cleanup.",
                    detail_payload={
                        "external_task_id": run.external_task_id,
                        "provider": run.provider,
                        "error": str(exc),
                    },
                )

        machine.begin_cleanup(ctx, "cancel cleanup")
        _sync_task_from_context(task, ctx)
        _cleanup_remote_resources(
            db,
            task,
            run,
            marketplace,
            reason="user_cancel",
        )
        run.status = TaskRunStatus.CANCELLED.value
        run.ended_at = datetime.now(UTC)

    if ctx.status == TaskStatus.CLEANING_UP:
        machine.cancel(ctx)
    elif ctx.status != TaskStatus.CANCELLED:
        machine.cancel(ctx)
    _sync_task_from_context(task, ctx)

    task.execution_status = StageStatus.FAILED.value
    task.review_status = StageStatus.SKIPPED.value
    task.workflow_stage = WorkflowStage.DONE.value
    task.progress = 0
    task.last_error = "cancelled by user"
    record_event(
        db,
        task,
        source="scheduler",
        stage=WorkflowStage.EXECUTION.value,
        level=EventLevel.SUCCESS.value,
        message="Task cancelled and cleanup chain completed.",
    )
    return {
        "status": task.status,
        "selected_provider": task.selected_provider,
        "retry_count": task.retry_count,
    }


def _apply_remote_status(
    db: Session,
    task: Task,
    run: TaskRun,
    ctx: TaskContext,
    machine: TaskStateMachine,
    status: ProviderMarketplaceTaskStatus,
    *,
    previous_signature: tuple[str, str, int, str, str] | None,
) -> tuple[str, str, int, str, str]:
    status_key = _normalize_remote_status(status.status)
    stage_key = _normalize_remote_status(status.stage)
    progress_percent = max(0, min(status.progress_percent, 100))

    if status.provider:
        run.provider = status.provider
        task.selected_provider = status.provider
    if status.gpu_type:
        run.gpu_type = status.gpu_type
        task.selected_gpu_type = status.gpu_type

    if status.message:
        task.result_summary = status.message

    if status_key in REMOTE_SUBMITTED_STATUSES:
        run.status = TaskRunStatus.INSTANCE_CREATING.value
        _update_remote_progress(task, max(progress_percent, 40))
    elif status_key in REMOTE_RUNNING_STATUSES:
        if ctx.status == TaskStatus.PROVISIONING:
            machine.start_run(ctx)
            _sync_task_from_context(task, ctx)
        run.status = TaskRunStatus.EXECUTING.value
        _update_remote_progress(task, max(progress_percent, 55))
    elif status_key in REMOTE_UPLOADING_STATUSES:
        if ctx.status == TaskStatus.PROVISIONING:
            machine.start_run(ctx)
            _sync_task_from_context(task, ctx)
        run.status = TaskRunStatus.UPLOADING.value
        _update_remote_progress(task, max(progress_percent, 85))
    elif status_key in REMOTE_SUCCESS_STATUSES:
        if ctx.status == TaskStatus.PROVISIONING:
            machine.start_run(ctx)
            _sync_task_from_context(task, ctx)
        run.status = TaskRunStatus.FINISHED.value
        _update_remote_progress(task, 92)
    elif status_key in REMOTE_FAILURE_STATUSES | REMOTE_CANCELLED_STATUSES:
        if ctx.status == TaskStatus.PROVISIONING:
            machine.start_run(ctx)
            _sync_task_from_context(task, ctx)
        run.status = TaskRunStatus.ERROR.value

    signature = (
        status_key,
        stage_key,
        progress_percent,
        status.provider or "",
        status.message or "",
    )
    if signature != previous_signature:
        record_event(
            db,
            task,
            source="marketplace",
            stage=WorkflowStage.EXECUTION.value,
            level=EventLevel.INFO.value,
            message="Marketplace status synced.",
            detail_payload={
                "external_task_id": status.external_task_id,
                "status": status.status,
                "stage": status.stage,
                "progress_percent": progress_percent,
                "provider": status.provider,
                "gpu_type": status.gpu_type,
                "retryable": status.retryable,
                "message": status.message,
            },
        )
    return signature


def _poll_remote_status(
    db: Session,
    task: Task,
    run: TaskRun,
    *,
    ctx: TaskContext,
    machine: TaskStateMachine,
    marketplace: ProviderMarketplaceService,
    should_cancel: Callable[[], bool],
) -> ProviderMarketplaceTaskStatus:
    settings = get_settings()
    signature: tuple[str, str, int, str, str] | None = None
    last_status: ProviderMarketplaceTaskStatus | None = None

    for poll_index in range(settings.worker_poll_max_attempts):
        if should_cancel():
            raise TaskCancellationRequested("Task cancellation requested during polling")

        status = marketplace.get_task_status(db, run.external_task_id or "")
        signature = _apply_remote_status(
            db,
            task,
            run,
            ctx,
            machine,
            status,
            previous_signature=signature,
        )
        last_status = status
        status_key = _normalize_remote_status(status.status)
        if (
            status_key in REMOTE_SUCCESS_STATUSES
            or status_key in REMOTE_FAILURE_STATUSES
            or status_key in REMOTE_CANCELLED_STATUSES
        ):
            return status

        if poll_index + 1 < settings.worker_poll_max_attempts and settings.worker_poll_interval > 0:
            time.sleep(settings.worker_poll_interval)

    raise ProviderMarketplaceError(
        "Marketplace task did not reach a terminal state within the polling window"
        if last_status is None
        else (
            "Marketplace task did not reach a terminal state within the polling window: "
            f"{last_status.status}"
        )
    )


def _apply_remote_result(
    db: Session,
    task: Task,
    run: TaskRun,
    result: ProviderMarketplaceResult,
    fallback_price: Decimal,
    fallback_runtime_seconds: int,
) -> None:
    if not result.artifacts:
        raise ProviderMarketplaceError(
            "Marketplace result did not include any delivery artifacts"
        )

    for artifact in result.artifacts:
        db.add(
            Artifact(
                task_id=task.id,
                type=artifact.kind,
                storage_path=artifact.uri,
                download_url=artifact.download_url,
                file_size=artifact.size_bytes or 0,
                checksum=artifact.checksum,
                metadata_payload=artifact.metadata or None,
            )
        )

    usage = dict(result.usage or {})
    runtime_seconds = (
        _coerce_int(usage.get("billable_seconds"))
        or _coerce_int(usage.get("runtime_seconds"))
        or _coerce_int(usage.get("duration_seconds"))
        or fallback_runtime_seconds
    )
    provider_cost = (
        _coerce_decimal(usage.get("provider_cost"))
        or _coerce_decimal(usage.get("actual_cost"))
        or _coerce_decimal(usage.get("cost"))
        or _coerce_decimal(usage.get("estimated_cost"))
        or fallback_price
    )

    run.status = TaskRunStatus.FINISHED.value
    run.runtime_seconds = runtime_seconds
    run.provider_cost = provider_cost
    run.ended_at = datetime.now(UTC)

    task.final_cost = Decimal(task.final_cost or 0) + Decimal(provider_cost)
    task.final_charge = Decimal(task.quoted_price or provider_cost)
    task.progress = 92
    task.result_summary = result.summary or task.result_summary
    task.execution_status = StageStatus.COMPLETED.value
    task.workflow_stage = WorkflowStage.REVIEW.value
    task.review_status = StageStatus.IN_PROGRESS.value

    record_event(
        db,
        task,
        source="marketplace",
        stage=WorkflowStage.EXECUTION.value,
        level=EventLevel.SUCCESS.value,
        message="Marketplace result collected.",
        detail_payload={
            "external_task_id": result.external_task_id,
            "status": result.status,
            "provider": result.provider,
            "artifact_count": len(result.artifacts),
            "provider_cost": str(provider_cost),
            "runtime_seconds": runtime_seconds,
        },
    )


def _run_failure_transition(
    db: Session,
    task: Task,
    run: TaskRun,
    ctx: TaskContext,
    machine: TaskStateMachine,
    marketplace: ProviderMarketplaceService,
    *,
    reason: str,
    previous_providers: set[str],
    source: str,
    error_message: str,
) -> tuple[TaskContext, bool]:
    run.status = TaskRunStatus.ERROR.value
    run.fail_reason = reason
    run.ended_at = datetime.now(UTC)
    task.last_error = reason
    previous_providers.add(run.provider)

    if ctx.status in {TaskStatus.PROVISIONING, TaskStatus.RUNNING, TaskStatus.CHECKPOINTING}:
        machine.begin_cleanup(ctx, "failure cleanup")
        _sync_task_from_context(task, ctx)
    _cleanup_remote_resources(db, task, run, marketplace, reason="failure")

    ctx = machine.fail_or_retry(ctx, reason)
    _sync_task_from_context(task, ctx)
    if ctx.status == TaskStatus.RETRYING:
        task.progress = 28
        record_event(
            db,
            task,
            source=source,
            stage=WorkflowStage.EXECUTION.value,
            level=EventLevel.WARN.value,
            message="Attempt failed; migrated to retry with provider failover.",
            detail_payload={
                "provider": run.provider,
                "external_task_id": run.external_task_id,
                "reason": reason,
                "retry_count": ctx.retry_count,
                "excluded_providers": sorted(previous_providers),
            },
        )
        return ctx, True

    _mark_task_failure(
        db,
        task,
        ctx,
        stage=WorkflowStage.EXECUTION,
        source=source,
        message=error_message,
        detail_payload={
            "provider": run.provider,
            "external_task_id": run.external_task_id,
            "reason": reason,
        },
    )
    return ctx, False


def _execute_task(db: Session, task: Task) -> dict[str, Any]:
    settings = get_settings()
    machine = TaskStateMachine()
    gpt_workflow = GPTWorkflow()
    code_editor = CodeEditor()
    marketplace = ProviderMarketplaceService()
    ctx = TaskContext(
        task_id=str(task.id),
        status=TaskStatus(task.status),
        retry_count=task.retry_count,
        max_retries=task.retry_limit,
    )

    task.workflow_stage = WorkflowStage.PLANNING.value
    task.planning_status = StageStatus.IN_PROGRESS.value
    record_event(
        db,
        task,
        source="planner",
        stage=WorkflowStage.PLANNING.value,
        level=EventLevel.INFO.value,
        message="Planning started.",
    )
    planner_result = gpt_workflow.plan_task(task)
    task.plan_summary = str(planner_result["plan_summary"])
    task.execution_brief = str(planner_result["execution_brief"])
    task.coding_instructions = str(planner_result["coding_instructions"])
    task.planning_status = StageStatus.COMPLETED.value
    record_event(
        db,
        task,
        source="planner",
        stage=WorkflowStage.PLANNING.value,
        level=EventLevel.SUCCESS.value,
        message="Planning completed.",
        detail_payload=planner_result,
    )

    previous_providers: set[str] = set()
    review_round = 0

    while True:
        task.workflow_stage = WorkflowStage.EXECUTION.value
        task.execution_status = StageStatus.IN_PROGRESS.value

        if ctx.status == TaskStatus.QUEUED:
            machine.dispatch(ctx)
        elif ctx.status == TaskStatus.RETRYING:
            machine.redispatch(ctx)
        _sync_task_from_context(task, ctx)

        record_event(
            db,
            task,
            source="scheduler",
            stage=WorkflowStage.EXECUTION.value,
            level=EventLevel.INFO.value,
            message="Selecting provider candidates.",
            detail_payload={"excluded_providers": sorted(previous_providers)},
        )

        offers = marketplace.list_offers(db)
        ranked = score_offers(
            offers,
            task.strategy,
            exclude_providers=previous_providers,
            estimated_runtime_minutes=int(task.quote_snapshot.get("estimated_runtime_minutes", 12))
            if task.quote_snapshot
            else 12,
        )
        if not ranked:
            ctx = machine.fail_or_retry(ctx, "no provider available")
            return _mark_task_failure(
                db,
                task,
                ctx,
                stage=WorkflowStage.EXECUTION,
                source="scheduler",
                message="No provider is available for this task.",
            )

        best = ranked[0]
        machine.provision(ctx)
        _sync_task_from_context(task, ctx)
        task.selected_provider = best["provider"]
        task.selected_gpu_type = best["gpu_type"]
        task.progress = 35

        run = TaskRun(
            task_id=task.id,
            attempt_no=ctx.retry_count + 1,
            provider=best["provider"],
            gpu_type=best["gpu_type"],
            region=best["region"],
            runtime_target=task.execution_mode,
            status=TaskRunStatus.INSTANCE_CREATING.value,
            scheduler_score=Decimal(str(best["score"])),
            started_at=datetime.now(UTC),
        )
        db.add(run)
        db.flush()

        record_event(
            db,
            task,
            source="scheduler",
            stage=WorkflowStage.EXECUTION.value,
            level=EventLevel.INFO.value,
            message="Provider selected.",
            detail_payload=best,
        )

        submission = marketplace.build_submission(task)
        submission.preferred_provider = best["provider"]
        submission.preferred_gpu_type = best["gpu_type"]

        try:
            handle = marketplace.submit_task(db, submission)
        except ProviderMarketplaceError as exc:
            ctx, keep_retrying = _run_failure_transition(
                db,
                task,
                run,
                ctx,
                machine,
                marketplace,
                reason=f"marketplace submission failed: {exc}",
                previous_providers=previous_providers,
                source="scheduler",
                error_message="Marketplace submission failed and no retry remains.",
            )
            if keep_retrying:
                continue
            return {
                "status": task.status,
                "selected_provider": task.selected_provider,
                "retry_count": task.retry_count,
            }

        run.external_task_id = handle.external_task_id
        if handle.provider:
            run.provider = handle.provider
            task.selected_provider = handle.provider
        if handle.gpu_type:
            run.gpu_type = handle.gpu_type
            task.selected_gpu_type = handle.gpu_type
        record_event(
            db,
            task,
            source="scheduler",
            stage=WorkflowStage.EXECUTION.value,
            level=EventLevel.INFO.value,
            message="Marketplace accepted the task.",
            detail_payload={
                "adapter": marketplace.adapter_key,
                "external_task_id": run.external_task_id,
                "provider": run.provider,
                "gpu_type": run.gpu_type,
                "marketplace_status": handle.status,
            },
        )

        if _should_fail(task, run.provider, run.attempt_no):
            ctx, keep_retrying = _run_failure_transition(
                db,
                task,
                run,
                ctx,
                machine,
                marketplace,
                reason="provider interrupted before result collection",
                previous_providers=previous_providers,
                source="worker",
                error_message="Execution failed before delivery artifacts were collected.",
            )
            if keep_retrying:
                continue
            return {
                "status": task.status,
                "selected_provider": task.selected_provider,
                "retry_count": task.retry_count,
            }

        def should_cancel() -> bool:
            db.refresh(task, attribute_names=["status"])
            return task.status == TaskStatus.CANCELLING.value

        if should_cancel():
            return _cancel_active_run(db, task, run, ctx, machine, marketplace)

        fallback_runtime_seconds = int(best["estimated_runtime_minutes"] * 60)
        fallback_price = Decimal(str(best["estimated_price"])) * Decimal("0.72")

        try:
            remote_status = _poll_remote_status(
                db,
                task,
                run,
                ctx=ctx,
                machine=machine,
                marketplace=marketplace,
                should_cancel=should_cancel,
            )
        except TaskCancellationRequested:
            return _cancel_active_run(db, task, run, ctx, machine, marketplace)
        except ProviderMarketplaceError as exc:
            ctx, keep_retrying = _run_failure_transition(
                db,
                task,
                run,
                ctx,
                machine,
                marketplace,
                reason=str(exc),
                previous_providers=previous_providers,
                source="marketplace",
                error_message="Marketplace polling failed and no retry remains.",
            )
            if keep_retrying:
                continue
            return {
                "status": task.status,
                "selected_provider": task.selected_provider,
                "retry_count": task.retry_count,
            }

        remote_status_key = _normalize_remote_status(remote_status.status)
        if remote_status_key in REMOTE_FAILURE_STATUSES | REMOTE_CANCELLED_STATUSES:
            ctx, keep_retrying = _run_failure_transition(
                db,
                task,
                run,
                ctx,
                machine,
                marketplace,
                reason=remote_status.message or remote_status.status,
                previous_providers=previous_providers,
                source="marketplace",
                error_message="Marketplace reported a terminal task failure.",
            )
            if keep_retrying:
                continue
            return {
                "status": task.status,
                "selected_provider": task.selected_provider,
                "retry_count": task.retry_count,
            }

        try:
            result = marketplace.collect_task_result(db, run.external_task_id or "")
            _apply_remote_result(
                db,
                task,
                run,
                result,
                fallback_price=fallback_price,
                fallback_runtime_seconds=fallback_runtime_seconds,
            )
        except ProviderMarketplaceError as exc:
            ctx, keep_retrying = _run_failure_transition(
                db,
                task,
                run,
                ctx,
                machine,
                marketplace,
                reason=f"result collection failed: {exc}",
                previous_providers=previous_providers,
                source="marketplace",
                error_message="Marketplace result collection failed and no retry remains.",
            )
            if keep_retrying:
                continue
            return {
                "status": task.status,
                "selected_provider": task.selected_provider,
                "retry_count": task.retry_count,
            }

        machine.begin_cleanup(ctx, "post-result cleanup")
        _sync_task_from_context(task, ctx)
        _cleanup_remote_resources(
            db,
            task,
            run,
            marketplace,
            reason="post_result",
        )
        if ctx.status == TaskStatus.CLEANING_UP:
            machine.resume_after_cleanup(ctx)
            _sync_task_from_context(task, ctx)

        review_result = gpt_workflow.review_task(
            task,
            run,
            execution_note=task.result_summary or "",
            revision_round=review_round,
        )
        task.review_round = review_round
        task.review_summary = str(review_result["review_summary"])
        task.latest_fix_instructions = str(review_result.get("fix_instructions") or "")
        task.review_approved = bool(review_result["approved"])

        is_terminal_review_failure = review_round >= settings.review_max_rounds
        code_editor.sync_task_review_chain(
            task_id=task.id,
            review_round=review_round,
            approved=bool(review_result["approved"]),
            review_summary=task.review_summary,
            fix_instructions=task.latest_fix_instructions,
            terminal=bool(review_result["approved"]) or is_terminal_review_failure,
            db=db,
        )

        if bool(review_result["approved"]):
            task.review_status = StageStatus.COMPLETED.value
            task.workflow_stage = WorkflowStage.DONE.value
            machine.complete(ctx)
            _sync_task_from_context(task, ctx)
            task.progress = 100
            apply_wallet_charge(db, task)
            record_event(
                db,
                task,
                source="reviewer",
                stage=WorkflowStage.REVIEW.value,
                level=EventLevel.SUCCESS.value,
                message="Review completed and delivery is approved.",
                detail_payload=review_result,
            )
            return {
                "status": task.status,
                "selected_provider": task.selected_provider,
                "retry_count": task.retry_count,
            }

        record_event(
            db,
            task,
            source="reviewer",
            stage=WorkflowStage.REVIEW.value,
            level=EventLevel.WARN.value,
            message="Review rejected the delivery and requested another execution attempt.",
            detail_payload=review_result,
        )

        task.last_error = task.latest_fix_instructions or task.review_summary or "review rejected"
        previous_providers.add(run.provider)

        if is_terminal_review_failure:
            task.review_status = StageStatus.FAILED.value
            task.execution_status = StageStatus.FAILED.value
            task.workflow_stage = WorkflowStage.DONE.value
            ctx.retry_count = ctx.max_retries
            ctx = machine.fail_or_retry(ctx, task.last_error)
            _sync_task_from_context(task, ctx)
            record_event(
                db,
                task,
                source="reviewer",
                stage=WorkflowStage.REVIEW.value,
                level=EventLevel.ERROR.value,
                message="Review retry budget exhausted.",
                detail_payload=review_result,
            )
            return {
                "status": task.status,
                "selected_provider": task.selected_provider,
                "retry_count": task.retry_count,
            }

        ctx = machine.fail_or_retry(ctx, task.last_error)
        _sync_task_from_context(task, ctx)
        task.review_status = StageStatus.FAILED.value
        task.execution_status = StageStatus.IN_PROGRESS.value
        task.workflow_stage = WorkflowStage.EXECUTION.value
        task.progress = 28
        review_round += 1


def _process_cancelling_task(db: Session, task: Task) -> dict[str, Any]:
    machine = TaskStateMachine()
    marketplace = ProviderMarketplaceService()
    ctx = TaskContext(
        task_id=str(task.id),
        status=TaskStatus(task.status),
        retry_count=task.retry_count,
        max_retries=task.retry_limit,
    )
    latest_run = db.scalar(
        select(TaskRun)
        .where(TaskRun.task_id == task.id)
        .order_by(TaskRun.attempt_no.desc(), TaskRun.id.desc())
        .limit(1)
    )
    return _cancel_active_run(db, task, latest_run, ctx, machine, marketplace)


def process_pending_tasks(limit: int = 5) -> list[dict[str, Any]]:
    processed: list[dict[str, Any]] = []
    with session_scope() as db:
        tasks = list(
            db.scalars(
                select(Task)
                .where(
                    Task.status.in_(
                        [
                            TaskStatus.QUEUED.value,
                            TaskStatus.RETRYING.value,
                            TaskStatus.CANCELLING.value,
                        ]
                    )
                )
                .order_by(Task.created_at.asc())
                .limit(limit)
            )
        )
        for task in tasks:
            if task.status == TaskStatus.CANCELLING.value:
                processed.append({"task_id": task.id, **_process_cancelling_task(db, task)})
            else:
                processed.append({"task_id": task.id, **_execute_task(db, task)})
    return processed
