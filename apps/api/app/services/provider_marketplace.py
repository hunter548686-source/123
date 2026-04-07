from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Protocol

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


def _pick_first(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


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

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._require_base_url()}{path}"
        try:
            response = httpx.request(
                method,
                url,
                headers=self._headers(),
                json=json_body,
                timeout=self.request_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderMarketplaceError(
                f"{self.adapter_key} request failed: {method} {path}: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderMarketplaceError(
                f"{self.adapter_key} returned non-JSON response for {method} {path}"
            ) from exc

        if not isinstance(payload, dict):
            raise ProviderMarketplaceError(
                f"{self.adapter_key} returned unexpected payload for {method} {path}"
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
        payload = self._request_json("GET", self.offers_path)
        offer_items = payload.get("offers", payload.get("items", payload.get("data")))
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
            raw_payload=item,
        )


@dataclass
class RunpodMarketplaceAdapter(RemoteMarketplaceAdapter):
    adapter_key: str = "runpod"

    def _normalize_offer(self, item: dict[str, Any]) -> ProviderOfferSnapshot:
        gpu_type = _pick_first(item, "gpu_type", "gpuType", "displayName", "name")
        price_per_hour = _safe_decimal(
            _pick_first(item, "price_per_hour", "pricePerHour", "price", "lowestPrice")
        )
        if price_per_hour is None and isinstance(item.get("secureCloud"), dict):
            price_per_hour = _safe_decimal(item["secureCloud"].get("lowestPrice"))
        if price_per_hour is None and isinstance(item.get("communityCloud"), dict):
            price_per_hour = _safe_decimal(item["communityCloud"].get("lowestPrice"))
        if not gpu_type or price_per_hour is None:
            raise ProviderMarketplaceError("runpod offer payload is missing gpu/price fields")
        region = _pick_first(item, "region", "location", "dataCenterId", "countryCode")
        return ProviderOfferSnapshot(
            provider="runpod",
            gpu_type=str(gpu_type),
            region=str(region) if region is not None else None,
            price_per_hour=price_per_hour,
            reliability_score=_safe_decimal(_pick_first(item, "reliability_score", "reliability")),
            startup_score=_safe_decimal(_pick_first(item, "startup_score", "startup")),
            success_rate=_safe_decimal(_pick_first(item, "success_rate", "successRate")),
            raw_payload=item,
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
