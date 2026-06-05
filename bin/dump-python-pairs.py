#!/usr/bin/env python3
"""Dump the Python axis_agent_registry source-of-truth as JSON.

Used by bin/sync-twin.ts to regenerate the TS twin's catalog.ts +
assignments.ts files AND to compute the 10-pair Python/TS parity
snapshot fixture (typescript/tests/snapshot-fixtures/python-pairs.json).

Flags:
    --catalog-only     emit CATALOG as a JSON object {model_id: ModelSpec...}
    --assignments-only emit DEFAULT_ASSIGNMENTS as a JSON object {role: model_id}
    --pairs            emit the 10 representative (role, env_overrides) pairs
                       with the Python-computed expected_model_id
    (no flag)          emit a single JSON envelope:
                       {"catalog": ..., "assignments": ..., "pairs": [...]}

The 10 pairs are constructed deterministically in this script so the
fixture is reproducible across machines:
    - 5 default-path pairs (no override) across 5 distinct roles:
        agentic_master, critic, intent_analyzer, confirm_problem, greet
    - 2 INVIDIA_MODEL_OVERRIDE_* pairs (legacy prefix):
        image_analyzer       -> openai/gpt-5.4-nano
        search_help_center   -> deepseek/deepseek-v4-flash
    - 2 AXIS_MODEL_OVERRIDE_* pairs (canonical prefix):
        acknowledge_escalation -> moonshotai/kimi-k2.6
        shift_report           -> qwen/qwen3.6-flash
    - 1 conflict pair (BOTH set, AXIS wins):
        agentic_master  AXIS=deepseek-v4-pro  INVIDIA=kimi-k2.6 -> deepseek-v4-pro

NOTE: the script appends the local Python package path to sys.path so it
runs without a pip install -e step. This keeps CI lean.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from pathlib import Path

# Ensure the local package is importable without pip install -e .
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PKG_PYTHON = _REPO_ROOT / "packages" / "agent-registry" / "python"
if str(_PKG_PYTHON) not in sys.path:
    sys.path.insert(0, str(_PKG_PYTHON))

import axis_agent_registry  # noqa: E402
from axis_agent_registry import CATALOG, DEFAULT_ASSIGNMENTS, get_model_for  # noqa: E402


# ---------------------------------------------------------------------------
# Pair definitions — single source of truth for the 10-pair snapshot fixture.
# Roles MUST come from DEFAULT_ASSIGNMENTS. Override model ids MUST be in
# CATALOG (otherwise the resolver warns + falls back to default — the test
# would still pass since expected_model_id is computed from Python live).
# ---------------------------------------------------------------------------

# 5 default-path pairs — distinct roles, no override.
_DEFAULT_PAIR_ROLES = [
    "agentic_master",
    "critic",
    "intent_analyzer",
    "confirm_problem",
    "greet",
]

# 2 INVIDIA_MODEL_OVERRIDE_* (legacy prefix) pairs.
_INVIDIA_OVERRIDE_PAIRS = [
    ("image_analyzer", "openai/gpt-5.4-nano"),
    ("search_help_center", "deepseek/deepseek-v4-flash"),
]

# 2 AXIS_MODEL_OVERRIDE_* (canonical prefix) pairs.
_AXIS_OVERRIDE_PAIRS = [
    ("acknowledge_escalation", "moonshotai/kimi-k2.6"),
    ("shift_report", "qwen/qwen3.6-flash"),
]

# 1 conflict pair — BOTH prefixes set, AXIS wins.
_CONFLICT_PAIR = {
    "role": "agentic_master",
    "axis_value": "deepseek/deepseek-v4-pro",
    "invidia_value": "moonshotai/kimi-k2.6",
}


def _dump_catalog() -> dict[str, dict]:
    """CATALOG as plain JSON dict — preserves Python field names (snake_case)."""
    return {mid: dataclasses.asdict(spec) for mid, spec in CATALOG.items()}


def _dump_assignments() -> dict[str, str]:
    """DEFAULT_ASSIGNMENTS as plain JSON dict."""
    return dict(DEFAULT_ASSIGNMENTS)


def _build_pair(
    role: str,
    env_overrides: dict[str, str],
) -> dict:
    """Construct one snapshot pair, computing expected_model_id from Python.

    env_overrides is in the SHAPE the TS twin consumes:
        full env-var name -> model_id
    e.g. {"AXIS_MODEL_OVERRIDE_AGENTIC_MASTER": "deepseek/deepseek-v4-pro"}

    To call get_model_for(role, env_overrides=...) we need the UPPERCASE-role
    -> model_id map (the explicit kwarg form). We extract it from the
    full env var names by stripping the known prefixes and honoring
    OVERRIDE_PREFIXES priority order so AXIS wins on conflict.
    """
    explicit: dict[str, str] = {}
    role_upper = role.upper()
    # Iterate in OVERRIDE_PREFIXES priority order so AXIS wins
    for prefix in axis_agent_registry.OVERRIDE_PREFIXES:
        env_key = f"{prefix}{role_upper}"
        if env_key in env_overrides and role_upper not in explicit:
            explicit[role_upper] = env_overrides[env_key]
    expected = get_model_for(role, env_overrides=explicit or None)
    return {
        "role": role,
        "env_overrides": env_overrides,
        "expected_model_id": expected,
    }


def _build_pairs() -> list[dict]:
    """Build the 10 representative pairs deterministically."""
    pairs: list[dict] = []

    # 5 default-path pairs
    for role in _DEFAULT_PAIR_ROLES:
        pairs.append(_build_pair(role, env_overrides={}))

    # 2 INVIDIA override pairs
    for role, model_id in _INVIDIA_OVERRIDE_PAIRS:
        env_key = f"INVIDIA_MODEL_OVERRIDE_{role.upper()}"
        pairs.append(_build_pair(role, env_overrides={env_key: model_id}))

    # 2 AXIS override pairs
    for role, model_id in _AXIS_OVERRIDE_PAIRS:
        env_key = f"AXIS_MODEL_OVERRIDE_{role.upper()}"
        pairs.append(_build_pair(role, env_overrides={env_key: model_id}))

    # 1 conflict pair (AXIS wins)
    role = _CONFLICT_PAIR["role"]
    pairs.append(
        _build_pair(
            role,
            env_overrides={
                f"AXIS_MODEL_OVERRIDE_{role.upper()}": _CONFLICT_PAIR["axis_value"],
                f"INVIDIA_MODEL_OVERRIDE_{role.upper()}": _CONFLICT_PAIR["invidia_value"],
            },
        )
    )

    assert len(pairs) == 10, f"expected 10 pairs, got {len(pairs)}"
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-only", action="store_true")
    parser.add_argument("--assignments-only", action="store_true")
    parser.add_argument("--pairs", action="store_true")
    args = parser.parse_args()

    # IMPORTANT: clear env to ensure pair resolution uses explicit kwargs only.
    # Otherwise a developer's local AXIS_MODEL_OVERRIDE_* would leak in.
    for key in list(os.environ.keys()):
        if key.startswith(("AXIS_MODEL_OVERRIDE_", "INVIDIA_MODEL_OVERRIDE_")):
            del os.environ[key]

    if args.catalog_only:
        json.dump(_dump_catalog(), sys.stdout, indent=2, sort_keys=True)
    elif args.assignments_only:
        json.dump(_dump_assignments(), sys.stdout, indent=2, sort_keys=True)
    elif args.pairs:
        json.dump(_build_pairs(), sys.stdout, indent=2)
    else:
        envelope = {
            "catalog": _dump_catalog(),
            "assignments": _dump_assignments(),
            "pairs": _build_pairs(),
        }
        json.dump(envelope, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
