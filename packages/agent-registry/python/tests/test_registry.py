"""Tests for axis_agent_registry.

12 tests cover catalog parity vs the originating Sophie module, default
assignment parity, the dual-prefix env override layer, the hybrid-crm
callback seam, and the public import surface.

The 'originating Sophie module' for parity tests is loaded by absolute path
so the test does not require invidia-chat-api to be pip-installed alongside
this package. If the file is moved or unavailable, parity tests skip with
a clear message rather than fail spuriously.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

from axis_agent_registry import (
    CATALOG,
    DEFAULT_ASSIGNMENTS,
    ModelSpec,
    OVERRIDE_PREFIXES,
    all_assignments,
    get_model_for,
    get_spec,
    set_hybrid_crm_override_lookup,
)
from axis_agent_registry import registry as registry_module


SOPHIE_MODEL_REGISTRY = Path("/Users/eluru/invidia-chat-api/lib/model_registry.py")


def _load_sophie_module():
    """Load the originating Sophie module by absolute path.

    Returns the module or None if the file is unavailable (in which case
    parity tests skip rather than fail).
    """
    if not SOPHIE_MODEL_REGISTRY.exists():
        return None
    spec = importlib.util.spec_from_file_location(
        "_sophie_model_registry_legacy", SOPHIE_MODEL_REGISTRY
    )
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    # Guard: Sophie's module lazy-imports inbox.workers.hybrid_crm_consumer
    # but only inside get_model_for, not at import time, so loading the
    # module here is safe even without Sophie's full sys.path.
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cannot import Sophie reference module: {exc!r}")
    return mod


@pytest.fixture(autouse=True)
def _clear_overrides(monkeypatch):
    """Strip every AXIS_/INVIDIA_ override env var before each test.

    Ensures tests are order-independent and never inherit operator-level
    overrides from the dev environment running pytest.
    """
    for key in list(os.environ.keys()):
        for prefix in OVERRIDE_PREFIXES:
            if key.startswith(prefix):
                monkeypatch.delenv(key, raising=False)
                break
    # Also clear the hybrid-crm callback between tests so test 10 doesn't
    # leak into the others.
    yield
    set_hybrid_crm_override_lookup(None)


# ---------------------------------------------------------------------------
# Test 1 — Catalog parity vs originating Sophie module
# ---------------------------------------------------------------------------

def test_catalog_parity_with_sophie():
    sophie = _load_sophie_module()
    if sophie is None:
        pytest.skip(f"Sophie reference module not at {SOPHIE_MODEL_REGISTRY}")
    assert set(CATALOG.keys()) == set(sophie.CATALOG.keys()), (
        "CATALOG keys diverged from Sophie's source-of-truth"
    )
    for mid, spec in CATALOG.items():
        ref = sophie.CATALOG[mid]
        assert spec.id == ref.id, f"{mid}: id"
        assert spec.in_price_per_m == ref.in_price_per_m, f"{mid}: in_price_per_m"
        assert spec.out_price_per_m == ref.out_price_per_m, f"{mid}: out_price_per_m"
        assert spec.ctx_tokens == ref.ctx_tokens, f"{mid}: ctx_tokens"
        assert spec.supports_tools == ref.supports_tools, f"{mid}: supports_tools"
        assert spec.released == ref.released, f"{mid}: released"
        assert spec.family == ref.family, f"{mid}: family"
        assert spec.leak_risk == ref.leak_risk, f"{mid}: leak_risk"
        # notes string comparison is best-effort — minor punctuation
        # differences are tolerated but the prefix must match the original
        # intent. We compare the first 40 chars.
        assert spec.notes[:40] == ref.notes[:40], f"{mid}: notes prefix"


# ---------------------------------------------------------------------------
# Test 2 — Assignments parity
# ---------------------------------------------------------------------------

def test_assignments_parity_with_sophie():
    sophie = _load_sophie_module()
    if sophie is None:
        pytest.skip(f"Sophie reference module not at {SOPHIE_MODEL_REGISTRY}")
    assert DEFAULT_ASSIGNMENTS == sophie.DEFAULT_ASSIGNMENTS, (
        "DEFAULT_ASSIGNMENTS diverged from Sophie's source-of-truth"
    )


# ---------------------------------------------------------------------------
# Test 3 — Default resolution
# ---------------------------------------------------------------------------

def test_get_model_for_default():
    assert get_model_for("agentic_master") == "openai/gpt-5.4-mini"


# ---------------------------------------------------------------------------
# Test 4 — Unknown role raises
# ---------------------------------------------------------------------------

def test_unknown_role_raises():
    with pytest.raises(ValueError, match="unknown role"):
        get_model_for("not_a_real_role")


# ---------------------------------------------------------------------------
# Test 5 — Legacy INVIDIA_ env override
# ---------------------------------------------------------------------------

def test_legacy_invidia_env_override(monkeypatch):
    monkeypatch.setenv("INVIDIA_MODEL_OVERRIDE_AGENTIC_MASTER", "moonshotai/kimi-k2.6")
    assert get_model_for("agentic_master") == "moonshotai/kimi-k2.6"


# ---------------------------------------------------------------------------
# Test 6 — New canonical AXIS_ env override
# ---------------------------------------------------------------------------

def test_new_canonical_axis_env_override(monkeypatch):
    monkeypatch.setenv("AXIS_MODEL_OVERRIDE_AGENTIC_MASTER", "deepseek/deepseek-v4-pro")
    assert get_model_for("agentic_master") == "deepseek/deepseek-v4-pro"


# ---------------------------------------------------------------------------
# Test 7 — Prefix precedence: AXIS_ wins over INVIDIA_
# ---------------------------------------------------------------------------

def test_axis_prefix_wins_over_invidia(monkeypatch):
    monkeypatch.setenv("INVIDIA_MODEL_OVERRIDE_AGENTIC_MASTER", "moonshotai/kimi-k2.6")
    monkeypatch.setenv("AXIS_MODEL_OVERRIDE_AGENTIC_MASTER", "deepseek/deepseek-v4-pro")
    assert get_model_for("agentic_master") == "deepseek/deepseek-v4-pro"


# ---------------------------------------------------------------------------
# Test 8 — Unknown override id warns and falls through
# ---------------------------------------------------------------------------

def test_unknown_override_id_falls_through(monkeypatch, caplog):
    monkeypatch.setenv("INVIDIA_MODEL_OVERRIDE_AGENTIC_MASTER", "nope/not-a-model")
    with caplog.at_level("WARNING", logger="axis_agent_registry.registry"):
        result = get_model_for("agentic_master")
    assert result == "openai/gpt-5.4-mini"  # falls through to default
    assert any("NOT in catalog" in rec.message for rec in caplog.records), (
        "Expected a NOT in catalog warning to be emitted"
    )


# ---------------------------------------------------------------------------
# Test 9 — Explicit env_overrides kwarg
# ---------------------------------------------------------------------------

def test_explicit_env_overrides_kwarg(monkeypatch):
    # Even with OS-level AXIS override set, explicit kwarg must win.
    monkeypatch.setenv("AXIS_MODEL_OVERRIDE_AGENTIC_MASTER", "deepseek/deepseek-v4-pro")
    result = get_model_for(
        "agentic_master",
        env_overrides={"AGENTIC_MASTER": "openai/gpt-5.4-nano"},
    )
    assert result == "openai/gpt-5.4-nano"


# ---------------------------------------------------------------------------
# Test 10 — hybrid-crm callback path
# ---------------------------------------------------------------------------

def test_hybrid_crm_callback_path():
    # Callback returning None -> fall through.
    set_hybrid_crm_override_lookup(lambda role: None)
    assert get_model_for("agentic_master") == "openai/gpt-5.4-mini"

    # Callback returning unknown model -> warn and fall through.
    set_hybrid_crm_override_lookup(lambda role: "nope/not-a-model")
    assert get_model_for("agentic_master") == "openai/gpt-5.4-mini"

    # Callback returning valid CATALOG id -> use it.
    set_hybrid_crm_override_lookup(lambda role: "moonshotai/kimi-k2.6")
    assert get_model_for("agentic_master") == "moonshotai/kimi-k2.6"

    # Callback raising must not break get_model_for (defensive).
    def _broken(_role: str) -> str:
        raise RuntimeError("simulated callback failure")
    set_hybrid_crm_override_lookup(_broken)
    assert get_model_for("agentic_master") == "openai/gpt-5.4-mini"


# ---------------------------------------------------------------------------
# Test 11 — Public import surface
# ---------------------------------------------------------------------------

def test_public_import_surface():
    # Re-imports inside the test body confirm the package-level names
    # exposed by __init__.py are exactly what the contract promises.
    from axis_agent_registry import (  # noqa: F401
        CATALOG,
        DEFAULT_ASSIGNMENTS,
        ModelSpec,
        OVERRIDE_PREFIXES,
        all_assignments,
        get_model_for,
        get_spec,
        set_hybrid_crm_override_lookup,
    )
    assert callable(get_model_for)
    assert callable(get_spec)
    assert callable(all_assignments)
    assert callable(set_hybrid_crm_override_lookup)
    assert isinstance(CATALOG, dict)
    assert isinstance(DEFAULT_ASSIGNMENTS, dict)
    assert isinstance(OVERRIDE_PREFIXES, tuple)
    # ModelSpec is a frozen dataclass — instances should reject mutation.
    sample = next(iter(CATALOG.values()))
    assert isinstance(sample, ModelSpec)
    with pytest.raises(Exception):
        sample.id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test 12 — OVERRIDE_PREFIXES constant + priority order
# ---------------------------------------------------------------------------

def test_override_prefixes_constant_and_order():
    assert OVERRIDE_PREFIXES == ("AXIS_MODEL_OVERRIDE_", "INVIDIA_MODEL_OVERRIDE_")
    # First entry MUST be the canonical AXIS prefix — Plan 02 TS twin
    # depends on this ordering to mirror priority.
    assert OVERRIDE_PREFIXES[0] == "AXIS_MODEL_OVERRIDE_"
