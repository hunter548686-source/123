from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    DISPATCHING = "dispatching"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    CHECKPOINTING = "checkpointing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.DRAFT: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {TaskStatus.DISPATCHING, TaskStatus.CANCELLED},
    TaskStatus.DISPATCHING: {TaskStatus.PROVISIONING, TaskStatus.FAILED, TaskStatus.RETRYING},
    TaskStatus.PROVISIONING: {TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.FAILED},
    TaskStatus.RUNNING: {
        TaskStatus.CHECKPOINTING,
        TaskStatus.COMPLETED,
        TaskStatus.RETRYING,
        TaskStatus.CANCELLED,
    },
    TaskStatus.CHECKPOINTING: {TaskStatus.RUNNING, TaskStatus.RETRYING, TaskStatus.FAILED},
    TaskStatus.RETRYING: {TaskStatus.DISPATCHING, TaskStatus.FAILED},
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

    def complete(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.COMPLETED, "task finished")

    def cancel(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.CANCELLED, "cancelled by user")

    def fail_or_retry(self, ctx: TaskContext, reason: str) -> TaskContext:
        if ctx.retry_count < ctx.max_retries:
            ctx.retry_count += 1
            return self.transition(ctx, TaskStatus.RETRYING, reason)
        return self.transition(ctx, TaskStatus.FAILED, reason)

    def redispatch(self, ctx: TaskContext) -> TaskContext:
        return self.transition(ctx, TaskStatus.DISPATCHING, "retry scheduling")


if __name__ == "__main__":
    machine = TaskStateMachine()
    task = TaskContext(task_id="task_001", max_retries=2)

    machine.queue(task)
    machine.dispatch(task)
    machine.provision(task)
    machine.start_run(task)
    machine.fail_or_retry(task, "provider disconnected")
    machine.redispatch(task)
    machine.provision(task)
    machine.start_run(task)
    machine.complete(task)

    for line in task.history:
        print(line)

