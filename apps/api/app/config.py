from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DATABASE_URL = f"sqlite:///{(DATA_DIR / 'stablegpu.db').as_posix()}"


class Settings(BaseSettings):
    app_name: str = "StableGPU API"
    database_url: str = DEFAULT_DATABASE_URL
    api_secret_key: str = "stablegpu-dev-secret-2026-minimum-32bytes"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3010",
        "http://127.0.0.1:3010",
    ]

    worker_poll_interval: float = 1.0
    worker_poll_max_attempts: int = 8
    review_max_rounds: int = 2
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    planning_model: str = "gpt-5.4"
    review_model: str = "gpt-5.4"
    workspace_root: str = str(ROOT_DIR)
    code_edit_max_files: int = 6
    code_edit_max_chars_per_file: int = 8000
    code_edit_max_test_commands: int = 3
    provider_marketplace_adapter: str = "database_mock"
    provider_marketplace_name: str = "mock-aggregator"
    provider_marketplace_base_url: str | None = None
    provider_marketplace_api_key: str | None = None
    provider_marketplace_request_timeout_seconds: float = 30.0
    vast_ai_base_url: str = "https://console.vast.ai/api/v0"
    vast_ai_api_key: str | None = None
    vast_ai_request_timeout_seconds: float = 30.0
    vast_ai_offers_path: str = "/offers"
    vast_ai_submit_path: str = "/tasks"
    vast_ai_status_path_template: str = "/tasks/{external_task_id}"
    vast_ai_cancel_path_template: str = "/tasks/{external_task_id}/cancel"
    vast_ai_result_path_template: str = "/tasks/{external_task_id}/result"
    vast_ai_cleanup_path_template: str = "/tasks/{external_task_id}/cleanup"
    runpod_base_url: str = "https://rest.runpod.io/v1"
    runpod_api_key: str | None = None
    runpod_request_timeout_seconds: float = 30.0
    runpod_offers_path: str = "/offers"
    runpod_submit_path: str = "/tasks"
    runpod_status_path_template: str = "/tasks/{external_task_id}"
    runpod_cancel_path_template: str = "/tasks/{external_task_id}/cancel"
    runpod_result_path_template: str = "/tasks/{external_task_id}/result"
    runpod_cleanup_path_template: str = "/tasks/{external_task_id}/cleanup"
    enable_local_executor: bool = False
    wsl_distro: str = "Ubuntu-24.04"
    ollama_model: str = "qwen2.5-coder:14b"
    ollama_planner_model: str | None = None
    ollama_reviewer_model: str | None = None
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_request_timeout_seconds: float = 180.0
    ollama_command_template: str = (
        "wsl -d {distro} bash -lc \"ollama run {model} \\\"{prompt}\\\"\""
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STABLEGPU_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
