from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class TaskStrategy(str, Enum):
    CHEAP = "cheap"
    STABLE = "stable"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    DISPATCHING = "dispatching"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    CHECKPOINTING = "checkpointing"
    RETRYING = "retrying"
    CANCELLING = "cancelling"
    CLEANING_UP = "cleaning_up"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRunStatus(str, Enum):
    SELECTED = "selected"
    INSTANCE_CREATING = "instance_creating"
    INSTANCE_READY = "instance_ready"
    RUNTIME_BOOTING = "runtime_booting"
    MODEL_LOADING = "model_loading"
    EXECUTING = "executing"
    UPLOADING = "uploading"
    CANCELLING = "cancelling"
    CLEANING_UP = "cleaning_up"
    CANCELLED = "cancelled"
    FINISHED = "finished"
    ERROR = "error"


class WorkflowStage(str, Enum):
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"
    DONE = "done"


class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionMode(str, Enum):
    HYBRID = "hybrid"
    CLOUD = "cloud"
    LOCAL_DEV = "local_dev"


class WalletLedgerType(str, Enum):
    RECHARGE = "recharge"
    CONSUME = "consume"
    REFUND = "refund"
    ADJUST = "adjust"


class EventLevel(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    SUCCESS = "success"


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.DRAFT: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {
        TaskStatus.DISPATCHING,
        TaskStatus.CANCELLING,
        TaskStatus.CANCELLED,
    },
    TaskStatus.DISPATCHING: {
        TaskStatus.PROVISIONING,
        TaskStatus.RETRYING,
        TaskStatus.CANCELLING,
        TaskStatus.FAILED,
    },
    TaskStatus.PROVISIONING: {
        TaskStatus.RUNNING,
        TaskStatus.RETRYING,
        TaskStatus.CANCELLING,
        TaskStatus.CLEANING_UP,
        TaskStatus.FAILED,
    },
    TaskStatus.RUNNING: {
        TaskStatus.CHECKPOINTING,
        TaskStatus.RETRYING,
        TaskStatus.CANCELLING,
        TaskStatus.CLEANING_UP,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
    },
    TaskStatus.CHECKPOINTING: {
        TaskStatus.RUNNING,
        TaskStatus.RETRYING,
        TaskStatus.CANCELLING,
        TaskStatus.CLEANING_UP,
        TaskStatus.FAILED,
    },
    TaskStatus.RETRYING: {
        TaskStatus.DISPATCHING,
        TaskStatus.CANCELLING,
        TaskStatus.FAILED,
    },
    TaskStatus.CANCELLING: {
        TaskStatus.CLEANING_UP,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
    TaskStatus.CLEANING_UP: {
        TaskStatus.RUNNING,
        TaskStatus.RETRYING,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
    },
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


@dataclass
class TaskContext:
    task_id: str
    status: TaskStatus = TaskStatus.DRAFT
    retry_count: int = 0
    max_retries: int = 2
    history: list[str] = field(default_factory=list)


class InvalidTransitionError(Exception):
    pass


class TaskStateMachine:
    def transition(self, ctx: TaskContext, target: TaskStatus, reason: str = "") -> TaskContext:
        allowed = ALLOWED_TRANSITIONS.get(ctx.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"{ctx.status.value} -> {target.value} not allowed")
        ctx.history.append(f"{ctx.status.value} -> {target.value}: {reason}".strip(": "))
        ctx.status = target
        return ctx

    def queue(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.QUEUED, "task created")

    def dispatch(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.DISPATCHING, "scheduler started")

    def provision(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.PROVISIONING, "provider instance requested")

    def start_run(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.RUNNING, "runtime booted")

    def checkpoint(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.CHECKPOINTING, "save checkpoint")

    def resume_after_checkpoint(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.RUNNING, "checkpoint saved")

    def begin_cancelling(self, ctx: TaskContext, reason: str = "cancel requested") -> TaskContext:
        return self.transition(ctx, TaskStatus.CANCELLING, reason)

    def begin_cleanup(self, ctx: TaskContext, reason: str = "resource cleanup") -> TaskContext:
        return self.transition(ctx, TaskStatus.CLEANING_UP, reason)

    def resume_after_cleanup(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.RUNNING, "cleanup finished")

    def complete(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.COMPLETED, "task finished")

    def cancel(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.CANCELLED, "cancelled by user")

    def fail_or_retry(self, ctx: TaskContext, reason: str) -> TaskContext:
        if ctx.retry_count < ctx.max_retries:
            ctx.retry_count += 1
            return self.transition(ctx, TaskStatus.RETRYING, reason)
        return self.transition(ctx, TaskStatus.FAILED, reason)

    def fail(self, ctx: TaskContext, reason: str) -> TaskContext:
        return self.transition(ctx, TaskStatus.FAILED, reason)

    def redispatch(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.DISPATCHING, "retry scheduling")
