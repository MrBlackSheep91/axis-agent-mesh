"""Parse SKILL.md files into SkillManifest objects.

Tolerant of legacy frontmatter (name/description/tools_exposed/platforms/
user-invocable): normalizes the kebab-case ``user-invocable`` key to
``user_invocable`` before passing to pydantic. Unknown extra keys are
passed through unchanged (SkillManifest uses extra="allow").
"""
from __future__ import annotations

from typing import Any, Dict

import yaml

from .manifest import SkillManifest


def parse_frontmatter(text: str) -> Dict[str, Any]:
    """Extract and return the YAML frontmatter dict from SKILL.md text.

    Expects the SKILL.md format::

        ---
        name: foo
        description: bar
        ---

        # Body ...

    Returns an empty dict when there is no frontmatter block.
    Also normalises the one kebab-case legacy key seen in the wild:
    ``user-invocable`` → ``user_invocable``.
    """
    stripped = text.strip()
    if not stripped.startswith("---"):
        return {}

    # Find the closing ---
    rest = stripped[3:]  # skip opening ---
    end = rest.find("\n---")
    if end == -1:
        # Try a --- on its own line at the very end
        end = rest.rfind("---")
        if end == -1:
            return {}
        yaml_block = rest[:end]
    else:
        yaml_block = rest[:end]

    try:
        data = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError:
        return {}

    if not isinstance(data, dict):
        return {}

    # Normalize the one kebab-case legacy key.
    if "user-invocable" in data and "user_invocable" not in data:
        data["user_invocable"] = data.pop("user-invocable")

    return data


def parse_skill_manifest(text: str) -> SkillManifest:
    """Parse SKILL.md text into a :class:`SkillManifest`.

    Does NOT validate beyond pydantic type coercion — call
    :func:`~axis_skill_registry.registry.validate_manifest` separately for
    structural validation.

    Raises:
        pydantic.ValidationError: if ``name`` or ``description`` are missing.
    """
    fm = parse_frontmatter(text)
    return SkillManifest.model_validate(fm)
