from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.app.database import init_db, reset_database, session_scope
from apps.api.app.main import app
from apps.api.app.services.bootstrap import seed_provider_offers


@pytest.fixture
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    reset_database(f"sqlite:///{db_path.as_posix()}")
    init_db()
    with session_scope() as db:
        seed_provider_offers(db)
    with TestClient(app) as test_client:
        yield test_client
