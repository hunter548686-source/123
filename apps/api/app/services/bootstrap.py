from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ProviderOfferSnapshot, Project, User, Wallet


DEFAULT_OFFERS = [
    {
        "provider": "vast.ai",
        "gpu_type": "RTX 4090",
        "region": "us-west",
        "price_per_hour": Decimal("0.30"),
        "reliability_score": Decimal("0.68"),
        "startup_score": Decimal("0.76"),
        "success_rate": Decimal("0.73"),
    },
    {
        "provider": "runpod",
        "gpu_type": "RTX 4090",
        "region": "us-central",
        "price_per_hour": Decimal("0.59"),
        "reliability_score": Decimal("0.93"),
        "startup_score": Decimal("0.88"),
        "success_rate": Decimal("0.95"),
    },
    {
        "provider": "io.net",
        "gpu_type": "RTX 4090",
        "region": "ap-southeast",
        "price_per_hour": Decimal("0.41"),
        "reliability_score": Decimal("0.79"),
        "startup_score": Decimal("0.71"),
        "success_rate": Decimal("0.82"),
    },
    {
        "provider": "runpod",
        "gpu_type": "A100 80GB",
        "region": "us-east",
        "price_per_hour": Decimal("1.39"),
        "reliability_score": Decimal("0.96"),
        "startup_score": Decimal("0.83"),
        "success_rate": Decimal("0.97"),
    },
]


def seed_provider_offers(db: Session) -> None:
    existing = db.scalar(select(ProviderOfferSnapshot.id).limit(1))
    if existing is not None:
        return

    for item in DEFAULT_OFFERS:
        db.add(
            ProviderOfferSnapshot(
                **item,
                raw_payload={"seed": True},
            )
        )
    db.commit()


def ensure_default_project(db: Session, user: User) -> Project:
    project = db.scalar(
        select(Project).where(Project.user_id == user.id).order_by(Project.id.asc()).limit(1)
    )
    if project is not None:
        return project

    project = Project(
        user_id=user.id,
        name=f"{user.email.split('@', 1)[0]} 的视频项目",
        scene_type="video_generation",
    )
    db.add(project)
    db.flush()
    return project


def ensure_wallet(db: Session, user: User) -> Wallet:
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id).limit(1))
    if wallet is not None:
        return wallet

    wallet = Wallet(user_id=user.id)
    db.add(wallet)
    db.flush()
    return wallet
