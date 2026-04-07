from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, WalletLedger
from ..schemas.wallet import (
    RechargeRequest,
    WalletBundleResponse,
    WalletLedgerRead,
    WalletRead,
)
from ..services.bootstrap import ensure_wallet


router = APIRouter(prefix="/api/wallet", tags=["wallet"])


@router.get("", response_model=WalletRead)
def get_wallet(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WalletRead:
    wallet = ensure_wallet(db, user)
    db.commit()
    return WalletRead.model_validate(wallet)


@router.post("/recharge", response_model=WalletBundleResponse)
def recharge(
    payload: RechargeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WalletBundleResponse:
    wallet = ensure_wallet(db, user)
    wallet.balance = Decimal(wallet.balance) + Decimal(str(payload.amount))
    ledger = WalletLedger(
        wallet_id=wallet.id,
        type="recharge",
        amount=Decimal(str(payload.amount)),
        balance_after=Decimal(wallet.balance),
        ref_type="manual",
        ref_id=payload.method,
    )
    db.add(ledger)
    db.commit()
    db.refresh(wallet)
    items = list(
        db.scalars(
            select(WalletLedger)
            .where(WalletLedger.wallet_id == wallet.id)
            .order_by(WalletLedger.created_at.desc())
        )
    )
    return WalletBundleResponse(
        wallet=WalletRead.model_validate(wallet),
        ledger=[WalletLedgerRead.model_validate(item) for item in items],
    )


@router.get("/ledger", response_model=list[WalletLedgerRead])
def get_ledger(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WalletLedgerRead]:
    wallet = ensure_wallet(db, user)
    items = list(
        db.scalars(
            select(WalletLedger)
            .where(WalletLedger.wallet_id == wallet.id)
            .order_by(WalletLedger.created_at.desc())
        )
    )
    return [WalletLedgerRead.model_validate(item) for item in items]
