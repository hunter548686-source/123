from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from sqlalchemy.orm import Session

from ..enums import TaskStrategy
from ..models import ProviderOfferSnapshot
from ..schemas.task import ProviderOfferRead, QuoteRequest, QuoteResponse
from .provider_marketplace import ProviderMarketplaceService


SERVICE_FEE_BY_STRATEGY = {
    TaskStrategy.CHEAP.value: Decimal("1.18"),
    TaskStrategy.STABLE.value: Decimal("1.28"),
    TaskStrategy.URGENT.value: Decimal("1.42"),
}

STRATEGY_WEIGHTS = {
    TaskStrategy.CHEAP.value: {
        "price": 0.55,
        "reliability": 0.15,
        "startup": 0.15,
        "success": 0.15,
    },
    TaskStrategy.STABLE.value: {
        "price": 0.15,
        "reliability": 0.35,
        "startup": 0.15,
        "success": 0.35,
    },
    TaskStrategy.URGENT.value: {
        "price": 0.10,
        "reliability": 0.20,
        "startup": 0.45,
        "success": 0.25,
    },
}


def _to_float(value: Decimal | None) -> float:
    return float(value or 0)


def estimate_runtime_minutes(
    task_type: str,
    duration_seconds: int,
    resolution: str,
    output_count: int,
) -> int:
    resolution_factor = {"720p": 1.0, "1080p": 1.3, "4k": 2.0}.get(resolution.lower(), 1.2)
    task_factor = 1.4 if "video" in task_type else 1.0
    minutes = max(8, round(duration_seconds * resolution_factor * output_count * task_factor))
    return minutes


def _normalize(values: list[float], invert: bool = False) -> list[float]:
    minimum = min(values)
    maximum = max(values)
    if maximum == minimum:
        return [1.0 for _ in values]
    normalized = [(value - minimum) / (maximum - minimum) for value in values]
    if invert:
        normalized = [1 - value for value in normalized]
    return normalized


def score_offers(
    offers: Iterable[ProviderOfferSnapshot],
    strategy: str,
    *,
    exclude_providers: set[str] | None = None,
    estimated_runtime_minutes: int = 12,
) -> list[dict]:
    offer_list = list(offers)
    if exclude_providers:
        offer_list = [offer for offer in offer_list if offer.provider not in exclude_providers]
    if not offer_list:
        return []

    weights = STRATEGY_WEIGHTS.get(strategy, STRATEGY_WEIGHTS[TaskStrategy.STABLE.value])
    price_scores = _normalize([_to_float(offer.price_per_hour) for offer in offer_list], invert=True)
    reliability_scores = _normalize([_to_float(offer.reliability_score) for offer in offer_list])
    startup_scores = _normalize([_to_float(offer.startup_score) for offer in offer_list])
    success_scores = _normalize([_to_float(offer.success_rate) for offer in offer_list])

    ranked: list[dict] = []
    for index, offer in enumerate(offer_list):
        score = (
            price_scores[index] * weights["price"]
            + reliability_scores[index] * weights["reliability"]
            + startup_scores[index] * weights["startup"]
            + success_scores[index] * weights["success"]
        )
        estimated_price = (
            Decimal(str(_to_float(offer.price_per_hour)))
            * Decimal(estimated_runtime_minutes)
            / Decimal(60)
            * SERVICE_FEE_BY_STRATEGY.get(strategy, Decimal("1.28"))
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        ranked.append(
            {
                "provider": offer.provider,
                "gpu_type": offer.gpu_type,
                "region": offer.region,
                "price_per_hour": round(_to_float(offer.price_per_hour), 4),
                "reliability_score": round(_to_float(offer.reliability_score), 4),
                "startup_score": round(_to_float(offer.startup_score), 4),
                "success_rate": round(_to_float(offer.success_rate), 4),
                "score": round(score, 4),
                "estimated_price": float(estimated_price),
                "estimated_runtime_minutes": estimated_runtime_minutes,
            }
        )
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def list_offers(db: Session) -> list[ProviderOfferSnapshot]:
    marketplace = ProviderMarketplaceService()
    return marketplace.list_offers(db)


def create_quote(db: Session, payload: QuoteRequest) -> QuoteResponse:
    offers = list_offers(db)
    runtime_minutes = estimate_runtime_minutes(
        payload.task_type,
        payload.duration_seconds,
        payload.resolution,
        payload.output_count,
    )
    ranked = score_offers(
        offers,
        payload.strategy,
        estimated_runtime_minutes=runtime_minutes,
    )
    if not ranked:
        raise ValueError("No offers available for quoting")

    risk_note = {
        TaskStrategy.CHEAP.value: "成本优先，首轮可能命中低价但低稳定供给。",
        TaskStrategy.STABLE.value: "稳定优先，会偏向高可靠和高成功率供给。",
        TaskStrategy.URGENT.value: "加急优先，会偏向启动速度和成功率更高的供给。",
    }.get(payload.strategy, "默认按稳定交付策略报价。")

    recommended = ProviderOfferRead(**ranked[0])
    candidates = [ProviderOfferRead(**item) for item in ranked]
    return QuoteResponse(
        recommended_offer=recommended,
        candidate_offers=candidates,
        estimated_price=recommended.estimated_price or 0,
        estimated_runtime_minutes=runtime_minutes,
        risk_note=risk_note,
    )
