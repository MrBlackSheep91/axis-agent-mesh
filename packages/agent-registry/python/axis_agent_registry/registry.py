"""Public resolution API for axis-agent-registry.

Resolution order for get_model_for(role, env_overrides=None):

  1. Explicit env_overrides kwarg (test injection / sync-twin snapshot).
     Map key is the UPPERCASE role; value is the model id.
  2. AXIS_MODEL_OVERRIDE_<ROLE_UPPER>  (new canonical env prefix).
  3. INVIDIA_MODEL_OVERRIDE_<ROLE_UPPER>  (legacy prefix, preserved for Sophie).
  4. Hybrid-CRM UI override via set_hybrid_crm_override_lookup(callable).
     Optional; host injects a callable returning a model id or None.
  5. DEFAULT_ASSIGNMENTS static fallback (catalog.py / assignments.py).

Unknown override model ids (any layer 1-4) trigger logger.warning and fall
through. Unknown roles raise ValueError. A role mapped to a model not in
CATALOG raises ValueError.

Why TWO env prefixes:
  - INVIDIA_MODEL_OVERRIDE_* already exists in Sophie's Railway env. Renaming
    it forces a redeploy + ops handoff with zero benefit during Wave A.
  - AXIS_MODEL_OVERRIDE_* is the new canonical prefix for the rest of the
    ecosystem (axis-cc, hybrid-crm, future tenants). Both are honored
    simultaneously, AXIS wins on collisions.

The hybrid-crm callback is a dependency-injection seam — the registry does
NOT import from inbox.workers.hybrid_crm_consumer. The Sophie shim (Task 3)
wires the callback via set_hybrid_crm_override_lookup at module import time.
"""
from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from .assignments import DEFAULT_ASSIGNMENTS
from .catalog import CATALOG, ModelSpec

logger = logging.getLogger(__name__)


# Priority order — first prefix wins on collision.
OVERRIDE_PREFIXES: tuple[str, ...] = (
    "AXIS_MODEL_OVERRIDE_",
    "INVIDIA_MODEL_OVERRIDE_",
)


# ---------------------------------------------------------------------------
# Hybrid-CRM override injection seam
# ---------------------------------------------------------------------------

_hybrid_crm_override_lookup: Optional[Callable[[str], Optional[str]]] = None


def set_hybrid_crm_override_lookup(
    fn: Optional[Callable[[str], Optional[str]]],
) -> None:
    """Register (or clear, with None) a callback that returns the
    hybrid-crm UI override for a role. Called once at host import time
    (Sophie's shim does this for backwards compatibility).

    Contract:
      - fn(role_lower) -> model_id (str) or None
      - fn MUST NOT raise; any exception is caught and treated as None.
      - fn is consulted only when no env override matched.
    """
    global _hybrid_crm_override_lookup
    _hybrid_crm_override_lookup = fn


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

def _resolve_explicit(
    role_upper: str,
    env_overrides: Optional[dict[str, str]],
) -> Optional[str]:
    """Layer 1 — explicit kwarg map. Test/sync-twin injection."""
    if not env_overrides:
        return None
    candidate = env_overrides.get(role_upper)
    if not candidate:
        return None
    if candidate not in CATALOG:
        logger.warning(
            "axis_agent_registry: explicit env_overrides[%s]=%s NOT in catalog "
            "— ignoring and falling back",
            role_upper, candidate,
        )
        return None
    return candidate


def _resolve_env_prefix(role_upper: str) -> Optional[str]:
    """Layer 2 + 3 — iterate OVERRIDE_PREFIXES in priority order."""
    for prefix in OVERRIDE_PREFIXES:
        env_key = f"{prefix}{role_upper}"
        value = (os.getenv(env_key) or "").strip()
        if not value:
            continue
        if value not in CATALOG:
            logger.warning(
                "axis_agent_registry: env override %s=%s NOT in catalog "
                "— ignoring and falling back",
                env_key, value,
            )
            continue
        return value
    return None


def _resolve_hybrid_crm(role_lower: str) -> Optional[str]:
    """Layer 4 — host-injected hybrid-crm UI override (optional)."""
    if _hybrid_crm_override_lookup is None:
        return None
    try:
        candidate = _hybrid_crm_override_lookup(role_lower)
    except Exception as exc:  # noqa: BLE001 — defensive, callback is host code
        logger.debug(
            "axis_agent_registry: hybrid-crm lookup raised %s for role=%s "
            "— falling through to defaults",
            type(exc).__name__, role_lower,
        )
        return None
    if not candidate:
        return None
    if candidate not in CATALOG:
        logger.warning(
            "axis_agent_registry: hybrid-crm UI override role=%s model=%s "
            "NOT in catalog — ignoring and falling back",
            role_lower, candidate,
        )
        return None
    logger.info(
        "axis_agent_registry: role=%s using hybrid-crm UI override model=%s",
        role_lower, candidate,
    )
    return candidate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_model_for(
    role: str,
    env_overrides: Optional[dict[str, str]] = None,
) -> str:
    """Return the model id assigned to a role, applying the override chain.

    Args:
        role: role name (case-insensitive, normalised to lowercase).
        env_overrides: optional explicit map taking precedence over OS env.
            Keys are UPPERCASE role names; values are model ids that must
            exist in CATALOG. Unknown ids warn and fall through.

    Raises:
        ValueError: if role is not in DEFAULT_ASSIGNMENTS, or if the
            assigned model is not registered in CATALOG.
    """
    role_lower = role.lower()
    role_upper = role_lower.upper()

    explicit = _resolve_explicit(role_upper, env_overrides)
    if explicit:
        return explicit

    env_value = _resolve_env_prefix(role_upper)
    if env_value:
        return env_value

    ui_value = _resolve_hybrid_crm(role_lower)
    if ui_value:
        return ui_value

    model = DEFAULT_ASSIGNMENTS.get(role_lower)
    if not model:
        raise ValueError(
            f"axis_agent_registry: unknown role={role!r}. "
            f"Add it to DEFAULT_ASSIGNMENTS first."
        )
    if model not in CATALOG:
        raise ValueError(
            f"axis_agent_registry: role={role!r} assigned to unregistered "
            f"model={model!r}. Add it to CATALOG first."
        )
    return model


def get_spec(model_id: str) -> Optional[ModelSpec]:
    """Return the ModelSpec for a registered model id, or None if unknown."""
    return CATALOG.get(model_id)


def all_assignments() -> dict[str, dict]:
    """Diagnostic dump — every role's resolved model + spec snapshot.

    The shape matches the legacy invidia-chat-api lib.model_registry.all_assignments()
    output exactly so existing admin endpoints / Sophie diagnostics keep working
    after the shim conversion (Task 3).
    """
    out: dict[str, dict] = {}
    for role in DEFAULT_ASSIGNMENTS:
        mid = get_model_for(role)
        spec = CATALOG.get(mid)
        # from_override is True if ANY env prefix supplied a value for this
        # role — mirrors the original boolean exactly.
        role_upper = role.upper()
        from_override = any(
            os.getenv(f"{prefix}{role_upper}") for prefix in OVERRIDE_PREFIXES
        )
        out[role] = {
            "model_id": mid,
            "from_override": bool(from_override),
            "in_price_per_m": spec.in_price_per_m if spec else None,
            "out_price_per_m": spec.out_price_per_m if spec else None,
            "supports_tools": spec.supports_tools if spec else None,
            "leak_risk": spec.leak_risk if spec else None,
            "released": spec.released if spec else None,
        }
    return out
