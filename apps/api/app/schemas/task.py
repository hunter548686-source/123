from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderOfferRead(BaseModel):
    provider: str
    gpu_type: str
    region: str | None
    price_per_hour: float
    reliability_score: float
    startup_score: float
    success_rate: float
    score: float | None = None
    estimated_price: float | None = None
    estimated_runtime_minutes: int | None = None


class QuoteRequest(BaseModel):
    task_type: str
    strategy: str
    duration_seconds: int = Field(default=8, ge=1)
    resolution: str = "1080p"
    output_count: int = Field(default=1, ge=1)
    execution_mode: str = "hybrid"


class QuoteResponse(BaseModel):
    recommended_offer: ProviderOfferRead
    candidate_offers: list[ProviderOfferRead]
    estimated_price: float
    estimated_runtime_minutes: int
    risk_note: str


class TaskCreateRequest(BaseModel):
    project_id: int
    task_type: str
    template_id: str
    strategy: str
    execution_mode: str = "hybrid"
    input_payload: dict[str, Any]
    quote_snapshot: dict[str, Any] | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    task_type: str
    template_id: str
    strategy: str
    status: str
    workflow_stage: str
    planning_status: str
    execution_status: str
    review_status: str
    execution_mode: str
    quoted_price: Decimal | None
    final_cost: Decimal | None
    final_charge: Decimal | None
    selected_provider: str | None
    selected_gpu_type: str | None
    retry_limit: int
    retry_count: int
    progress: int
    last_error: str | None
    plan_summary: str | None
    execution_brief: str | None
    coding_instructions: str | None
    review_summary: str | None
    latest_fix_instructions: str | None
    result_summary: str | None
    review_round: int
    review_approved: bool | None
    created_at: datetime
    updated_at: datetime


class TaskRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attempt_no: int
    external_task_id: str | None
    provider: str
    gpu_type: str
    region: str | None
    runtime_target: str
    status: str
    runtime_seconds: int
    provider_cost: Decimal
    scheduler_score: Decimal | None
    fail_reason: str | None
    local_executor_note: str | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class TaskEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    stage: str
    level: str
    message: str
    detail_payload: dict[str, Any] | None
    created_at: datetime


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    storage_path: str
    download_url: str | None
    file_size: int
    checksum: str | None
    metadata_payload: dict[str, Any] | None
    created_at: datetime


class ArtifactDownloadResponse(BaseModel):
    artifact_id: int
    download_url: str
    source: str


class TaskDetailResponse(BaseModel):
    task: TaskRead
    current_run: TaskRunRead | None
    runs: list[TaskRunRead]
    events: list[TaskEventRead]
    artifacts: list[ArtifactRead]
    code_edit_chains: list[CodeEditReviewChainRead]
    code_edits: list[CodeEditExecutionRead]


class AdminTaskSummary(BaseModel):
    total: int
    running: int
    failed: int
    completed: int


class AdminTaskListResponse(BaseModel):
    items: list[TaskRead]
    summary: AdminTaskSummary


class AdminUserOverview(BaseModel):
    id: int
    email: str
    role: str
    status: str
    wallet_balance: float
    frozen_balance: float
    total_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    created_at: datetime


class AdminProviderHealth(BaseModel):
    provider: str
    offer_count: int
    average_price_per_hour: float
    average_reliability: float
    average_startup_score: float
    average_success_rate: float


class BillingProfitResponse(BaseModel):
    revenue: float
    cost: float
    gross_profit: float
    gross_margin: float
    by_provider: list[dict[str, Any]]


class AdminMonitoringOverview(BaseModel):
    status_breakdown: dict[str, int]
    active_runs: int
    queued_for_retry: int
    pending_cleanup: int
    open_cancellations: int
    recent_provider_cost: float
    recent_runtime_seconds: int
    adapter_key: str
    marketplace_name: str
    recent_failures: list[dict[str, Any]]


class HomeMetricsResponse(BaseModel):
    average_delivery_seconds: int
    success_rate_7d: float
    provider_count: int
    cost_visibility_coverage: float
    sample_size_7d: int
    completed_tasks_7d: int
    updated_at: datetime


class CodeEditRequest(BaseModel):
    instructions: str
    files: list[str] = Field(default_factory=list, min_length=1)
    test_commands: list[str] = Field(default_factory=list)
    task_id: int | None = None


class CodeEditResponse(BaseModel):
    summary: str
    mode: str
    changed_files: list[str]
    operations_count: int
    execution_id: int | None = None
    task_id: int | None = None
    review_chain_id: int | None = None
    chain_step_no: int | None = None
    review_chain_status: str | None = None
    workflow_stage: str | None = None
    review_round: int | None = None
    review_approved: bool | None = None
    diff_preview: str | None = None
    test_results: list[dict[str, Any]] = Field(default_factory=list)
    raw_model_note: str | None = None
    rollback_status: str | None = None


class CodeEditExecutionFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    created_at: datetime


class CodeEditExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int | None
    review_chain_id: int | None
    actor_user_id: int | None
    actor_email: str | None
    chain_step_no: int | None
    review_chain_status: str | None
    workflow_stage: str | None
    review_round: int | None
    review_approved: bool | None
    status: str
    summary: str | None
    instructions: str
    requested_files: list[str]
    changed_files: list[str]
    operations_count: int
    diff_preview: str | None
    test_commands: list[str]
    test_results: list[dict[str, Any]]
    model_mode: str | None
    raw_model_note: str | None
    rollback_status: str
    rollback_error: str | None
    rollback_actor_user_id: int | None
    rollback_actor_email: str | None
    rolled_back_at: datetime | None
    created_at: datetime
    updated_at: datetime
    files: list[CodeEditExecutionFileRead] = Field(default_factory=list)


class CodeEditReviewChainRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    status: str
    started_review_round: int
    current_review_round: int
    total_executions: int
    latest_review_summary: str | None
    latest_fix_instructions: str | None
    final_review_approved: bool | None
    final_review_summary: str | None
    opened_at: datetime
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CodeEditRollbackResponse(BaseModel):
    execution_id: int
    rollback_status: str
    restored_files: list[str]
    message: str
