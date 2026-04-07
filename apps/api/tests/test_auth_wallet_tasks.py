from __future__ import annotations

import json

from apps.api.app.config import get_settings
from apps.worker.worker.scheduler import process_pending_tasks


def test_auth_wallet_quote_and_task_flow(client):
    register = client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "phone": "123456789",
            "password": "pass1234",
        },
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    recharge = client.post(
        "/api/wallet/recharge",
        headers=headers,
        json={"amount": 100, "method": "manual"},
    )
    assert recharge.status_code == 200
    assert float(recharge.json()["wallet"]["balance"]) >= 100

    quote = client.post(
        "/api/quotes",
        json={
            "task_type": "text_to_video",
            "strategy": "cheap",
            "duration_seconds": 8,
            "resolution": "1080p",
            "output_count": 1,
            "execution_mode": "hybrid",
        },
    )
    assert quote.status_code == 200
    recommended = quote.json()["recommended_offer"]

    task = client.post(
        "/api/tasks",
        headers=headers,
        json={
            "project_id": 1,
            "task_type": "text_to_video",
            "template_id": "wanx-v1",
            "strategy": "cheap",
            "execution_mode": "hybrid",
            "input_payload": {
                "prompt": "city skyline cinematic",
                "duration_seconds": 8,
                "resolution": "1080p",
                "retry_limit": 2,
            },
            "quote_snapshot": {
                "estimated_price": quote.json()["estimated_price"],
                "estimated_runtime_minutes": quote.json()["estimated_runtime_minutes"],
                "recommended_offer": recommended,
            },
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    processed = process_pending_tasks(limit=10)
    assert processed
    assert processed[0]["task_id"] == task_id

    detail = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["task"]["status"] == "completed"
    assert body["task"]["execution_status"] == "completed"
    assert body["task"]["review_status"] == "completed"
    assert body["task"]["result_summary"]
    assert body["runs"]
    assert body["runs"][0]["external_task_id"]
    assert body["events"]
    assert body["artifacts"]
    assert body["artifacts"][0]["storage_path"].endswith(".mp4")
    assert "download_url" in body["artifacts"][0]
    assert "checksum" in body["artifacts"][0]

    download = client.get(
        f"/api/tasks/{task_id}/artifacts/{body['artifacts'][0]['id']}/download",
        headers=headers,
    )
    assert download.status_code == 200
    assert download.json()["download_url"]

    monitoring = client.get("/api/admin/monitoring/overview", headers=headers)
    assert monitoring.status_code == 200
    assert monitoring.json()["adapter_key"]
    assert "status_breakdown" in monitoring.json()

    home_metrics = client.get("/api/home/metrics")
    assert home_metrics.status_code == 200
    metrics_payload = home_metrics.json()
    assert metrics_payload["provider_count"] >= 1
    assert metrics_payload["average_delivery_seconds"] >= 0
    assert metrics_payload["sample_size_7d"] >= 1
    assert metrics_payload["success_rate_7d"] >= 0


def test_review_failure_generates_fix_loop(client):
    register = client.post(
        "/api/auth/register",
        json={
            "email": "reviewer@example.com",
            "phone": "123456780",
            "password": "pass1234",
        },
    )
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/wallet/recharge", headers=headers, json={"amount": 100, "method": "manual"})
    quote = client.post(
        "/api/quotes",
        json={
            "task_type": "text_to_video",
            "strategy": "stable",
            "duration_seconds": 8,
            "resolution": "1080p",
            "output_count": 1,
            "execution_mode": "hybrid",
        },
    )

    task = client.post(
        "/api/tasks",
        headers=headers,
        json={
            "project_id": 1,
            "task_type": "text_to_video",
            "template_id": "wanx-v1",
            "strategy": "stable",
            "execution_mode": "hybrid",
            "input_payload": {
                "prompt": "forest cinematic",
                "duration_seconds": 8,
                "resolution": "1080p",
                "retry_limit": 2,
                "force_review_fail_once": True,
            },
            "quote_snapshot": {
                "estimated_price": quote.json()["estimated_price"],
                "estimated_runtime_minutes": quote.json()["estimated_runtime_minutes"],
            },
        },
    )
    task_id = task.json()["id"]

    process_pending_tasks(limit=10)

    detail = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["task"]["status"] == "completed"
    review_warn_events = [event for event in body["events"] if event["level"] == "warn"]
    assert review_warn_events


def test_admin_code_edit_links_to_task_history(client, monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "sample.txt"
    target.write_text("hello world", encoding="utf-8")

    monkeypatch.setenv("STABLEGPU_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("STABLEGPU_ENABLE_LOCAL_EXECUTOR", "true")
    get_settings.cache_clear()

    def fake_run_prompt(self, prompt: str, model: str | None = None):
        if "update greeting again" in prompt:
            old = "hello stablegpu"
            new = "hello stablegpu v2"
        else:
            old = "hello world"
            new = "hello stablegpu"
        return {
            "mode": "test-local-model",
            "note": json.dumps(
                {
                    "summary": "linked code edit",
                    "operations": [
                        {
                            "path": "sample.txt",
                            "old": old,
                            "new": new,
                        }
                    ],
                }
            ),
        }

    monkeypatch.setattr(
        "apps.worker.worker.local_executor.LocalExecutor.run_prompt", fake_run_prompt
    )

    register = client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "phone": "123456700",
            "password": "pass1234",
        },
    )
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/wallet/recharge",
        headers=headers,
        json={"amount": 100, "method": "manual"},
    )

    quote = client.post(
        "/api/quotes",
        json={
            "task_type": "text_to_video",
            "strategy": "stable",
            "duration_seconds": 8,
            "resolution": "1080p",
            "output_count": 1,
            "execution_mode": "hybrid",
        },
    )

    task = client.post(
        "/api/tasks",
        headers=headers,
        json={
            "project_id": 1,
            "task_type": "text_to_video",
            "template_id": "wanx-v1",
            "strategy": "stable",
            "execution_mode": "hybrid",
            "input_payload": {
                "prompt": "task bound code edit",
                "duration_seconds": 8,
                "resolution": "1080p",
                "retry_limit": 2,
                "force_review_fail_once": True,
            },
            "quote_snapshot": {
                "estimated_price": quote.json()["estimated_price"],
                "estimated_runtime_minutes": quote.json()["estimated_runtime_minutes"],
            },
        },
    )
    task_id = task.json()["id"]

    response = client.post(
        "/api/admin/execution/code-edit",
        headers=headers,
        json={
            "instructions": "update greeting",
            "files": ["sample.txt"],
            "test_commands": ["python -c \"print('ok')\""],
            "task_id": task_id,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert payload["review_chain_id"] is not None
    assert payload["chain_step_no"] == 1
    first_chain_id = payload["review_chain_id"]

    second = client.post(
        "/api/admin/execution/code-edit",
        headers=headers,
        json={
            "instructions": "update greeting again",
            "files": ["sample.txt"],
            "test_commands": [],
            "task_id": task_id,
        },
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["review_chain_id"] == first_chain_id
    assert second_payload["chain_step_no"] == 2

    assert payload["review_round"] == 0
    assert payload["review_approved"] is None

    process_pending_tasks(limit=10)

    detail = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["code_edit_chains"]
    assert body["code_edit_chains"][0]["id"] == first_chain_id
    assert body["code_edit_chains"][0]["status"] == "approved"
    assert body["code_edit_chains"][0]["current_review_round"] == 1
    assert body["code_edits"]
    assert body["code_edits"][0]["task_id"] == task_id
    assert all(item["review_chain_id"] == first_chain_id for item in body["code_edits"])
    assert all(item["review_chain_status"] == "approved" for item in body["code_edits"])
    assert all(item["review_approved"] is True for item in body["code_edits"])
    code_editor_events = [
        event for event in body["events"] if event["source"] == "code_editor"
    ]
    assert code_editor_events
    review_chain_events = [
        event for event in body["events"] if event["source"] == "review_chain"
    ]
    assert review_chain_events
    get_settings.cache_clear()


def test_admin_task_management_and_users_overview(client):
    register = client.post(
        "/api/auth/register",
        json={
            "email": "ops-admin@example.com",
            "phone": "18800000000",
            "password": "pass1234",
        },
    )
    assert register.status_code == 200
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/wallet/recharge",
        headers=headers,
        json={"amount": 200, "method": "manual"},
    )

    quote = client.post(
        "/api/quotes",
        json={
            "task_type": "text_to_video",
            "strategy": "stable",
            "duration_seconds": 8,
            "resolution": "1080p",
            "output_count": 1,
            "execution_mode": "hybrid",
        },
    )
    assert quote.status_code == 200

    created_task_ids: list[int] = []
    for strategy in ["stable", "cheap"]:
        created = client.post(
            "/api/tasks",
            headers=headers,
            json={
                "project_id": 1,
                "task_type": "text_to_video",
                "template_id": "wanx-v1",
                "strategy": strategy,
                "execution_mode": "hybrid",
                "input_payload": {
                    "prompt": f"ops-admin-{strategy}",
                    "duration_seconds": 8,
                    "resolution": "1080p",
                    "retry_limit": 2,
                },
                "quote_snapshot": {
                    "estimated_price": quote.json()["estimated_price"],
                    "estimated_runtime_minutes": quote.json()[
                        "estimated_runtime_minutes"
                    ],
                },
            },
        )
        assert created.status_code == 200
        created_task_ids.append(created.json()["id"])

    listing = client.get("/api/admin/tasks", headers=headers)
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["summary"]["total"] >= 2
    assert len(payload["items"]) >= 2

    task_id = created_task_ids[0]
    detail = client.get(f"/api/admin/tasks/{task_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["task"]["id"] == task_id

    retry_resp = client.post(f"/api/admin/tasks/{task_id}/retry", headers=headers)
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == "retrying"

    cancel_resp = client.post(
        f"/api/admin/tasks/{created_task_ids[1]}/cancel",
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] in {"cancelling", "cancelled"}

    users = client.get("/api/admin/users", headers=headers)
    assert users.status_code == 200
    users_payload = users.json()
    assert users_payload
    admin_user = next(item for item in users_payload if item["email"] == "ops-admin@example.com")
    assert admin_user["role"] == "admin"
    assert admin_user["total_tasks"] >= 2
