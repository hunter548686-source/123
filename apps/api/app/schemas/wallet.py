from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class WalletRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    balance: Decimal
    frozen_balance: Decimal
    currency: str
    created_at: datetime


class WalletLedgerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    amount: Decimal
    balance_after: Decimal
    ref_type: str | None
    ref_id: str | None
    created_at: datetime


class RechargeRequest(BaseModel):
    amount: float = Field(gt=0)
    method: str = "manual"


class WalletBundleResponse(BaseModel):
    wallet: WalletRead
    ledger: list[WalletLedgerRead]
