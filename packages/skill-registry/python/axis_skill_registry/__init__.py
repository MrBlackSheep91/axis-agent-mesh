"""axis-skill-registry — the skill manifest standard + resolver (Python mirror).

The TypeScript package (``typescript/src/``) is the canonical shape; the JSON
Schema (``skill-manifest.schema.json``) and this Python package are mirrors
kept in sync.

Public API:
    MANIFEST_VERSION                 int — current SkillManifest format version (1)
    SkillManifest                    pydantic v2 root model
    SkillType                        Literal["tool", "inprocess", "declarative"]
    infer_type(m)                    infer the skill type from a manifest
    manifest_version(m)              return the version, defaulting to "0.1.0"
    parse_skill_manifest(text)       SKILL.md text → SkillManifest
    validate_manifest(obj)           structural validation → ValidationResult
    load_skill(name, roots, version) resolve a skill by name
    ResolvedSkill                    dataclass result from load_skill
    ValidationResult                 dataclass result from validate_manifest
"""
from __future__ import annotations

from .manifest import (
    MANIFEST_VERSION,
    InprocTransport,
    McpTransport,
    RegistryTransport,
    SkillIoSchema,
    SkillManifest,
    SkillTransport,
    SkillType,
    infer_type,
    manifest_version,
)
from .parser import parse_frontmatter, parse_skill_manifest
from .registry import ResolvedSkill, ValidationResult, load_skill, validate_manifest

__all__ = [
    "MANIFEST_VERSION",
    "SkillManifest",
    "SkillType",
    "SkillTransport",
    "McpTransport",
    "InprocTransport",
    "RegistryTransport",
    "SkillIoSchema",
    "infer_type",
    "manifest_version",
    "parse_frontmatter",
    "parse_skill_manifest",
    "validate_manifest",
    "ValidationResult",
    "load_skill",
    "ResolvedSkill",
]

__version__ = "0.1.0"
