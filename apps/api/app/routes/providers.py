from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.task import (
    HomeMetricsResponse,
    ProviderOfferRead,
    QuoteRequest,
    QuoteResponse,
)
from ..services.providers import create_quote, list_offers
from ..services.tasks import build_home_metrics


router = APIRouter(prefix="/api", tags=["providers"])


@router.post("/quotes", response_model=QuoteResponse)
def quotes(payload: QuoteRequest, db: Session = Depends(get_db)) -> QuoteResponse:
    return create_quote(db, payload)


@router.get("/providers/offers", response_model=list[ProviderOfferRead])
def provider_offers(db: Session = Depends(get_db)) -> list[ProviderOfferRead]:
    offers = list_offers(db)
    return [
        ProviderOfferRead(
            provider=offer.provider,
            gpu_type=offer.gpu_type,
            region=offer.region,
            price_per_hour=float(offer.price_per_hour),
            reliability_score=float(offer.reliability_score or 0),
            startup_score=float(offer.startup_score or 0),
            success_rate=float(offer.success_rate or 0),
        )
        for offer in offers
    ]


@router.get("/home/metrics", response_model=HomeMetricsResponse)
def home_metrics(db: Session = Depends(get_db)) -> HomeMetricsResponse:
    return HomeMetricsResponse(**build_home_metrics(db))
