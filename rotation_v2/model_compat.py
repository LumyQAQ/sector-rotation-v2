from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from .theme_taxonomy import enrich_theme_structure


def normalize_rotation_model(model: Any) -> Any:
    if hasattr(model, "family_frame"):
        return model

    sector_frame, family_frame = enrich_theme_structure(model.sector_frame)
    summary = dict(getattr(model, "summary", {}))
    if not family_frame.empty:
        summary.setdefault("最强主线", str(family_frame.iloc[0]["主线家族"]))
        summary.setdefault("Top3主线共振", round(float(family_frame.head(3)["家族共振度"].mean()), 1))
        summary.setdefault("主线家族数", int(len(family_frame)))

    return SimpleNamespace(
        as_of=model.as_of,
        sector_frame=sector_frame,
        family_frame=family_frame,
        trail_frame=model.trail_frame,
        leaders_frame=model.leaders_frame,
        market_state=model.market_state,
        summary=summary,
    )
