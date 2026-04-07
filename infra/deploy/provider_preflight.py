#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass
class CheckResult:
    provider: str
    ok: bool
    status_code: int | None
    endpoint: str
    detail: str


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _cfg(env_file_values: dict[str, str], key: str, default: str = "") -> str:
    return os.getenv(key) or env_file_values.get(key) or default


def _check_vast(
    *,
    base_url: str,
    offers_path: str,
    api_key: str,
    timeout_seconds: float = 20.0,
) -> CheckResult:
    endpoint = f"{base_url.rstrip('/')}{offers_path}"
    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = httpx.get(endpoint, headers=headers, timeout=timeout_seconds)
        payload: Any
        try:
            payload = response.json()
        except Exception:
            payload = None
        if response.status_code == 200 and isinstance(payload, dict):
            offers = payload.get("offers")
            if isinstance(offers, list):
                return CheckResult(
                    provider="vast.ai",
                    ok=True,
                    status_code=response.status_code,
                    endpoint=endpoint,
                    detail=f"offers={len(offers)}",
                )
            return CheckResult(
                provider="vast.ai",
                ok=False,
                status_code=response.status_code,
                endpoint=endpoint,
                detail="response json does not contain offers[]",
            )
        return CheckResult(
            provider="vast.ai",
            ok=False,
            status_code=response.status_code,
            endpoint=endpoint,
            detail=response.text[:300] if response.text else "non-200 response",
        )
    except Exception as exc:
        return CheckResult(
            provider="vast.ai",
            ok=False,
            status_code=None,
            endpoint=endpoint,
            detail=str(exc),
        )


def _check_runpod(
    *,
    base_url: str,
    api_key: str,
    timeout_seconds: float = 20.0,
) -> CheckResult:
    # Runpod's public OpenAPI does not expose a direct "offers" endpoint.
    # Use /pods as a credentials/connectivity probe.
    endpoint = f"{base_url.rstrip('/')}/pods"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = httpx.get(endpoint, headers=headers, timeout=timeout_seconds)
        if response.status_code == 200:
            return CheckResult(
                provider="runpod",
                ok=True,
                status_code=response.status_code,
                endpoint=endpoint,
                detail="authorized",
            )
        return CheckResult(
            provider="runpod",
            ok=False,
            status_code=response.status_code,
            endpoint=endpoint,
            detail=response.text[:300] if response.text else "non-200 response",
        )
    except Exception as exc:
        return CheckResult(
            provider="runpod",
            ok=False,
            status_code=None,
            endpoint=endpoint,
            detail=str(exc),
        )


def main() -> None:
    env_file_path = Path(
        os.getenv("STABLEGPU_SYSTEMD_ENV_FILE", "/opt/stablegpu/repo/.env")
    )
    env_file_values = _load_env_file(env_file_path)

    vast_base_url = _cfg(
        env_file_values,
        "STABLEGPU_VAST_AI_BASE_URL",
        "https://console.vast.ai/api/v0",
    )
    # Vast uses /bundles/ for search offers in current API docs.
    vast_offers_path = _cfg(env_file_values, "STABLEGPU_VAST_AI_OFFERS_PATH", "/bundles/")
    runpod_base_url = _cfg(
        env_file_values,
        "STABLEGPU_RUNPOD_BASE_URL",
        "https://rest.runpod.io/v1",
    )

    vast_key = _cfg(env_file_values, "STABLEGPU_VAST_AI_API_KEY", "")
    runpod_key = _cfg(env_file_values, "STABLEGPU_RUNPOD_API_KEY", "")

    results = [
        _check_vast(base_url=vast_base_url, offers_path=vast_offers_path, api_key=vast_key),
        _check_runpod(base_url=runpod_base_url, api_key=runpod_key),
    ]

    all_ok = all(item.ok for item in results)
    report = {
        "env_file": str(env_file_path),
        "all_ok": all_ok,
        "results": [
            {
                "provider": item.provider,
                "ok": item.ok,
                "status_code": item.status_code,
                "endpoint": item.endpoint,
                "detail": item.detail,
            }
            for item in results
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not all_ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

