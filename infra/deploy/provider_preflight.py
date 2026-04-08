#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib import error as urlerror
from urllib import request as urlrequest


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


def _http_json(
    method: str,
    endpoint: str,
    headers: dict[str, str],
    timeout_seconds: float,
    json_body: dict[str, Any] | None = None,
) -> tuple[int, str, Any | None]:
    body_bytes = None
    request_headers = dict(headers)
    if json_body is not None:
        body_bytes = json.dumps(json_body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = urlrequest.Request(
        endpoint,
        headers=request_headers,
        data=body_bytes,
        method=method.upper(),
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout_seconds) as resp:
            status = int(resp.status)
            text = resp.read().decode("utf-8", errors="replace")
    except urlerror.HTTPError as exc:
        status = int(exc.code)
        text = exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc

    parsed: Any | None = None
    try:
        parsed = json.loads(text) if text else None
    except Exception:
        parsed = None
    return status, text, parsed


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
        status_code, raw_text, payload = _http_json(
            "POST",
            endpoint,
            headers,
            timeout_seconds,
            json_body={
                "verified": {"eq": True},
                "rentable": {"eq": True},
                "limit": 3,
            },
        )
        if status_code == 200 and isinstance(payload, (dict, list)):
            if isinstance(payload, list):
                offers = payload
            else:
                offers = payload.get("offers", payload.get("items", payload.get("data")))
            if isinstance(offers, list):
                return CheckResult(
                    provider="vast.ai",
                    ok=True,
                    status_code=status_code,
                    endpoint=endpoint,
                    detail=f"offers={len(offers)}",
                )
        return CheckResult(
            provider="vast.ai",
            ok=False,
            status_code=status_code,
            endpoint=endpoint,
            detail=raw_text[:300] if raw_text else "non-200 response",
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
    graphql_url: str,
    api_key: str,
    timeout_seconds: float = 20.0,
) -> CheckResult:
    endpoint = f"{base_url.rstrip('/')}/pods"
    if not api_key:
        return CheckResult(
            provider="runpod",
            ok=False,
            status_code=None,
            endpoint=endpoint,
            detail="missing STABLEGPU_RUNPOD_API_KEY",
        )
    headers = {"Accept": "application/json", "Authorization": f"Bearer {api_key}"}
    try:
        status_code, raw_text, _ = _http_json("GET", endpoint, headers, timeout_seconds)
        if status_code != 200:
            return CheckResult(
                provider="runpod",
                ok=False,
                status_code=status_code,
                endpoint=endpoint,
                detail=raw_text[:300] if raw_text else "non-200 response",
            )

        graphql_endpoint = (
            f"{graphql_url.rstrip('/')}?api_key={quote_plus(api_key)}"
            if "?" not in graphql_url
            else f"{graphql_url}&api_key={quote_plus(api_key)}"
        )
        gql_status, gql_text, gql_payload = _http_json(
            "POST",
            graphql_endpoint,
            {"Accept": "application/json"},
            timeout_seconds,
            json_body={"query": "query { gpuTypes { id } }"},
        )
        if gql_status == 200 and isinstance(gql_payload, dict):
            types = ((gql_payload.get("data") or {}).get("gpuTypes")) if gql_payload else None
            if isinstance(types, list):
                return CheckResult(
                    provider="runpod",
                    ok=True,
                    status_code=gql_status,
                    endpoint=graphql_endpoint,
                    detail=f"gpuTypes={len(types)}",
                )
        return CheckResult(
            provider="runpod",
            ok=False,
            status_code=gql_status,
            endpoint=graphql_endpoint,
            detail=gql_text[:300] if gql_text else "graphql query failed",
        )
    except Exception as exc:
        return CheckResult(
            provider="runpod",
            ok=False,
            status_code=None,
            endpoint=endpoint,
            detail=str(exc),
        )


def _mask_key(value: str) -> str:
    if not value:
        return value
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


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
    runpod_graphql_url = _cfg(
        env_file_values,
        "STABLEGPU_RUNPOD_GRAPHQL_URL",
        "https://api.runpod.io/graphql",
    )

    vast_key = _cfg(env_file_values, "STABLEGPU_VAST_AI_API_KEY", "")
    runpod_key = _cfg(env_file_values, "STABLEGPU_RUNPOD_API_KEY", "")

    results = [
        _check_vast(base_url=vast_base_url, offers_path=vast_offers_path, api_key=vast_key),
        _check_runpod(
            base_url=runpod_base_url,
            graphql_url=runpod_graphql_url,
            api_key=runpod_key,
        ),
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
        "runpod_api_key_masked": _mask_key(runpod_key),
        "vast_api_key_masked": _mask_key(vast_key),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not all_ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
