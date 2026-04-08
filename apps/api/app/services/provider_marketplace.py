from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Protocol
from urllib.parse import quote_plus

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ProviderOfferSnapshot, Task


class ProviderMarketplaceError(RuntimeError):
    pass


@dataclass(slots=True)
class ProviderMarketplaceTaskSubmission:
    local_task_id: int
    task_type: str
    template_id: str
    strategy: str
    execution_mode: str
    input_payload: dict[str, Any]
    quote_snapshot: dict[str, Any] | None = None
    preferred_provider: str | None = None
    preferred_gpu_type: str | None = None
    callback_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_task(cls, task: Task) -> "ProviderMarketplaceTaskSubmission":
        recommended_offer = (task.quote_snapshot or {}).get("recommended_offer") or {}
        return cls(
            local_task_id=task.id,
            task_type=task.task_type,
            template_id=task.template_id,
            strategy=task.strategy,
            execution_mode=task.execution_mode,
            input_payload=dict(task.input_payload or {}),
            quote_snapshot=dict(task.quote_snapshot or {}) or None,
            preferred_provider=task.selected_provider or recommended_offer.get("provider"),
            preferred_gpu_type=task.selected_gpu_type or recommended_offer.get("gpu_type"),
            metadata={
                "project_id": task.project_id,
                "user_id": task.user_id,
                "workflow_stage": task.workflow_stage,
            },
        )


@dataclass(slots=True)
class ProviderMarketplaceTaskHandle:
    external_task_id: str
    accepted: bool
    status: str
    provider: str | None = None
    gpu_type: str | None = None
    message: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderMarketplaceTaskStatus:
    external_task_id: str
    status: str
    progress_percent: int
    provider: str | None = None
    gpu_type: str | None = None
    stage: str | None = None
    message: str | None = None
    retryable: bool = False
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderMarketplaceCancelResult:
    external_task_id: str
    cancelled: bool
    status: str
    provider: str | None = None
    message: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderMarketplaceCleanupResult:
    external_task_id: str
    cleaned: bool
    status: str
    provider: str | None = None
    message: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderMarketplaceArtifact:
    kind: str
    uri: str
    download_url: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderMarketplaceResult:
    external_task_id: str
    status: str
    provider: str | None = None
    summary: str | None = None
    artifacts: list[ProviderMarketplaceArtifact] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    raw_payload: dict[str, Any] = field(default_factory=dict)


