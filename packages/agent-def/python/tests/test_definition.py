"""Tests for axis_agent_def — the pydantic v2 AgentDefinition mirror.

Coverage:
  1. A minimal-but-complete (all required fields) AgentDefinition validates.
  2. The version gate rejects version=2 with a ValueError.
  3. A missing required field fails validation.
  4. extra="forbid" rejects an unknown field.
Plus: JSON-string input path, version gate runs BEFORE pydantic, and the
discriminated unions (KnowledgeSource, AgentTrigger) resolve to the right
concrete subclass.
"""
from __future__ import annotations

import copy
import json

import pytest

from axis_agent_def import (
    SCHEMA_VERSION,
    AgentDefinition,
    AxisMemoryKnowledgeSource,
    ScheduleTrigger,
    load_agent_definition,
)


def _minimal_definition() -> dict:
    """A valid AgentDefinition with every required field populated."""
    return {
        "version": SCHEMA_VERSION,
        "identity": {
            "id": "00000000-0000-0000-0000-000000000001",
            "fqid": "maicol/personal/maik",
            "name": "MAIK",
            "tenant": {"customer": "maicol", "org": "personal"},
            "version": 1,
        },
        "goal": {
            "objective": "Keep Maicol's command center coherent.",
            "success_criteria": ["No dropped captures", "All tasks routed"],
        },
        "context_scope": {
            "memory_namespace": "customer/maicol/org/personal/agent/maik",
            "knowledge_sources": [
                {"type": "axis-memory", "scope": "maicol"},
            ],
        },
        "skills": [
            {"name": "quick-capture", "version": "1.0.0", "enabled": True},
        ],
        "model_routing": {
            "default": "agentic_master",
            "fallback_chain": ["openai/gpt-5.4-mini"],
        },
        "guardrails": [
            {"id": "rate-limit", "severity": "block", "config": {"rpm": 60}},
        ],
        "kpis": [
            {
                "name": "capture_routing_pct",
                "source": "postgres",
                "direction": "higher_better",
            },
        ],
        "runtime": {
            "deployment_target": "axis-runtime",
            "trigger": [{"type": "manual"}],
            "governance": {"confirmation_gate": "disabled"},
            "observability": {"langfuse_project": "axis-cc", "tags": ["maik"]},
        },
    }


# ---------------------------------------------------------------------------
# Test 1 — minimal valid definition is accepted
# ---------------------------------------------------------------------------


def test_minimal_valid_definition_accepted():
    data = _minimal_definition()
    model = load_agent_definition(data)
    assert isinstance(model, AgentDefinition)
    assert model.version == SCHEMA_VERSION
    assert model.identity.fqid == "maicol/personal/maik"
    # identity.version is the AGENT version, distinct from the format version.
    assert model.identity.version == 1


def test_minimal_valid_definition_from_json_string():
    model = load_agent_definition(json.dumps(_minimal_definition()))
    assert isinstance(model, AgentDefinition)
    assert model.runtime.deployment_target == "axis-runtime"


# ---------------------------------------------------------------------------
# Test 2 — version gate rejects an unsupported format version
# ---------------------------------------------------------------------------


def test_version_gate_rejects_version_2():
    data = _minimal_definition()
    data["version"] = 2
    with pytest.raises(ValueError, match="unsupported AgentDefinition version 2"):
        load_agent_definition(data)


def test_version_gate_runs_before_pydantic():
    # Wrong version AND a structurally broken body: the version error must
    # win, proving the gate runs before model_validate.
    data = {"version": 99, "identity": "garbage"}
    with pytest.raises(ValueError, match="unsupported AgentDefinition version 99"):
        load_agent_definition(data)


# ---------------------------------------------------------------------------
# Test 3 — missing a required field fails
# ---------------------------------------------------------------------------


def test_missing_required_field_fails():
    data = _minimal_definition()
    del data["goal"]  # goal is required
    with pytest.raises(Exception):
        load_agent_definition(data)


def test_missing_nested_required_field_fails():
    data = _minimal_definition()
    del data["identity"]["fqid"]  # identity.fqid is required
    with pytest.raises(Exception):
        load_agent_definition(data)


# ---------------------------------------------------------------------------
# Test 4 — extra="forbid" rejects an unknown field
# ---------------------------------------------------------------------------


def test_unknown_top_level_field_rejected():
    data = _minimal_definition()
    data["surprise"] = "not in the contract"
    with pytest.raises(Exception):
        load_agent_definition(data)


def test_unknown_nested_field_rejected():
    data = _minimal_definition()
    data["identity"]["surprise"] = "nope"
    with pytest.raises(Exception):
        load_agent_definition(data)


# ---------------------------------------------------------------------------
# Discriminated-union sanity — type tag resolves to the right subclass
# ---------------------------------------------------------------------------


def test_knowledge_source_discriminated_union():
    model = load_agent_definition(_minimal_definition())
    ks = model.context_scope.knowledge_sources[0]
    assert isinstance(ks, AxisMemoryKnowledgeSource)
    assert ks.type == "axis-memory"
    assert ks.scope == "maicol"


def test_trigger_discriminated_union_schedule():
    data = _minimal_definition()
    data["runtime"]["trigger"] = [{"type": "schedule", "cron": "0 7 * * *"}]
    model = load_agent_definition(data)
    trig = model.runtime.trigger[0]
    assert isinstance(trig, ScheduleTrigger)
    assert trig.cron == "0 7 * * *"


def test_wrong_field_for_trigger_type_rejected():
    # A schedule trigger carrying a webhook's `route` must fail (extra=forbid
    # + discriminator).
    data = _minimal_definition()
    data["runtime"]["trigger"] = [{"type": "schedule", "route": "/hook"}]
    with pytest.raises(Exception):
        load_agent_definition(data)


def test_deepcopy_isolation_between_tests():
    # Defensive: confirm the helper returns a fresh dict each call so mutating
    # tests don't leak into one another.
    a = _minimal_definition()
    b = _minimal_definition()
    a["identity"]["name"] = "MUTATED"
    assert b["identity"]["name"] == "MAIK"
    assert a is not b
    _ = copy.deepcopy(a)  # no-op, asserts deepcopy-able
