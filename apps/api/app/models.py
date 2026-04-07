from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .enums import (
    ExecutionMode,
    StageStatus,
    TaskRunStatus,
    TaskStatus,
    TaskStrategy,
    UserRole,
    UserStatus,
    WalletLedgerType,
    WorkflowStage,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, default=UserRole.USER.value)
    status: Mapped[str] = mapped_column(Text, default=UserStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    wallet: Mapped["Wallet"] = relationship(back_populates="user", uselist=False)
    projects: Mapped[list["Project"]] = relationship(back_populates="user")
    tasks: Mapped[list["Task"]] = relationship(back_populates="user")


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    frozen_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0")
    )
    currency: Mapped[str] = mapped_column(Text, default="CNY")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="wallet")
    ledger_items: Mapped[list["WalletLedger"]] = relationship(back_populates="wallet")


class WalletLedger(Base):
    __tablename__ = "wallet_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), index=True)
    type: Mapped[str] = mapped_column(Text, default=WalletLedgerType.RECHARGE.value)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    ref_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    wallet: Mapped["Wallet"] = relationship(back_populates="ledger_items")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    scene_type: Mapped[str] = mapped_column(Text, default="video_generation")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_type: Mapped[str] = mapped_column(Text)
    template_id: Mapped[str] = mapped_column(Text)
    strategy: Mapped[str] = mapped_column(Text, default=TaskStrategy.STABLE.value)
    status: Mapped[str] = mapped_column(Text, default=TaskStatus.QUEUED.value)
    workflow_stage: Mapped[str] = mapped_column(
        Text, default=WorkflowStage.PLANNING.value
    )
    planning_status: Mapped[str] = mapped_column(Text, default=StageStatus.PENDING.value)
    execution_status: Mapped[str] = mapped_column(
        Text, default=StageStatus.PENDING.value
    )
    review_status: Mapped[str] = mapped_column(Text, default=StageStatus.PENDING.value)
    execution_mode: Mapped[str] = mapped_column(
        Text, default=ExecutionMode.HYBRID.value
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    quote_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    quoted_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    final_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    final_charge: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    selected_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_gpu_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_limit: Mapped[int] = mapped_column(Integer, default=2)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_brief: Mapped[str | None] = mapped_column(Text, nullable=True)
    coding_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_fix_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_round: Mapped[int] = mapped_column(Integer, default=0)
    review_approved: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="tasks")
    user: Mapped["User"] = relationship(back_populates="tasks")
    runs: Mapped[list["TaskRun"]] = relationship(back_populates="task")
    checkpoints: Mapped[list["Checkpoint"]] = relationship(back_populates="task")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="task")
    events: Mapped[list["TaskEvent"]] = relationship(back_populates="task")
    code_edit_review_chains: Mapped[list["CodeEditReviewChain"]] = relationship(
        back_populates="task"
    )
    code_edit_executions: Mapped[list["CodeEditExecution"]] = relationship(
        back_populates="task"
    )


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str] = mapped_column(Text)
    gpu_type: Mapped[str] = mapped_column(Text)
    instance_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_task_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_target: Mapped[str] = mapped_column(Text, default=ExecutionMode.HYBRID.value)
    status: Mapped[str] = mapped_column(Text, default=TaskRunStatus.SELECTED.value)
    runtime_seconds: Mapped[int] = mapped_column(Integer, default=0)
    provider_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    scheduler_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    fail_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_executor_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    task: Mapped["Task"] = relationship(back_populates="runs")
    checkpoints: Mapped[list["Checkpoint"]] = relationship(back_populates="task_run")


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    task_run_id: Mapped[int] = mapped_column(ForeignKey("task_runs.id"), index=True)
    storage_path: Mapped[str] = mapped_column(Text)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    task: Mapped["Task"] = relationship(back_populates="checkpoints")
    task_run: Mapped["TaskRun"] = relationship(back_populates="checkpoints")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    type: Mapped[str] = mapped_column(Text)
    storage_path: Mapped[str] = mapped_column(Text)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    task: Mapped["Task"] = relationship(back_populates="artifacts")


class ProviderOfferSnapshot(Base):
    __tablename__ = "provider_offers_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(Text, index=True)
    gpu_type: Mapped[str] = mapped_column(Text, index=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_per_hour: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    reliability_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    startup_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    success_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    source: Mapped[str] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    detail_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    task: Mapped["Task"] = relationship(back_populates="events")


class CodeEditReviewChain(Base):
    __tablename__ = "code_edit_review_chains"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    status: Mapped[str] = mapped_column(Text, default="awaiting_review")
    started_review_round: Mapped[int] = mapped_column(Integer, default=0)
    current_review_round: Mapped[int] = mapped_column(Integer, default=0)
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    latest_review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_fix_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_review_approved: Mapped[bool | None] = mapped_column(nullable=True)
    final_review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    task: Mapped["Task"] = relationship(back_populates="code_edit_review_chains")
    executions: Mapped[list["CodeEditExecution"]] = relationship(
        back_populates="review_chain"
    )


class CodeEditExecution(Base):
    __tablename__ = "code_edit_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), index=True, nullable=True
    )
    review_chain_id: Mapped[int | None] = mapped_column(
        ForeignKey("code_edit_review_chains.id"), index=True, nullable=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    actor_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    chain_step_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_chain_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_stage: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_approved: Mapped[bool | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(Text, default="applied")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str] = mapped_column(Text)
    requested_files: Mapped[list[str]] = mapped_column(JSON, default=list)
    changed_files: Mapped[list[str]] = mapped_column(JSON, default=list)
    operations_count: Mapped[int] = mapped_column(Integer, default=0)
    diff_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_commands: Mapped[list[str]] = mapped_column(JSON, default=list)
    test_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    model_mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_model_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_status: Mapped[str] = mapped_column(Text, default="not_requested")
    rollback_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    rollback_actor_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    files: Mapped[list["CodeEditExecutionFile"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )
    task: Mapped["Task | None"] = relationship(back_populates="code_edit_executions")
    review_chain: Mapped["CodeEditReviewChain | None"] = relationship(
        back_populates="executions"
    )


class CodeEditExecutionFile(Base):
    __tablename__ = "code_edit_execution_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("code_edit_executions.id"), index=True
    )
    path: Mapped[str] = mapped_column(Text)
    before_content: Mapped[str] = mapped_column(Text)
    after_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    execution: Mapped["CodeEditExecution"] = relationship(back_populates="files")
