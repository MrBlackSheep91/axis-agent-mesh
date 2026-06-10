"""Tests for axis_skill_registry — the pydantic v2 SkillManifest mirror.

Coverage:
  1. Parse a minimal valid manifest (name + description only).
  2. infer_type for all 3 cases: mcp transport → tool; tools_exposed → tool;
     neither → declarative.
  3. extra="allow" accepts an unknown legacy field (e.g. allowed-tools).
  4. load_skill against real SKILL.md files in axis-runtime:
       - "axis-cc"   → type tool  (has tools_exposed)
       - "transcribe" → type declarative (no tools_exposed, no transport)
  5. load_skill raises FileNotFoundError for a non-existent skill.
  6. load_skill raises ValueError on version mismatch.
"""
from __future__ import annotations

import pytest

from axis_skill_registry import (
    MANIFEST_VERSION,
    SkillManifest,
    infer_type,
    load_skill,
    manifest_version,
    parse_skill_manifest,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AXIS_RUNTIME_SKILLS = "/Users/eluru/axis-runtime/skills"

_MINIMAL_SKILL_MD = """\
---
name: my-skill
description: Does something useful.
---

# Body
"""

_MCP_TRANSPORT_MD = """\
---
name: mcp-skill
description: An MCP-backed skill.
transport:
  kind: mcp
  server: axis-mcp
  tool: do_something
---
"""

_TOOLS_EXPOSED_MD = """\
---
name: tool-skill
description: Exposes tools.
tools_exposed:
  - tool_a
  - tool_b
---
"""

_LEGACY_FIELD_MD = """\
---
name: legacy-skill
description: Has a legacy frontmatter field.
allowed-tools: [bash, python]
user-invocable: true
---
"""


# ---------------------------------------------------------------------------
# Test 1 — minimal valid manifest is accepted
# ---------------------------------------------------------------------------

def test_minimal_manifest_parses():
    m = parse_skill_manifest(_MINIMAL_SKILL_MD)
    assert isinstance(m, SkillManifest)
    assert m.name == "my-skill"
    assert m.description == "Does something useful."
    assert m.tools_exposed is None
    assert m.transport is None


def test_manifest_version_defaults_to_0_1_0():
    m = parse_skill_manifest(_MINIMAL_SKILL_MD)
    assert manifest_version(m) == "0.1.0"


def test_manifest_version_explicit():
    md = """\
---
name: versioned-skill
description: Has a version.
version: 1.2.3
---
"""
    m = parse_skill_manifest(md)
    assert manifest_version(m) == "1.2.3"


def test_manifest_version_constant():
    assert MANIFEST_VERSION == 1


# ---------------------------------------------------------------------------
# Test 2 — infer_type covers all 3 cases
# ---------------------------------------------------------------------------

def test_infer_type_mcp_transport():
    m = parse_skill_manifest(_MCP_TRANSPORT_MD)
    assert infer_type(m) == "tool"


def test_infer_type_tools_exposed():
    m = parse_skill_manifest(_TOOLS_EXPOSED_MD)
    assert infer_type(m) == "tool"


def test_infer_type_declarative_fallback():
    m = parse_skill_manifest(_MINIMAL_SKILL_MD)
    assert infer_type(m) == "declarative"


def test_infer_type_explicit_inprocess():
    md = """\
---
name: inproc-skill
description: Hot-path skill.
type: inprocess
---
"""
    m = parse_skill_manifest(md)
    assert infer_type(m) == "inprocess"


def test_infer_type_explicit_wins_over_tools_exposed():
    """Explicit type field wins even when tools_exposed would imply tool."""
    md = """\
---
name: override-skill
description: Explicitly inprocess but has tools_exposed.
type: inprocess
tools_exposed:
  - some_tool
---
"""
    m = parse_skill_manifest(md)
    assert infer_type(m) == "inprocess"


# ---------------------------------------------------------------------------
# Test 3 — extra="allow" accepts legacy fields
# ---------------------------------------------------------------------------

def test_extra_allow_accepts_legacy_field():
    m = parse_skill_manifest(_LEGACY_FIELD_MD)
    assert isinstance(m, SkillManifest)
    assert m.name == "legacy-skill"
    # user-invocable was normalized to user_invocable by the parser
    assert m.user_invocable is True
    # allowed-tools is an extra field — pydantic stores it in __pydantic_extra__
    extra = m.model_extra or {}
    # The key may be stored under its original name (hyphenated) since we only
    # normalize user-invocable in the parser.
    assert "allowed-tools" in extra or "allowed_tools" in extra


# ---------------------------------------------------------------------------
# Test 4 — load_skill against real axis-runtime SKILL.md files
# ---------------------------------------------------------------------------

def test_load_skill_axis_cc_is_tool():
    """axis-cc has tools_exposed → inferred type must be tool."""
    result = load_skill("axis-cc", roots=[_AXIS_RUNTIME_SKILLS])
    assert result.type == "tool"
    assert result.manifest.name == "axis-cc"
    assert result.manifest.tools_exposed  # non-empty list
    assert result.version == "0.1.0"
    assert "axis-cc/SKILL.md" in result.path


def test_load_skill_transcribe_is_declarative():
    """transcribe has no tools_exposed and no transport → declarative."""
    result = load_skill("transcribe", roots=[_AXIS_RUNTIME_SKILLS])
    assert result.type == "declarative"
    assert result.manifest.name == "transcribe"
    assert result.version == "0.1.0"
    assert "transcribe/SKILL.md" in result.path


# ---------------------------------------------------------------------------
# Test 5 — not-found raises FileNotFoundError
# ---------------------------------------------------------------------------

def test_load_skill_not_found():
    with pytest.raises(FileNotFoundError, match='skill "does-not-exist" not found'):
        load_skill("does-not-exist", roots=[_AXIS_RUNTIME_SKILLS])


def test_load_skill_empty_roots():
    with pytest.raises(ValueError, match="at least one search root"):
        load_skill("axis-cc", roots=[])


# ---------------------------------------------------------------------------
# Test 6 — version mismatch raises ValueError
# ---------------------------------------------------------------------------

def test_load_skill_version_mismatch():
    # axis-cc has no version in its SKILL.md, defaults to 0.1.0
    with pytest.raises(ValueError, match="version 0.1.0, requested 9.9.9"):
        load_skill("axis-cc", roots=[_AXIS_RUNTIME_SKILLS], version="9.9.9")


def test_load_skill_version_match_succeeds():
    result = load_skill("axis-cc", roots=[_AXIS_RUNTIME_SKILLS], version="0.1.0")
    assert result.version == "0.1.0"
