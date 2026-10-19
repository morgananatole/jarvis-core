"""AI Hub offline planning only. No external calls, credentials or billing."""
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Iterable
import os

@dataclass(frozen=True)
class Provider:
    name: str
    quality: int
    cost_per_1k: Decimal
    local: bool = False
    available: bool = True

def enabled() -> bool:
    return os.getenv("JARVIS_AI_HUB_ENABLED", "false").lower() == "true"

def select_provider(providers: Iterable[Provider], minimum_quality: int = 80,
                    estimated_tokens: int = 1000, budget: Decimal = Decimal("0")) -> dict:
    """Rank viable providers by estimated cost; never perform a call."""
    if not enabled():
        return {"status": "disabled", "selected": None, "estimated_cost": "0", "reason": "feature_flag_off"}
    if estimated_tokens < 0 or not 0 <= minimum_quality <= 100 or budget < 0:
        raise ValueError("Invalid planning constraints")
    choices = []
    for p in providers:
        if p.available and p.quality >= minimum_quality and p.cost_per_1k >= 0:
            cost = p.cost_per_1k * Decimal(estimated_tokens) / Decimal(1000)
            if cost <= budget:
                choices.append((cost, -p.quality, p.name, p))
    if not choices:
        return {"status": "requires_approval_or_alternative", "selected": None,
                "estimated_cost": "0", "reason": "no_quality_qualified_provider_within_budget"}
    cost, _, _, provider = min(choices)
    return {"status": "planned_only", "selected": provider.name,
            "estimated_cost": str(cost), "reason": "lowest_cost_meeting_quality_and_budget",
            "local": provider.local}
