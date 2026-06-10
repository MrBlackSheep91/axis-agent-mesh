"""Skill resolver and structural validator for axis-skill-registry.

Public API:
    ResolvedSkill                 dataclass result from load_skill
    ValidationResult              dataclass result from validate_manifest
    validate_manifest(obj)        structural validation against JSON Schema
    load_skill(name, roots, version=None)   resolve a skill by name
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError

from .manifest import SkillManifest, SkillType, infer_type, manifest_version
from .parser import parse_skill_manifest


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Result of :func:`validate_manifest`."""

    valid: bool
    errors: List[str]


def _load_schema() -> dict:
    """Locate and load the JSON Schema adjacent to this package."""
    # Walk upward from this file to find skill-manifest.schema.json.
    # It lives at: packages/skill-registry/skill-manifest.schema.json
    # This file is at: packages/skill-registry/python/axis_skill_registry/registry.py
    candidates = [
        Path(__file__).parent.parent.parent / "skill-manifest.schema.json",
        Path(__file__).parent.parent.parent.parent / "skill-manifest.schema.json",
    ]
    for p in candidates:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        "axis-skill-registry: could not locate skill-manifest.schema.json"
    )


_SCHEMA: Optional[dict] = None


def _get_schema() -> dict:
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = _load_schema()
    return _SCHEMA


def validate_manifest(obj: object) -> ValidationResult:
    """Validate a (parsed) manifest object against the JSON Schema.

    Uses ``jsonschema`` when available; falls back to a lightweight
    pydantic-only check so the package works without jsonschema installed.

    Returns a :class:`ValidationResult` with ``valid`` and ``errors`` list.
    """
    try:
        import jsonschema  # type: ignore[import-untyped]

        schema = _get_schema()
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
        if not errors:
            return ValidationResult(valid=True, errors=[])
        msgs = [
            f"{'/' + '/'.join(str(p) for p in e.path) if e.path else '(root)'} {e.message}"
            for e in errors
        ]
        return ValidationResult(valid=False, errors=msgs)
    except ImportError:
        pass

    # Lightweight fallback: just check required fields via pydantic.
    if not isinstance(obj, dict):
        return ValidationResult(
            valid=False,
            errors=[f"(root) expected object, got {type(obj).__name__}"],
        )
    try:
        SkillManifest.model_validate(obj)
        return ValidationResult(valid=True, errors=[])
    except ValidationError as exc:
        return ValidationResult(
            valid=False,
            errors=[f"{e['loc']} {e['msg']}" for e in exc.errors()],
        )


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

@dataclass
class ResolvedSkill:
    """Result of :func:`load_skill`."""

    manifest: SkillManifest
    # Resolved type (inferred if the manifest didn't state it).
    type: SkillType
    # Resolved version (defaults to "0.1.0").
    version: str
    # Absolute path to the SKILL.md it came from.
    path: str


def load_skill(
    name: str,
    roots: List[str],
    version: Optional[str] = None,
) -> ResolvedSkill:
    """Resolve a skill by name from one of the given root directories.

    Searches each root for ``<root>/<name>/SKILL.md`` in order and returns
    the first match. Parses and validates the manifest, infers type and
    version, and optionally requires an exact version match.

    Args:
        name:    Skill name (kebab-case id).
        roots:   List of directories to search. Each is checked for
                 ``<root>/<name>/SKILL.md``.
        version: If set, require the resolved manifest version to equal this
                 (exact match).

    Returns:
        A :class:`ResolvedSkill` with manifest, type, version, and path.

    Raises:
        ValueError: if no root is provided.
        FileNotFoundError: if the skill is not found under any root.
        ValueError: if the manifest is structurally invalid.
        ValueError: if ``version`` is specified and doesn't match.
    """
    if not roots:
        raise ValueError(
            "axis-skill-registry: load_skill requires at least one search root"
        )

    found: Optional[str] = None
    for root in roots:
        candidate = Path(root) / name / "SKILL.md"
        if candidate.is_file():
            found = str(candidate)
            break

    if found is None:
        raise FileNotFoundError(
            f'axis-skill-registry: skill "{name}" not found under roots '
            f"[{', '.join(roots)}]"
        )

    text = Path(found).read_text(encoding="utf-8")
    try:
        manifest = parse_skill_manifest(text)
    except Exception as exc:
        raise ValueError(
            f'axis-skill-registry: "{name}" manifest parse error: {exc}'
        ) from exc

    result = validate_manifest(manifest.model_dump(exclude_none=True))
    if not result.valid:
        raise ValueError(
            f'axis-skill-registry: "{name}" manifest invalid:\n  - '
            + "\n  - ".join(result.errors)
        )

    resolved_version = manifest_version(manifest)
    if version is not None and version != resolved_version:
        raise ValueError(
            f'axis-skill-registry: "{name}" is version {resolved_version}, '
            f"requested {version}"
        )

    return ResolvedSkill(
        manifest=manifest,
        type=infer_type(manifest),
        version=resolved_version,
        path=found,
    )
