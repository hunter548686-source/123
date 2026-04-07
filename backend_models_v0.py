from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


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
    FINISHED = "finished"
    ERROR = "error"


class WalletLedgerType(str, Enum):
    RECHARGE = "recharge"
    CONSUME = "consume"
    REFUND = "refund"
    ADJUST = "adjust"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(Text)
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
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    frozen_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
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
    type: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    ref_type: Mapped[str | None] = mapped_column(Text)
    ref_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    wallet: Mapped["Wallet"] = relationship(back_populates="ledger_items")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    scene_type: Mapped[str] = mapped_column(Text)
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
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    quoted_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    final_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    final_charge: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    progress: Mapped[int] = mapped_column(Integer, default=0)
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


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    provider: Mapped[str] = mapped_column(Text)
    gpu_type: Mapped[str] = mapped_column(Text)
    instance_id: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default=TaskRunStatus.SELECTED.value)
    runtime_seconds: Mapped[int] = mapped_column(Integer, default=0)
    provider_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    fail_reason: Mapped[str | None] = mapped_column(Text)
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
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    task: Mapped["Task"] = relationship(back_populates="artifacts")


class ProviderOfferSnapshot(Base):
    __tablename__ = "provider_offers_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(Text, index=True)
    gpu_type: Mapped[str] = mapped_column(Text, index=True)
    region: Mapped[str | None] = mapped_column(Text)
    price_per_hour: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    reliability_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    startup_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    success_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

