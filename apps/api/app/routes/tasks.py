from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..schemas.task import (
    ArtifactRead,
    ArtifactDownloadResponse,
    CodeEditExecutionRead,
    CodeEditReviewChainRead,
    TaskCreateRequest,
    TaskDetailResponse,
    TaskEventRead,
    TaskRead,
    TaskRunRead,
)
from ..services.tasks import (
    cancel_task,
    create_task,
    get_task_or_404,
    get_task_query,
    retry_task,
    serialize_artifacts,
    serialize_code_edit_chains,
    serialize_code_edits,
    serialize_events,
    serialize_runs,
    resolve_artifact_download_url,
)


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskRead]:
    tasks = list(db.scalars(get_task_query(user, status)))
    return [TaskRead.model_validate(task) for task in tasks]


@router.post("", response_model=TaskRead)
def create_task_endpoint(
    payload: TaskCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskRead:
    task = create_task(
        db,
        user=user,
        project_id=payload.project_id,
        task_type=payload.task_type,
        template_id=payload.template_id,
        strategy=payload.strategy,
        execution_mode=payload.execution_mode,
        input_payload=payload.input_payload,
        quote_snapshot=payload.quote_snapshot,
    )
    return TaskRead.model_validate(task)


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task_detail(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskDetailResponse:
    task = get_task_or_404(db, task_id, user=user)
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


@router.get("/{task_id}/runs", response_model=list[TaskRunRead])
def get_task_runs(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskRunRead]:
    task = get_task_or_404(db, task_id, user=user)
    return [TaskRunRead.model_validate(run) for run in serialize_runs(task)]


@router.post("/{task_id}/retry", response_model=TaskRead)
def retry_task_endpoint(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskRead:
    task = retry_task(db, get_task_or_404(db, task_id, user=user))
    return TaskRead.model_validate(task)


@router.post("/{task_id}/cancel", response_model=TaskRead)
def cancel_task_endpoint(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskRead:
    task = cancel_task(db, get_task_or_404(db, task_id, user=user))
    return TaskRead.model_validate(task)


@router.get(
    "/{task_id}/artifacts/{artifact_id}/download",
    response_model=ArtifactDownloadResponse,
)
def get_artifact_download(
    task_id: int,
    artifact_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ArtifactDownloadResponse:
    task = get_task_or_404(db, task_id, user=user)
    artifact = next((item for item in task.artifacts if item.id == artifact_id), None)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    download_url = resolve_artifact_download_url(artifact)
    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Artifact download URL is not available yet",
        )
    source = "download_url" if artifact.download_url else "storage_path"
    return ArtifactDownloadResponse(
        artifact_id=artifact.id,
        download_url=download_url,
        source=source,
    )
