"""axis-agent-registry — canonical model registry for the axis ecosystem.

Public API:
    CATALOG                          dict[str, ModelSpec]
    DEFAULT_ASSIGNMENTS              dict[str, str]
    ModelSpec                        frozen dataclass
    OVERRIDE_PREFIXES                tuple[str, ...] in priority order
    get_model_for(role, env_overrides=None) -> str
    get_spec(model_id) -> ModelSpec | None
    all_assignments() -> dict[str, dict]
    set_hybrid_crm_override_lookup(callable | None) -> None

Resolution order: explicit kwarg > AXIS_MODEL_OVERRIDE_<ROLE> >
INVIDIA_MODEL_OVERRIDE_<ROLE> > hybrid-crm UI callback > DEFAULT_ASSIGNMENTS.

Origin: extracted 2026-06-04 from /Users/eluru/invidia-chat-api/lib/model_registry.py
(see EXPLORATION-2026-05-27 §7 Fase A and 01-MONOREPO-SKELETON-PLAN.md).
"""
from __future__ import annotations

from .assignments import DEFAULT_ASSIGNMENTS
from .catalog import CATALOG, ModelSpec
from .registry import (
    OVERRIDE_PREFIXES,
    all_assignments,
    get_model_for,
    get_spec,
    set_hybrid_crm_override_lookup,
)

__all__ = [
    "CATALOG",
    "DEFAULT_ASSIGNMENTS",
    "ModelSpec",
    "OVERRIDE_PREFIXES",
    "all_assignments",
    "get_model_for",
    "get_spec",
    "set_hybrid_crm_override_lookup",
]

__version__ = "0.1.0"
