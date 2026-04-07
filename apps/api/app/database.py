from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Base


_ENGINE = None
_SESSION_FACTORY = None
_DATABASE_URL = None


def _build_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, connect_args=connect_args)


def get_engine():
    global _ENGINE, _DATABASE_URL
    settings = get_settings()
    if _ENGINE is None or _DATABASE_URL != settings.database_url:
        _ENGINE = _build_engine(settings.database_url)
        _DATABASE_URL = settings.database_url
    return _ENGINE


def get_session_factory():
    global _SESSION_FACTORY
    engine = get_engine()
    if _SESSION_FACTORY is None or _SESSION_FACTORY.kw["bind"] is not engine:
        _SESSION_FACTORY = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _SESSION_FACTORY


def reset_database(database_url: str | None = None) -> None:
    global _ENGINE, _SESSION_FACTORY, _DATABASE_URL
    if database_url is not None:
        os.environ["STABLEGPU_DATABASE_URL"] = database_url
        get_settings.cache_clear()
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
    _SESSION_FACTORY = None
    _DATABASE_URL = None


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
