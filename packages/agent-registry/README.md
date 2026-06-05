# axis-agent-registry

Canonical model registry for the axis ecosystem. Extracted from `invidia-chat-api/lib/model_registry.py` so every host (Sophie, axis-cc, hybrid-crm, axis-runtime, future agents) imports the same source of truth.

## Public API

```python
from axis_agent_registry import (
    CATALOG,                          # dict[str, ModelSpec] — every allowed model
    DEFAULT_ASSIGNMENTS,              # dict[str, str] — role → model id
    ModelSpec,                        # frozen dataclass
    OVERRIDE_PREFIXES,                # ("AXIS_MODEL_OVERRIDE_", "INVIDIA_MODEL_OVERRIDE_")
    get_model_for,                    # (role, env_overrides=None) -> str
    get_spec,                         # (model_id) -> ModelSpec | None
    all_assignments,                  # () -> dict[str, dict]
    set_hybrid_crm_override_lookup,   # (callable | None) -> None
)
```

## Resolution chain

`get_model_for(role)` resolves in this order; first hit wins:

1. Explicit `env_overrides` kwarg (test injection).
2. `AXIS_MODEL_OVERRIDE_<ROLE>` env var (new canonical prefix).
3. `INVIDIA_MODEL_OVERRIDE_<ROLE>` env var (legacy prefix — preserved for Sophie).
4. Hybrid-CRM UI override via `set_hybrid_crm_override_lookup` callback (optional, host-injected).
5. `DEFAULT_ASSIGNMENTS[role]` static fallback.

Unknown override model ids log a warning and fall through. Unknown roles raise `ValueError`. Roles mapped to unregistered models raise `ValueError`.

## Why two env prefixes?

`INVIDIA_MODEL_OVERRIDE_*` is the legacy prefix in production today (Sophie's Railway env). `AXIS_MODEL_OVERRIDE_*` is the new canonical prefix shared across the ecosystem. Both are honored simultaneously, with AXIS taking priority. Sophie keeps working with zero env-var migration; new tenants/agents adopt AXIS_* directly.

## Install (dev / local path)

```bash
pip install -e /Users/eluru/axis-agent-mesh/packages/agent-registry
```

## Tests

```bash
python3.11 -m pytest python/tests -v
```

12 tests cover catalog parity, assignment parity, default resolution, both env prefixes, prefix precedence, unknown overrides, unknown roles, the hybrid-crm callback path, and the public import surface.
