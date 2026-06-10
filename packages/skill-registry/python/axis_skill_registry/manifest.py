"""Pydantic v2 mirror of the canonical SkillManifest contract.

This module is a faithful, 1:1 mirror of the TypeScript `SkillManifest`
interface (`typescript/src/manifest.ts`) and the JSON Schema
(`skill-manifest.schema.json`). Every field, its optionality, and every
enum/literal is mapped exactly.

`additionalProperties: true` in the schema is mirrored with
`model_config = ConfigDict(extra="allow")` on the root model so that legacy
SKILL.md frontmatter keys (e.g. `allowed-tools`) are tolerated without
validation errors. Optional fields (the TS `?` modifier) are typed
`Optional[...] = None`.

Discriminated unions (`SkillTransport`) are modelled with a pydantic v2
tagged union keyed on the literal `kind` field.
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# ─── transport (discriminated union on `kind`) ────────────────────────────────


class McpTransport(BaseModel):
    """MCP server transport."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["mcp"]
    server: str
    tool: str


class InprocTransport(BaseModel):
    """In-process (hot-path) transport."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["inproc"]
    module: str
    export: Optional[str] = None


class RegistryTransport(BaseModel):
    """Registry-routed tool transport."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["registry"]
    tool: str


SkillTransport = Annotated[
    Union[McpTransport, InprocTransport, RegistryTransport],
    Field(discriminator="kind"),
]

# ─── io schema ────────────────────────────────────────────────────────────────


class SkillIoSchema(BaseModel):
    """JSON-Schema-ish description of skill input/output (loose by design at v1)."""

    model_config = ConfigDict(extra="forbid")

    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None


# ─── root manifest ────────────────────────────────────────────────────────────

SkillType = Literal["tool", "inprocess", "declarative"]

# Current manifest format version. Loaders reject unknown versions.
MANIFEST_VERSION = 1


class SkillManifest(BaseModel):
    """Extended SKILL.md frontmatter.

    Mirror of @axis/skill-registry SkillManifest (v1).
    extra="allow" is intentional — tolerates legacy frontmatter keys such as
    `allowed-tools` without validation errors (additionalProperties:true in
    the JSON Schema).
    """

    model_config = ConfigDict(extra="allow")

    # ─── existing SKILL.md frontmatter (unchanged) ───────────────────────────
    # kebab-case id, unique within scope.
    name: str
    # When to invoke + what it does (drives LLM tool selection).
    description: str
    # Tool names this skill exposes in the host REGISTRY (axis-runtime convention).
    tools_exposed: Optional[List[str]] = None
    # OS platforms the skill supports.
    platforms: Optional[List[str]] = None
    # Whether a user can invoke it directly (Claude Code skills).
    user_invocable: Optional[bool] = None

    # ─── new in the extended manifest (all optional, back-compatible) ────────
    # Semver of THIS skill. Defaults to "0.1.0" when absent.
    version: Optional[str] = None
    # Skill kind. Inferred via `infer_type()` when absent.
    type: Optional[SkillType] = None
    io_schema: Optional[SkillIoSchema] = None
    # How the skill resolves at runtime. Required-ish for `type: tool`.
    transport: Optional[SkillTransport] = None
    # Names of other skills this one needs.
    dependencies: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    # Tenants allowed to use this skill (enforced at the MCP server via token).
    tenants: Optional[List[str]] = None


def infer_type(m: SkillManifest) -> SkillType:
    """Infer the skill type when the manifest doesn't state it.

    Rules (identical to the TypeScript inferType function):
      - has ``transport.kind == "mcp"``       → tool
      - has non-empty ``tools_exposed``        → tool
      - otherwise                              → declarative

    Note: ``inprocess`` must be declared explicitly — it cannot be inferred
    from frontmatter alone.
    """
    if m.type is not None:
        return m.type
    if m.transport is not None and m.transport.kind == "mcp":
        return "tool"
    if m.tools_exposed and len(m.tools_exposed) > 0:
        return "tool"
    return "declarative"


def manifest_version(m: SkillManifest) -> str:
    """Return the version of a manifest, defaulting to '0.1.0' when unset."""
    return m.version if m.version is not None else "0.1.0"
