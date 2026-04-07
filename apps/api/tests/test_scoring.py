from __future__ import annotations

from decimal import Decimal

from apps.api.app.models import ProviderOfferSnapshot
from apps.api.app.services.providers import score_offers


def test_scoring_prefers_lower_price_for_cheap_strategy():
    offers = [
        ProviderOfferSnapshot(
            provider="cheap-low-reliability",
            gpu_type="RTX 4090",
            region="us",
            price_per_hour=Decimal("0.20"),
            reliability_score=Decimal("0.60"),
            startup_score=Decimal("0.70"),
            success_rate=Decimal("0.65"),
        ),
        ProviderOfferSnapshot(
            provider="expensive-high-reliability",
            gpu_type="RTX 4090",
            region="us",
            price_per_hour=Decimal("0.80"),
            reliability_score=Decimal("0.95"),
            startup_score=Decimal("0.90"),
            success_rate=Decimal("0.96"),
        ),
    ]
    ranked = score_offers(offers, "cheap", estimated_runtime_minutes=12)
    assert ranked[0]["provider"] == "cheap-low-reliability"


def test_scoring_prefers_stability_for_stable_strategy():
    offers = [
        ProviderOfferSnapshot(
            provider="cheap",
            gpu_type="RTX 4090",
            region="us",
            price_per_hour=Decimal("0.20"),
            reliability_score=Decimal("0.55"),
            startup_score=Decimal("0.60"),
            success_rate=Decimal("0.50"),
        ),
        ProviderOfferSnapshot(
            provider="stable",
            gpu_type="RTX 4090",
            region="us",
            price_per_hour=Decimal("0.60"),
            reliability_score=Decimal("0.95"),
            startup_score=Decimal("0.88"),
            success_rate=Decimal("0.97"),
        ),
    ]
    ranked = score_offers(offers, "stable", estimated_runtime_minutes=12)
    assert ranked[0]["provider"] == "stable"
