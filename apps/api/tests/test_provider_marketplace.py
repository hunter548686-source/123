from __future__ import annotations

from decimal import Decimal

from apps.api.app.config import get_settings
from apps.api.app.database import session_scope
from apps.api.app.models import ProviderOfferSnapshot
from apps.api.app.services import provider_marketplace as provider_marketplace_module
from apps.api.app.services.provider_marketplace import (
    ProviderMarketplaceError,
    ProviderMarketplaceService,
    ProviderMarketplaceTaskSubmission,
)


def test_database_mock_marketplace_adapter_reads_snapshot_rows(client, monkeypatch):
    monkeypatch.setenv("STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER", "database_mock")
    monkeypatch.setenv("STABLEGPU_PROVIDER_MARKETPLACE_NAME", "mock-aggregator")
    get_settings.cache_clear()

    with session_scope() as db:
        db.add(
            ProviderOfferSnapshot(
                provider="custom-provider",
                gpu_type="L40S",
                region="eu-west",
                price_per_hour=Decimal("0.77"),
                reliability_score=Decimal("0.91"),
                startup_score=Decimal("0.84"),
                success_rate=Decimal("0.93"),
                raw_payload={"source": "test"},
            )
        )

    with session_scope() as db:
        service = ProviderMarketplaceService()
        offers = service.list_offers(db)
        submission = ProviderMarketplaceTaskSubmission(
            local_task_id=42,
            task_type="video_generation",
            template_id="template-a",
            strategy="stable",
            execution_mode="cloud",
            input_payload={"prompt": "A neon city flythrough"},
        )
        handle = service.submit_task(db, submission)
        status = service.get_task_status(db, handle.external_task_id)
        cancel = service.cancel_task(db, handle.external_task_id)
        cleanup = service.cleanup_task(db, handle.external_task_id)
        result = service.collect_task_result(db, handle.external_task_id)

    assert service.adapter_key == "database_mock"
    assert service.marketplace_name == "mock-aggregator"
    assert any(offer.provider == "custom-provider" for offer in offers)
    assert status.status == "succeeded"
    assert cancel.cancelled is True
    assert cleanup.cleaned is True
    assert result.artifacts[0].download_url is not None
    get_settings.cache_clear()


def test_remote_marketplace_contract_calls_generic_http_gateway(
    client,
    monkeypatch,
):
    monkeypatch.setenv("STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER", "remote_marketplace")
    monkeypatch.setenv("STABLEGPU_PROVIDER_MARKETPLACE_NAME", "real-aggregator")
    monkeypatch.setenv(
        "STABLEGPU_PROVIDER_MARKETPLACE_BASE_URL", "https://example.com/marketplace"
    )
    monkeypatch.setenv("STABLEGPU_PROVIDER_MARKETPLACE_API_KEY", "dummy-key")
    get_settings.cache_clear()

    submission = ProviderMarketplaceTaskSubmission(
        local_task_id=99,
        task_type="video_generation",
        template_id="template-b",
        strategy="urgent",
        execution_mode="cloud",
        input_payload={"prompt": "Test"},
    )

    calls: list[tuple[str, str, dict | None, dict[str, str]]] = []

    class FakeResponse:
        def __init__(self, payload: dict):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    def fake_request(method, url, headers=None, json=None, timeout=None):
        del timeout
        calls.append((method, url, json, headers or {}))
        if method == "GET" and url.endswith("/offers"):
            return FakeResponse(
                {
                    "offers": [
                        {
                            "provider": "runpod",
                            "gpu_type": "L40S",
                            "region": "us-east",
                            "price_per_hour": 0.88,
                            "reliability_score": 0.97,
                            "startup_score": 0.84,
                            "success_rate": 0.95,
                        }
                    ]
                }
            )
        if method == "POST" and url.endswith("/tasks"):
            return FakeResponse(
                {
                    "external_task_id": "ext-99",
                    "accepted": True,
                    "status": "submitted",
                    "provider": "runpod",
                    "gpu_type": "L40S",
                }
            )
        if method == "GET" and url.endswith("/tasks/ext-99"):
            return FakeResponse(
                {
                    "external_task_id": "ext-99",
                    "status": "running",
                    "progress_percent": 65,
                    "provider": "runpod",
                    "gpu_type": "L40S",
                    "stage": "rendering",
                    "retryable": False,
                }
            )
        if method == "POST" and url.endswith("/tasks/ext-99/cancel"):
            return FakeResponse(
                {
                    "external_task_id": "ext-99",
                    "cancelled": True,
                    "status": "cancelled",
                }
            )
        if method == "POST" and url.endswith("/tasks/ext-99/cleanup"):
            return FakeResponse(
                {
                    "external_task_id": "ext-99",
                    "cleaned": True,
                    "status": "cleaned",
                }
            )
        if method == "GET" and url.endswith("/tasks/ext-99/result"):
            return FakeResponse(
                {
                    "external_task_id": "ext-99",
                    "status": "succeeded",
                    "provider": "runpod",
                    "summary": "done",
                    "artifacts": [
                        {
                            "kind": "video",
                            "uri": "https://cdn.example.com/ext-99.mp4",
                            "download_url": "https://download.example.com/ext-99.mp4",
                            "size_bytes": 1234,
                        }
                    ],
                    "usage": {"billable_seconds": 300, "provider_cost": 1.23},
                }
            )
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(provider_marketplace_module.httpx, "request", fake_request)

    with session_scope() as db:
        service = ProviderMarketplaceService()
        assert service.adapter_key == "remote_marketplace"
        assert service.marketplace_name == "real-aggregator"
        offers = service.list_offers(db)
        handle = service.submit_task(db, submission)
        status = service.get_task_status(db, "ext-99")
        cancel = service.cancel_task(db, "ext-99")
        cleanup = service.cleanup_task(db, "ext-99")
        result = service.collect_task_result(db, "ext-99")

    assert len(offers) == 1
    assert offers[0].provider == "runpod"
    assert str(offers[0].price_per_hour) == "0.88"
    assert handle.external_task_id == "ext-99"
    assert status.status == "running"
    assert cancel.cancelled is True
    assert cleanup.cleaned is True
    assert result.artifacts[0].download_url is not None
    assert all(call[3]["Authorization"] == "Bearer " + "dummy-key" for call in calls)
    get_settings.cache_clear()