class ProviderMarketplaceAdapter(Protocol):
    adapter_key: str
    marketplace_name: str

    def list_offers(self, db: Session) -> list[ProviderOfferSnapshot]:
        ...

    def submit_task(
        self,
        db: Session,
        submission: ProviderMarketplaceTaskSubmission,
    ) -> ProviderMarketplaceTaskHandle:
        ...

    def get_task_status(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceTaskStatus:
        ...

    def cancel_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCancelResult:
        ...

    def cleanup_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCleanupResult:
        ...

    def collect_task_result(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceResult:
        ...


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick_first(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None


def _runtime_seconds_from_datetimes(started_at: Any, ended_at: Any | None = None) -> int | None:
    start_dt = _parse_datetime(started_at)
    if start_dt is None:
        return None
    end_dt = _parse_datetime(ended_at) if ended_at else datetime.now(UTC)
    if end_dt is None:
        end_dt = datetime.now(UTC)
    delta = int((end_dt - start_dt).total_seconds())
    return max(delta, 0)


@dataclass
class DatabaseSnapshotMarketplaceAdapter:
    marketplace_name: str
    adapter_key: str = "database_mock"

    def list_offers(self, db: Session) -> list[ProviderOfferSnapshot]:
        return list(
            db.scalars(
                select(ProviderOfferSnapshot).order_by(
                    ProviderOfferSnapshot.price_per_hour.asc()
                )
            )
        )

    def submit_task(
        self,
        db: Session,
        submission: ProviderMarketplaceTaskSubmission,
    ) -> ProviderMarketplaceTaskHandle:
        del db
        provider = (
            submission.preferred_provider
            or ((submission.quote_snapshot or {}).get("recommended_offer") or {}).get("provider")
            or self.marketplace_name
        )
        gpu_type = (
            submission.preferred_gpu_type
            or ((submission.quote_snapshot or {}).get("recommended_offer") or {}).get("gpu_type")
        )
        external_task_id = f"{self.adapter_key}-task-{submission.local_task_id}"
        return ProviderMarketplaceTaskHandle(
            external_task_id=external_task_id,
            accepted=True,
            status="submitted",
            provider=provider,
            gpu_type=gpu_type,
            message="database_mock adapter accepted the task submission",
            raw_payload={
                "local_task_id": submission.local_task_id,
                "strategy": submission.strategy,
                "execution_mode": submission.execution_mode,
            },
        )

    def get_task_status(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceTaskStatus:
        del db
        return ProviderMarketplaceTaskStatus(
            external_task_id=external_task_id,
            status="succeeded",
            progress_percent=100,
            provider=self.marketplace_name,
            stage="completed",
            message="database_mock adapter completed the task",
            retryable=False,
            raw_payload={"adapter": self.adapter_key},
        )

    def cancel_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCancelResult:
        del db
        return ProviderMarketplaceCancelResult(
            external_task_id=external_task_id,
            cancelled=True,
            status="cancelled",
            provider=self.marketplace_name,
            message="database_mock adapter cancelled the task",
            raw_payload={"adapter": self.adapter_key},
        )

    def cleanup_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCleanupResult:
        del db
        return ProviderMarketplaceCleanupResult(
            external_task_id=external_task_id,
            cleaned=True,
            status="cleaned",
            provider=self.marketplace_name,
            message="database_mock adapter cleaned task resources",
            raw_payload={"adapter": self.adapter_key},
        )

    def collect_task_result(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceResult:
        del db
        artifact = ProviderMarketplaceArtifact(
            kind="video",
            uri=f"/mock-marketplace/tasks/{external_task_id}/result.mp4",
            download_url=f"https://example.invalid/downloads/{external_task_id}.mp4",
            size_bytes=24_000_000,
            checksum=f"mock-{external_task_id}",
            metadata={"adapter": self.adapter_key},
        )
        return ProviderMarketplaceResult(
            external_task_id=external_task_id,
            status="succeeded",
            provider=self.marketplace_name,
            summary="database_mock adapter returned a simulated delivery artifact",
            artifacts=[artifact],
            usage={"billable_seconds": 600, "estimated_cost": 0.0, "provider_cost": 0.0},
            raw_payload={"adapter": self.adapter_key},
        )


@dataclass
class RemoteMarketplaceAdapter:
    marketplace_name: str
    base_url: str | None
    api_key: str | None
    request_timeout_seconds: float = 30.0
    adapter_key: str = "remote_marketplace"
    offers_path: str = "/offers"
    submit_path: str = "/tasks"
    status_path_template: str = "/tasks/{external_task_id}"
    cancel_path_template: str = "/tasks/{external_task_id}/cancel"
    result_path_template: str = "/tasks/{external_task_id}/result"
    cleanup_path_template: str = "/tasks/{external_task_id}/cleanup"

    def _require_base_url(self) -> str:
        if not self.base_url:
            raise ProviderMarketplaceError(
                f"{self.adapter_key} requires a base URL configuration"
            )
        return self.base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request_payload(
        self,
        method: str,
        path_or_url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            url = path_or_url
        else:
            url = f"{self._require_base_url()}{path_or_url}"
        try:
            response = httpx.request(
                method,
                url,
                headers=headers or self._headers(),
                json=json_body,
                timeout=self.request_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderMarketplaceError(
                f"{self.adapter_key} request failed: {method} {path_or_url}: {exc}"
            ) from exc

        if response.status_code == 204:
            return {}
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderMarketplaceError(
                f"{self.adapter_key} returned non-JSON response for {method} {path_or_url}"
            ) from exc
        return payload

    def _request_json(
        self,
        method: str,
        path_or_url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload = self._request_payload(
            method,
            path_or_url,
            json_body=json_body,
            headers=headers,
        )
        if not isinstance(payload, dict):
            raise ProviderMarketplaceError(
                f"{self.adapter_key} returned unexpected payload for {method} {path_or_url}"
            )
        return payload

    def _normalize_offer(self, item: dict[str, Any]) -> ProviderOfferSnapshot:
        provider = _pick_first(item, "provider", "provider_name") or self.marketplace_name
        gpu_type = _pick_first(item, "gpu_type", "gpu", "gpu_name")
        price_per_hour = _safe_decimal(
            _pick_first(item, "price_per_hour", "hourly_price", "price")
        )
        if not gpu_type or price_per_hour is None:
            raise ProviderMarketplaceError(
                f"{self.adapter_key} offer is missing required fields"
            )
        return ProviderOfferSnapshot(
            provider=str(provider),
            gpu_type=str(gpu_type),
            region=str(_pick_first(item, "region", "location", "zone"))
            if _pick_first(item, "region", "location", "zone") is not None
            else None,
            price_per_hour=price_per_hour,
            reliability_score=_safe_decimal(_pick_first(item, "reliability_score", "reliability")),
            startup_score=_safe_decimal(_pick_first(item, "startup_score", "startup")),
            success_rate=_safe_decimal(_pick_first(item, "success_rate", "success")),
            raw_payload=item,
        )

    def _normalize_handle(self, payload: dict[str, Any]) -> ProviderMarketplaceTaskHandle:
        external_task_id = (
            _pick_first(payload, "external_task_id", "task_id", "id", "instance_id")
        )
        if not external_task_id:
            raise ProviderMarketplaceError(
                f"{self.adapter_key} submit response is missing external_task_id"
            )
        return ProviderMarketplaceTaskHandle(
            external_task_id=str(external_task_id),
            accepted=bool(payload.get("accepted", True)),
            status=str(payload.get("status") or payload.get("state") or "submitted"),
            provider=str(payload["provider"]) if payload.get("provider") is not None else None,
            gpu_type=str(payload["gpu_type"]) if payload.get("gpu_type") is not None else None,
            message=str(payload["message"]) if payload.get("message") is not None else None,
            raw_payload=payload,
        )

    def list_offers(self, db: Session) -> list[ProviderOfferSnapshot]:
        del db
        payload = self._request_payload("GET", self.offers_path)
        offer_items: Any | None = None
        if isinstance(payload, dict):
            offer_items = payload.get("offers", payload.get("items", payload.get("data")))
        elif isinstance(payload, list):
            offer_items = payload
        if offer_items is None:
            raise ProviderMarketplaceError(
                f"{self.adapter_key} offer payload is missing offers[]"
            )
        if not isinstance(offer_items, list):
            raise ProviderMarketplaceError(
                f"{self.adapter_key} offer payload must contain a list"
            )
        return [self._normalize_offer(item) for item in offer_items if isinstance(item, dict)]

    def submit_task(
        self,
        db: Session,
        submission: ProviderMarketplaceTaskSubmission,
    ) -> ProviderMarketplaceTaskHandle:
        del db
        payload = self._request_json("POST", self.submit_path, json_body=asdict(submission))
        return self._normalize_handle(payload)

    def get_task_status(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceTaskStatus:
        del db
        path = self.status_path_template.format(external_task_id=external_task_id)
        payload = self._request_json("GET", path)
        progress_percent = _safe_int(
            _pick_first(payload, "progress_percent", "progress", "progressPercent")
        ) or 0
        return ProviderMarketplaceTaskStatus(
            external_task_id=str(
                _pick_first(payload, "external_task_id", "task_id", "id")
                or external_task_id
            ),
            status=str(_pick_first(payload, "status", "state") or "unknown"),
            progress_percent=max(0, min(progress_percent, 100)),
            provider=str(payload["provider"]) if payload.get("provider") is not None else None,
            gpu_type=str(payload["gpu_type"]) if payload.get("gpu_type") is not None else None,
            stage=str(payload["stage"]) if payload.get("stage") is not None else None,
            message=str(payload["message"]) if payload.get("message") is not None else None,
            retryable=bool(payload.get("retryable", False)),
            raw_payload=payload,
        )

    def cancel_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCancelResult:
        del db
        path = self.cancel_path_template.format(external_task_id=external_task_id)
        payload = self._request_json("POST", path)
        return ProviderMarketplaceCancelResult(
            external_task_id=str(
                _pick_first(payload, "external_task_id", "task_id", "id")
                or external_task_id
            ),
            cancelled=bool(payload.get("cancelled", True)),
            status=str(_pick_first(payload, "status", "state") or "cancelled"),
            provider=str(payload["provider"]) if payload.get("provider") is not None else None,
            message=str(payload["message"]) if payload.get("message") is not None else None,
            raw_payload=payload,
        )

    def cleanup_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCleanupResult:
        del db
        path = self.cleanup_path_template.format(external_task_id=external_task_id)
        try:
            payload = self._request_json("POST", path)
        except ProviderMarketplaceError as exc:
            message = str(exc)
            if "404" in message or "405" in message:
                return ProviderMarketplaceCleanupResult(
                    external_task_id=external_task_id,
                    cleaned=False,
                    status="not_supported",
                    provider=self.marketplace_name,
                    message=message,
                    raw_payload={},
                )
            raise

        return ProviderMarketplaceCleanupResult(
            external_task_id=str(
                _pick_first(payload, "external_task_id", "task_id", "id")
                or external_task_id
            ),
            cleaned=bool(payload.get("cleaned", payload.get("success", True))),
            status=str(_pick_first(payload, "status", "state") or "cleaned"),
            provider=str(payload["provider"]) if payload.get("provider") is not None else None,
            message=str(payload["message"]) if payload.get("message") is not None else None,
            raw_payload=payload,
        )

    def collect_task_result(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceResult:
        del db
        path = self.result_path_template.format(external_task_id=external_task_id)
        payload = self._request_json("GET", path)
        artifact_items = payload.get("artifacts", payload.get("outputs", []))
        if not isinstance(artifact_items, list):
            raise ProviderMarketplaceError(
                f"{self.adapter_key} result payload must contain artifacts[]"
            )
        artifacts = [
            ProviderMarketplaceArtifact(
                kind=str(_pick_first(item, "kind", "type") or "artifact"),
                uri=str(_pick_first(item, "uri", "path", "storage_path")),
                download_url=str(_pick_first(item, "download_url", "url"))
                if _pick_first(item, "download_url", "url") is not None
                else None,
                size_bytes=_safe_int(_pick_first(item, "size_bytes", "size", "file_size")),
                checksum=str(item["checksum"]) if item.get("checksum") is not None else None,
                metadata=dict(item.get("metadata") or {}),
            )
            for item in artifact_items
            if isinstance(item, dict)
            and _pick_first(item, "uri", "path", "storage_path") is not None
        ]
        return ProviderMarketplaceResult(
            external_task_id=str(
                _pick_first(payload, "external_task_id", "task_id", "id")
                or external_task_id
            ),
            status=str(_pick_first(payload, "status", "state") or "unknown"),
            provider=str(payload["provider"]) if payload.get("provider") is not None else None,
            summary=str(payload["summary"]) if payload.get("summary") is not None else None,
            artifacts=artifacts,
            usage=dict(payload.get("usage") or {}),
            raw_payload=payload,
        )


@dataclass
class VastAiMarketplaceAdapter(RemoteMarketplaceAdapter):
    adapter_key: str = "vast_ai"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _normalize_offer(self, item: dict[str, Any]) -> ProviderOfferSnapshot:
        gpu_type = _pick_first(item, "gpu_type", "gpu_name", "gpu", "model_name")
        price_per_hour = _safe_decimal(
            _pick_first(item, "price_per_hour", "dph_total", "dph", "hourly_cost")
        )
        if not gpu_type or price_per_hour is None:
            raise ProviderMarketplaceError("vast_ai offer payload is missing gpu/price fields")
        offer_id = _pick_first(item, "id", "ask_id", "ask", "bundle_id")
        return ProviderOfferSnapshot(
            provider="vast.ai",
            gpu_type=str(gpu_type),
            region=str(_pick_first(item, "region", "geolocation", "location"))
            if _pick_first(item, "region", "geolocation", "location") is not None
            else None,
            price_per_hour=price_per_hour,
            reliability_score=_safe_decimal(
                _pick_first(item, "reliability_score", "reliability2", "reliability")
            ),
            startup_score=_safe_decimal(
                _pick_first(item, "startup_score", "verification_score", "verification")
            ),
            success_rate=_safe_decimal(
                _pick_first(item, "success_rate", "success_ratio", "success")
            ),
            raw_payload={**item, "offer_id": offer_id},
        )

    def _search_offers_payload(self) -> dict[str, Any]:
        return {
            "verified": {"eq": True},
            "rentable": {"eq": True},
            "limit": 80,
            "order": [["dph_total", "asc"]],
        }

    def list_offers(self, db: Session) -> list[ProviderOfferSnapshot]:
        del db
        payload = self._request_payload(
            "POST",
            self.offers_path,
            json_body=self._search_offers_payload(),
        )
        offer_items: list[Any] | None = None
        if isinstance(payload, dict):
            offer_items = payload.get("offers", payload.get("items", payload.get("data")))
        elif isinstance(payload, list):
            offer_items = payload
        if offer_items is None:
            raise ProviderMarketplaceError("vast_ai offer payload is missing offers[]")
        return [self._normalize_offer(item) for item in offer_items if isinstance(item, dict)]

    def _resolve_offer_id(
        self,
        db: Session,
        submission: ProviderMarketplaceTaskSubmission,
    ) -> str:
        recommended = (submission.quote_snapshot or {}).get("recommended_offer") or {}
        recommended_payload = recommended.get("raw_payload") or {}
        candidate_offer_id = _pick_first(
            recommended_payload if isinstance(recommended_payload, dict) else {},
            "offer_id",
            "id",
            "ask_id",
            "ask",
            "bundle_id",
        )
        if candidate_offer_id is None:
            candidate_offer_id = _pick_first(
                recommended if isinstance(recommended, dict) else {},
                "offer_id",
                "id",
                "ask_id",
                "ask",
                "bundle_id",
            )
        if candidate_offer_id is not None:
            return str(candidate_offer_id)

        offers = self.list_offers(db)
        preferred_gpu = (submission.preferred_gpu_type or "").strip().lower()
        for offer in offers:
            raw = dict(offer.raw_payload or {})
            offer_id = _pick_first(raw, "offer_id", "id", "ask_id", "ask", "bundle_id")
            if offer_id is None:
                continue
            if preferred_gpu and preferred_gpu not in offer.gpu_type.strip().lower():
                continue
            return str(offer_id)

        for offer in offers:
            raw = dict(offer.raw_payload or {})
            offer_id = _pick_first(raw, "offer_id", "id", "ask_id", "ask", "bundle_id")
            if offer_id is not None:
                return str(offer_id)

        raise ProviderMarketplaceError("vast_ai could not resolve offer_id for task submission")

    def _build_submit_payload(
        self,
        submission: ProviderMarketplaceTaskSubmission,
    ) -> dict[str, Any]:
        runtime = dict(submission.input_payload.get("provider_runtime") or {})
        payload: dict[str, Any] = {
            "image": str(runtime.get("image") or "ubuntu:22.04"),
            "disk": int(runtime.get("disk") or submission.input_payload.get("disk_gb") or 20),
            "runtype": str(runtime.get("runtype") or "ssh_direct"),
            "label": str(runtime.get("label") or f"stablegpu-task-{submission.local_task_id}"),
        }
        optional_keys = [
            "template_hash_id",
            "env",
            "onstart",
            "args",
            "args_str",
            "price",
            "volume_info",
            "image_login",
        ]
        for key in optional_keys:
            value = runtime.get(key)
            if value is not None:
                payload[key] = value
        return payload

    def submit_task(
        self,
        db: Session,
        submission: ProviderMarketplaceTaskSubmission,
    ) -> ProviderMarketplaceTaskHandle:
        offer_id = self._resolve_offer_id(db, submission)
        submit_path = self.submit_path
        if "{offer_id}" in submit_path:
            path = submit_path.format(offer_id=offer_id)
        else:
            path = f"/asks/{offer_id}/"

        payload = self._request_json(
            "PUT",
            path,
            json_body=self._build_submit_payload(submission),
        )
        external_task_id = _pick_first(
            payload,
            "new_contract",
            "instance_id",
            "id",
            "contract_id",
        )
        if external_task_id is None:
            raise ProviderMarketplaceError(
                "vast_ai create instance response is missing instance identifier"
            )

        return ProviderMarketplaceTaskHandle(
            external_task_id=str(external_task_id),
            accepted=bool(payload.get("success", True)),
            status=str(payload.get("status") or "submitted"),
            provider="vast.ai",
            gpu_type=submission.preferred_gpu_type,
            message=str(payload.get("msg") or "vast_ai instance requested"),
            raw_payload={**payload, "offer_id": offer_id},
        )

    def _instance_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        instance_obj = payload.get("instances")
        if isinstance(instance_obj, dict):
            return instance_obj
        if isinstance(instance_obj, list) and instance_obj:
            candidate = instance_obj[0]
            if isinstance(candidate, dict):
                return candidate
        return payload

    def _map_instance_status(self, instance: dict[str, Any]) -> tuple[str, int, str]:
        settings = get_settings()
        raw_status = str(
            _pick_first(instance, "actual_status", "status", "state", "machine_status")
            or "unknown"
        ).strip()
        lowered = raw_status.lower()
        if lowered in {"offline", "failed", "error", "stopped_error"}:
            return "failed", 100, raw_status
        if lowered in {"destroyed", "terminated", "exited"}:
            return "cancelled", 100, raw_status
        if lowered in {"running", "loaded", "ready", "online"}:
            if settings.provider_ready_state_is_success:
                return "succeeded", 100, raw_status
            return "running", 75, raw_status
        if lowered in {"creating", "loading", "initializing", "starting"}:
            return "provisioning", 45, raw_status
        return "running", 65, raw_status

    def get_task_status(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceTaskStatus:
        del db
        path = self.status_path_template.format(external_task_id=external_task_id)
        payload = self._request_json("GET", path)
        instance = self._instance_payload(payload)
        normalized_status, default_progress, raw_status = self._map_instance_status(instance)
        progress_percent = (
            _safe_int(
                _pick_first(instance, "progress_percent", "progress", "progressPercent")
            )
            or default_progress
        )
        gpu_type = _pick_first(instance, "gpu_name", "gpu_type", "gpu")
        return ProviderMarketplaceTaskStatus(
            external_task_id=str(
                _pick_first(instance, "id", "instance_id") or external_task_id
            ),
            status=normalized_status,
            progress_percent=max(0, min(progress_percent, 100)),
            provider="vast.ai",
            gpu_type=str(gpu_type) if gpu_type is not None else None,
            stage=str(_pick_first(instance, "actual_status", "status", "state") or raw_status),
            message=str(_pick_first(instance, "label", "hostname", "msg") or raw_status),
            retryable=normalized_status in {"failed", "cancelled"},
            raw_payload=payload,
        )

    def cancel_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCancelResult:
        del db
        path = self.cancel_path_template.format(external_task_id=external_task_id)
        payload = self._request_json("DELETE", path)
        return ProviderMarketplaceCancelResult(
            external_task_id=external_task_id,
            cancelled=bool(payload.get("success", True)),
            status="cancelled",
            provider="vast.ai",
            message=str(payload.get("msg") or "vast_ai instance cancellation sent"),
            raw_payload=payload,
        )

    def cleanup_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCleanupResult:
        del db
        path = self.cleanup_path_template.format(external_task_id=external_task_id)
        try:
            payload = self._request_json("DELETE", path)
        except ProviderMarketplaceError as exc:
            message = str(exc)
            if "404" in message:
                return ProviderMarketplaceCleanupResult(
                    external_task_id=external_task_id,
                    cleaned=True,
                    status="already_gone",
                    provider="vast.ai",
                    message=message,
                    raw_payload={},
                )
            raise
        return ProviderMarketplaceCleanupResult(
            external_task_id=external_task_id,
            cleaned=bool(payload.get("success", True)),
            status="cleaned",
            provider="vast.ai",
            message=str(payload.get("msg") or "vast_ai cleanup finished"),
            raw_payload=payload,
        )

    def collect_task_result(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceResult:
        del db
        path = self.result_path_template.format(external_task_id=external_task_id)
        payload = self._request_json("GET", path)
        instance = self._instance_payload(payload)

        runtime_seconds = (
            _safe_int(
                _pick_first(instance, "duration", "runtime_seconds", "uptime_seconds")
            )
            or _runtime_seconds_from_datetimes(
                _pick_first(instance, "start_date", "last_update", "created_at"),
                _pick_first(instance, "end_date"),
            )
            or 600
        )
        hourly_price = _safe_decimal(_pick_first(instance, "dph_total", "dph", "cost_per_hour"))
        provider_cost = (
            (hourly_price * Decimal(str(runtime_seconds)) / Decimal("3600")).quantize(
                Decimal("0.0001")
            )
            if hourly_price is not None
            else Decimal("0")
        )

        instance_url = f"{self._require_base_url()}/instances/{external_task_id}/"
        artifact = ProviderMarketplaceArtifact(
            kind="runtime_manifest",
            uri=instance_url,
            download_url=instance_url,
            metadata={
                "provider": "vast.ai",
                "instance_id": external_task_id,
                "gpu_type": _pick_first(instance, "gpu_name", "gpu", "gpu_type"),
                "status": _pick_first(instance, "actual_status", "status"),
            },
        )

        return ProviderMarketplaceResult(
            external_task_id=external_task_id,
            status="succeeded",
            provider="vast.ai",
            summary=str(
                _pick_first(instance, "label", "actual_status", "status")
                or "vast_ai runtime ready"
            ),
            artifacts=[artifact],
            usage={
                "billable_seconds": runtime_seconds,
                "provider_cost": float(provider_cost),
                "hourly_price": float(hourly_price) if hourly_price is not None else None,
            },
            raw_payload=payload,
        )


@dataclass
class RunpodMarketplaceAdapter(RemoteMarketplaceAdapter):
    adapter_key: str = "runpod"
    graphql_url: str = "https://api.runpod.io/graphql"

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        headers["Content-Type"] = "application/json"
        return headers

    def _normalize_offer(self, item: dict[str, Any]) -> ProviderOfferSnapshot:
        gpu_type = _pick_first(item, "gpu_type", "gpuType", "displayName", "name", "id")
        lowest_price = item.get("lowestPrice")
        price_per_hour = None
        if isinstance(lowest_price, dict):
            price_per_hour = _safe_decimal(
                _pick_first(lowest_price, "uninterruptablePrice", "minimumBidPrice")
            )
        if price_per_hour is None:
            price_per_hour = _safe_decimal(
                _pick_first(item, "price_per_hour", "pricePerHour", "price", "lowestPrice")
            )
        if not gpu_type or price_per_hour is None:
            raise ProviderMarketplaceError("runpod offer payload is missing gpu/price fields")
        stock_status = (
            _pick_first(lowest_price, "stockStatus")
            if isinstance(lowest_price, dict)
            else None
        )
        reliability_score = Decimal("0.90")
        if isinstance(stock_status, str):
            status_map = {
                "high": Decimal("0.98"),
                "medium": Decimal("0.92"),
                "low": Decimal("0.80"),
                "none": Decimal("0.45"),
            }
            reliability_score = status_map.get(stock_status.strip().lower(), reliability_score)
        return ProviderOfferSnapshot(
            provider="runpod",
            gpu_type=str(gpu_type),
            region=str(_pick_first(item, "region", "location", "countryCode"))
            if _pick_first(item, "region", "location", "countryCode") is not None
            else None,
            price_per_hour=price_per_hour,
            reliability_score=reliability_score,
            startup_score=_safe_decimal(_pick_first(item, "startup_score", "startup"))
            or Decimal("0.85"),
            success_rate=_safe_decimal(_pick_first(item, "success_rate", "successRate"))
            or Decimal("0.90"),
            raw_payload=item,
        )

    def _graphql_request(self, query: str) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderMarketplaceError("runpod requires API key for GraphQL offers query")
        connector = "&" if "?" in self.graphql_url else "?"
        url = f"{self.graphql_url}{connector}api_key={quote_plus(self.api_key)}"
        payload = self._request_json(
            "POST",
            url,
            json_body={"query": query},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            raise ProviderMarketplaceError(f"runpod graphql returned errors: {errors}")
        return payload

    def list_offers(self, db: Session) -> list[ProviderOfferSnapshot]:
        del db
        query = """
        query {
          gpuTypes {
            id
            displayName
            memoryInGb
            secureCloud
            communityCloud
            lowestPrice(input: { gpuCount: 1 }) {
              minimumBidPrice
              uninterruptablePrice
              stockStatus
              availableGpuCounts
            }
          }
        }
        """
        payload = self._graphql_request(query)
        data = payload.get("data") or {}
        offer_items = data.get("gpuTypes")
        if not isinstance(offer_items, list):
            raise ProviderMarketplaceError("runpod graphql payload is missing gpuTypes[]")
        normalized: list[ProviderOfferSnapshot] = []
        for item in offer_items:
            if isinstance(item, dict):
                normalized.append(self._normalize_offer(item))
        return normalized

    def _resolve_gpu_type_id(
        self,
        db: Session,
        submission: ProviderMarketplaceTaskSubmission,
    ) -> str:
        preferred_gpu = (submission.preferred_gpu_type or "").strip().lower()
        recommended = (submission.quote_snapshot or {}).get("recommended_offer") or {}
        recommended_payload = recommended.get("raw_payload") or {}
        if isinstance(recommended_payload, dict):
            gpu_type_id = _pick_first(recommended_payload, "id", "gpuTypeId", "gpu_type_id")
            if gpu_type_id is not None:
                return str(gpu_type_id)
        if isinstance(recommended, dict):
            gpu_type_id = _pick_first(recommended, "id", "gpuTypeId", "gpu_type_id")
            if gpu_type_id is not None:
                return str(gpu_type_id)

        offers = self.list_offers(db)
        for offer in offers:
            raw = dict(offer.raw_payload or {})
            gpu_type_id = _pick_first(raw, "id", "gpuTypeId", "gpu_type_id")
            if gpu_type_id is None:
                continue
            if preferred_gpu and preferred_gpu not in offer.gpu_type.strip().lower():
                continue
            return str(gpu_type_id)

        for offer in offers:
            raw = dict(offer.raw_payload or {})
            gpu_type_id = _pick_first(raw, "id", "gpuTypeId", "gpu_type_id")
            if gpu_type_id is not None:
                return str(gpu_type_id)

        raise ProviderMarketplaceError("runpod could not resolve gpuTypeId for submission")

    def _build_create_payload(
        self,
        submission: ProviderMarketplaceTaskSubmission,
        gpu_type_id: str,
    ) -> dict[str, Any]:
        runtime = dict(submission.input_payload.get("provider_runtime") or {})
        strategy = submission.strategy.strip().lower()
        cloud_type = str(runtime.get("cloudType") or ("SECURE" if strategy != "cheap" else "ALL"))
        payload: dict[str, Any] = {
            "name": str(runtime.get("name") or f"stablegpu-task-{submission.local_task_id}"),
            "imageName": str(runtime.get("imageName") or runtime.get("image") or "runpod/pytorch:latest"),
            "computeType": str(runtime.get("computeType") or "GPU"),
            "cloudType": cloud_type,
            "gpuTypeIds": runtime.get("gpuTypeIds") or [gpu_type_id],
            "gpuCount": int(runtime.get("gpuCount") or submission.input_payload.get("gpu_count") or 1),
            "volumeInGb": int(runtime.get("volumeInGb") or submission.input_payload.get("volume_gb") or 40),
            "containerDiskInGb": int(
                runtime.get("containerDiskInGb")
                or submission.input_payload.get("container_disk_gb")
                or 40
            ),
            "ports": runtime.get("ports") or ["22/tcp", "8888/http"],
        }
        optional_keys = [
            "dockerEntrypoint",
            "dockerStartCmd",
            "env",
            "interruptible",
            "templateId",
            "networkVolumeId",
            "volumeMountPath",
            "allowedCudaVersions",
            "supportPublicIp",
            "dataCenterIds",
            "countryCodes",
            "minVCPUPerGPU",
            "minRAMPerGPU",
            "vcpuCount",
        ]
        for key in optional_keys:
            value = runtime.get(key)
            if value is not None:
                payload[key] = value
        return payload

    def submit_task(
        self,
        db: Session,
        submission: ProviderMarketplaceTaskSubmission,
    ) -> ProviderMarketplaceTaskHandle:
        gpu_type_id = self._resolve_gpu_type_id(db, submission)
        payload = self._request_json(
            "POST",
            self.submit_path,
            json_body=self._build_create_payload(submission, gpu_type_id),
        )
        external_task_id = _pick_first(payload, "id", "podId", "external_task_id")
        if external_task_id is None:
            raise ProviderMarketplaceError("runpod create pod response is missing id")
        status = str(_pick_first(payload, "desiredStatus", "status") or "submitted")
        return ProviderMarketplaceTaskHandle(
            external_task_id=str(external_task_id),
            accepted=True,
            status=status.lower(),
            provider="runpod",
            gpu_type=str(_pick_first(payload, "gpuTypeId", "gpu", "gpuType") or gpu_type_id),
            message=f"runpod pod created: {status}",
            raw_payload={**payload, "gpu_type_id": gpu_type_id},
        )

    def _map_pod_status(self, payload: dict[str, Any]) -> tuple[str, int, str]:
        settings = get_settings()
        desired_status = str(
            _pick_first(payload, "desiredStatus", "status", "state") or "UNKNOWN"
        ).strip()
        lowered = desired_status.lower()
        if lowered in {"terminated", "error", "failed"}:
            return "failed", 100, desired_status
        if lowered in {"stopping", "stopped"}:
            return "cancelled", 100, desired_status
        if lowered == "exited":
            return "succeeded", 100, desired_status
        if lowered in {"created", "provisioning", "starting"}:
            return "provisioning", 40, desired_status
        if lowered in {"running", "resumed"}:
            if settings.provider_ready_state_is_success:
                return "succeeded", 100, desired_status
            return "running", 75, desired_status
        return "running", 60, desired_status

    def get_task_status(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceTaskStatus:
        del db
        path = self.status_path_template.format(external_task_id=external_task_id)
        payload = self._request_json("GET", path)
        normalized_status, default_progress, raw_status = self._map_pod_status(payload)
        return ProviderMarketplaceTaskStatus(
            external_task_id=str(_pick_first(payload, "id", "podId") or external_task_id),
            status=normalized_status,
            progress_percent=max(0, min(default_progress, 100)),
            provider="runpod",
            gpu_type=str(_pick_first(payload, "gpu", "gpuTypeId", "gpuType"))
            if _pick_first(payload, "gpu", "gpuTypeId", "gpuType") is not None
            else None,
            stage=raw_status,
            message=str(_pick_first(payload, "name", "id") or raw_status),
            retryable=normalized_status in {"failed", "cancelled"},
            raw_payload=payload,
        )

    def cancel_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCancelResult:
        del db
        path = self.cancel_path_template.format(external_task_id=external_task_id)
        payload = self._request_json("POST", path)
        desired_status = str(_pick_first(payload, "desiredStatus", "status") or "EXITED")
        return ProviderMarketplaceCancelResult(
            external_task_id=str(_pick_first(payload, "id", "podId") or external_task_id),
            cancelled=desired_status.strip().lower() in {"exited", "stopped", "terminated"},
            status=desired_status.lower(),
            provider="runpod",
            message=f"runpod stop requested: {desired_status}",
            raw_payload=payload,
        )

    def cleanup_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCleanupResult:
        del db
        path = self.cleanup_path_template.format(external_task_id=external_task_id)
        try:
            payload = self._request_payload("DELETE", path)
        except ProviderMarketplaceError as exc:
            message = str(exc)
            if "404" in message:
                return ProviderMarketplaceCleanupResult(
                    external_task_id=external_task_id,
                    cleaned=True,
                    status="already_gone",
                    provider="runpod",
                    message=message,
                    raw_payload={},
                )
            raise

        payload_dict = payload if isinstance(payload, dict) else {}
        return ProviderMarketplaceCleanupResult(
            external_task_id=str(_pick_first(payload_dict, "id", "podId") or external_task_id),
            cleaned=True,
            status=str(_pick_first(payload_dict, "status", "desiredStatus") or "cleaned").lower(),
            provider="runpod",
            message="runpod pod deleted",
            raw_payload=payload_dict,
        )

    def collect_task_result(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceResult:
        del db
        path = self.result_path_template.format(external_task_id=external_task_id)
        payload = self._request_json("GET", path)

        runtime_seconds = _runtime_seconds_from_datetimes(
            _pick_first(payload, "lastStartedAt"),
            _pick_first(payload, "lastStatusChange"),
        ) or 600
        hourly_cost = _safe_decimal(_pick_first(payload, "adjustedCostPerHr", "costPerHr")) or Decimal("0")
        provider_cost = (
            (hourly_cost * Decimal(str(runtime_seconds)) / Decimal("3600")).quantize(
                Decimal("0.0001")
            )
            if hourly_cost > 0
            else Decimal("0")
        )

        pod_console_url = f"https://www.runpod.io/console/pods/{external_task_id}"
        artifact = ProviderMarketplaceArtifact(
            kind="runtime_manifest",
            uri=pod_console_url,
            download_url=pod_console_url,
            metadata={
                "provider": "runpod",
                "pod_id": external_task_id,
                "desired_status": _pick_first(payload, "desiredStatus", "status"),
            },
        )
        return ProviderMarketplaceResult(
            external_task_id=external_task_id,
            status="succeeded",
            provider="runpod",
            summary=str(
                _pick_first(payload, "name", "desiredStatus", "status")
                or "runpod runtime ready"
            ),
            artifacts=[artifact],
            usage={
                "billable_seconds": runtime_seconds,
                "provider_cost": float(provider_cost),
                "hourly_price": float(hourly_cost),
            },
            raw_payload=payload,
        )


@dataclass
class MultiProviderMarketplaceAdapter:
    vast_adapter: ProviderMarketplaceAdapter
    runpod_adapter: ProviderMarketplaceAdapter
    marketplace_name: str = "vast-runpod-live"
    adapter_key: str = "multi_provider_live"

    def _encode_external_id(self, provider_key: str, external_id: str) -> str:
        return f"{provider_key}::{external_id}"

    def _decode_external_id(
        self,
        external_task_id: str,
    ) -> tuple[ProviderMarketplaceAdapter, str, str]:
        if "::" in external_task_id:
            provider_key, raw_id = external_task_id.split("::", 1)
            if provider_key == "vast_ai":
                return self.vast_adapter, provider_key, raw_id
            if provider_key == "runpod":
                return self.runpod_adapter, provider_key, raw_id
        if external_task_id.startswith("runpod-"):
            return self.runpod_adapter, "runpod", external_task_id
        if external_task_id.startswith("vast-"):
            return self.vast_adapter, "vast_ai", external_task_id
        raise ProviderMarketplaceError(
            f"Unable to route external task id to a provider adapter: {external_task_id}"
        )

    def _choose_adapter(self, provider_hint: str | None) -> tuple[ProviderMarketplaceAdapter, str]:
        hint = (provider_hint or "").strip().lower()
        if "vast" in hint:
            return self.vast_adapter, "vast_ai"
        if "runpod" in hint:
            return self.runpod_adapter, "runpod"
        return self.runpod_adapter, "runpod"

    def list_offers(self, db: Session) -> list[ProviderOfferSnapshot]:
        offers: list[ProviderOfferSnapshot] = []
        errors: list[str] = []
        for adapter in (self.vast_adapter, self.runpod_adapter):
            try:
                offers.extend(adapter.list_offers(db))
            except ProviderMarketplaceError as exc:
                errors.append(str(exc))
        if offers:
            return offers
        raise ProviderMarketplaceError(
            "Multi-provider marketplace failed to fetch offers from every provider: "
            + "; ".join(errors)
        )

    def submit_task(
        self,
        db: Session,
        submission: ProviderMarketplaceTaskSubmission,
    ) -> ProviderMarketplaceTaskHandle:
        provider_hint = submission.preferred_provider
        adapter, provider_key = self._choose_adapter(provider_hint)
        handle = adapter.submit_task(db, submission)
        return ProviderMarketplaceTaskHandle(
            external_task_id=self._encode_external_id(provider_key, handle.external_task_id),
            accepted=handle.accepted,
            status=handle.status,
            provider=handle.provider or provider_hint,
            gpu_type=handle.gpu_type,
            message=handle.message,
            raw_payload={
                "delegated_adapter_key": adapter.adapter_key,
                "delegated_external_task_id": handle.external_task_id,
                "payload": handle.raw_payload,
            },
        )

    def get_task_status(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceTaskStatus:
        adapter, provider_key, raw_id = self._decode_external_id(external_task_id)
        status = adapter.get_task_status(db, raw_id)
        status.external_task_id = self._encode_external_id(provider_key, status.external_task_id)
        return status

    def cancel_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCancelResult:
        adapter, provider_key, raw_id = self._decode_external_id(external_task_id)
        result = adapter.cancel_task(db, raw_id)
        result.external_task_id = self._encode_external_id(provider_key, result.external_task_id)
        return result

    def cleanup_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCleanupResult:
        adapter, provider_key, raw_id = self._decode_external_id(external_task_id)
        result = adapter.cleanup_task(db, raw_id)
        result.external_task_id = self._encode_external_id(provider_key, result.external_task_id)
        return result

    def collect_task_result(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceResult:
        adapter, provider_key, raw_id = self._decode_external_id(external_task_id)
        result = adapter.collect_task_result(db, raw_id)
        result.external_task_id = self._encode_external_id(provider_key, result.external_task_id)
        return result


def build_provider_marketplace_adapter() -> ProviderMarketplaceAdapter:
    settings = get_settings()
    if settings.provider_marketplace_adapter == "database_mock":
        return DatabaseSnapshotMarketplaceAdapter(
            marketplace_name=settings.provider_marketplace_name,
        )
    if settings.provider_marketplace_adapter == "remote_marketplace":
        return RemoteMarketplaceAdapter(
            marketplace_name=settings.provider_marketplace_name,
            base_url=settings.provider_marketplace_base_url,
            api_key=settings.provider_marketplace_api_key,
            request_timeout_seconds=settings.provider_marketplace_request_timeout_seconds,
        )
    if settings.provider_marketplace_adapter == "vast_ai":
        return VastAiMarketplaceAdapter(
            marketplace_name="vast.ai",
            base_url=settings.vast_ai_base_url,
            api_key=settings.vast_ai_api_key,
            request_timeout_seconds=settings.vast_ai_request_timeout_seconds,
            offers_path=settings.vast_ai_offers_path,
            submit_path=settings.vast_ai_submit_path,
            status_path_template=settings.vast_ai_status_path_template,
            cancel_path_template=settings.vast_ai_cancel_path_template,
            result_path_template=settings.vast_ai_result_path_template,
            cleanup_path_template=settings.vast_ai_cleanup_path_template,
        )
    if settings.provider_marketplace_adapter == "runpod":
        return RunpodMarketplaceAdapter(
            marketplace_name="runpod",
            base_url=settings.runpod_base_url,
            graphql_url=settings.runpod_graphql_url,
            api_key=settings.runpod_api_key,
            request_timeout_seconds=settings.runpod_request_timeout_seconds,
            offers_path=settings.runpod_offers_path,
            submit_path=settings.runpod_submit_path,
            status_path_template=settings.runpod_status_path_template,
            cancel_path_template=settings.runpod_cancel_path_template,
            result_path_template=settings.runpod_result_path_template,
            cleanup_path_template=settings.runpod_cleanup_path_template,
        )
    if settings.provider_marketplace_adapter == "multi_provider_live":
        vast_adapter = VastAiMarketplaceAdapter(
            marketplace_name="vast.ai",
            base_url=settings.vast_ai_base_url,
            api_key=settings.vast_ai_api_key,
            request_timeout_seconds=settings.vast_ai_request_timeout_seconds,
            offers_path=settings.vast_ai_offers_path,
            submit_path=settings.vast_ai_submit_path,
            status_path_template=settings.vast_ai_status_path_template,
            cancel_path_template=settings.vast_ai_cancel_path_template,
            result_path_template=settings.vast_ai_result_path_template,
            cleanup_path_template=settings.vast_ai_cleanup_path_template,
        )
        runpod_adapter = RunpodMarketplaceAdapter(
            marketplace_name="runpod",
            base_url=settings.runpod_base_url,
            graphql_url=settings.runpod_graphql_url,
            api_key=settings.runpod_api_key,
            request_timeout_seconds=settings.runpod_request_timeout_seconds,
            offers_path=settings.runpod_offers_path,
            submit_path=settings.runpod_submit_path,
            status_path_template=settings.runpod_status_path_template,
            cancel_path_template=settings.runpod_cancel_path_template,
            result_path_template=settings.runpod_result_path_template,
            cleanup_path_template=settings.runpod_cleanup_path_template,
        )
        return MultiProviderMarketplaceAdapter(
            vast_adapter=vast_adapter,
            runpod_adapter=runpod_adapter,
        )
    raise ProviderMarketplaceError(
        f"Unsupported provider marketplace adapter: {settings.provider_marketplace_adapter}"
    )


class ProviderMarketplaceService:
    def __init__(self) -> None:
        self.adapter = build_provider_marketplace_adapter()

    @property
    def marketplace_name(self) -> str:
        return self.adapter.marketplace_name

    @property
    def adapter_key(self) -> str:
        return self.adapter.adapter_key

    def list_offers(self, db: Session) -> list[ProviderOfferSnapshot]:
        return self.adapter.list_offers(db)

    def build_submission(
        self,
        task: Task,
    ) -> ProviderMarketplaceTaskSubmission:
        return ProviderMarketplaceTaskSubmission.from_task(task)

    def submit_task(
        self,
        db: Session,
        submission: ProviderMarketplaceTaskSubmission,
    ) -> ProviderMarketplaceTaskHandle:
        return self.adapter.submit_task(db, submission)

    def get_task_status(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceTaskStatus:
        return self.adapter.get_task_status(db, external_task_id)

    def cancel_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCancelResult:
        return self.adapter.cancel_task(db, external_task_id)

    def cleanup_task(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceCleanupResult:
        return self.adapter.cleanup_task(db, external_task_id)

    def collect_task_result(
        self,
        db: Session,
        external_task_id: str,
    ) -> ProviderMarketplaceResult:
        return self.adapter.collect_task_result(db, external_task_id)