def test_vast_and_runpod_adapters_normalize_provider_payloads(client, monkeypatch):
    monkeypatch.setenv("STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER", "vast_ai")
    monkeypatch.setenv("STABLEGPU_VAST_AI_API_KEY", "vast-key")
    monkeypatch.setenv("STABLEGPU_VAST_AI_BASE_URL", "https://vast.example/api/v0")
    get_settings.cache_clear()

    class FakeResponse:
        def __init__(self, payload: dict):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    def fake_vast_request(method, url, headers=None, json=None, timeout=None):
        del json, timeout
        assert headers is not None and headers.get("Authorization") == "Bearer vast-key"
        if method == "GET" and url.endswith("/offers"):
            return FakeResponse(
                {
                    "offers": [
                        {
                            "gpu_name": "RTX 4090",
                            "dph_total": 0.39,
                            "region": "us-west",
                            "reliability2": 0.72,
                            "verification_score": 0.82,
                            "success_ratio": 0.88,
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(provider_marketplace_module.httpx, "request", fake_vast_request)

    with session_scope() as db:
        service = ProviderMarketplaceService()
        offers = service.list_offers(db)

    assert service.adapter_key == "vast_ai"
    assert offers[0].provider == "vast.ai"
    assert offers[0].gpu_type == "RTX 4090"
    assert str(offers[0].price_per_hour) == "0.39"

    monkeypatch.setenv("STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER", "runpod")
    monkeypatch.setenv("STABLEGPU_RUNPOD_API_KEY", "runpod-key")
    monkeypatch.setenv("STABLEGPU_RUNPOD_BASE_URL", "https://runpod.example/v1")
    get_settings.cache_clear()

    def fake_runpod_request(method, url, headers=None, json=None, timeout=None):
        del json, timeout
        assert headers is not None and headers.get("Authorization") == "Bearer runpod-key"
        if method == "GET" and url.endswith("/offers"):
            return FakeResponse(
                {
                    "offers": [
                        {
                            "displayName": "A100 80GB",
                            "secureCloud": {"lowestPrice": 1.29},
                            "region": "us-east",
                            "successRate": 0.96,
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected request: {method} {url}")

    monkeypatch.setattr(provider_marketplace_module.httpx, "request", fake_runpod_request)

    with session_scope() as db:
        service = ProviderMarketplaceService()
        offers = service.list_offers(db)

    assert service.adapter_key == "runpod"
    assert offers[0].provider == "runpod"
    assert offers[0].gpu_type == "A100 80GB"
    assert str(offers[0].price_per_hour) == "1.29"
    get_settings.cache_clear()


def test_remote_marketplace_requires_base_url(client, monkeypatch):
    monkeypatch.setenv("STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER", "remote_marketplace")
    monkeypatch.setenv("STABLEGPU_PROVIDER_MARKETPLACE_NAME", "real-aggregator")
    monkeypatch.delenv("STABLEGPU_PROVIDER_MARKETPLACE_BASE_URL", raising=False)
    monkeypatch.setenv("STABLEGPU_PROVIDER_MARKETPLACE_API_KEY", "dummy-key")
    get_settings.cache_clear()

    with session_scope() as db:
        service = ProviderMarketplaceService()
        try:
            service.list_offers(db)
        except ProviderMarketplaceError as exc:
            assert "base URL" in str(exc)
        else:
            raise AssertionError("expected ProviderMarketplaceError")
    get_settings.cache_clear()
