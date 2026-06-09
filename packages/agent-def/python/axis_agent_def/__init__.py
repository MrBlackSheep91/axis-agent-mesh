"""axis-agent-def — pydantic v2 mirror of the canonical AgentDefinition contract.

The TypeScript interface (`typescript/src/agent-definition.ts`) is the canonical
shape; the JSON Schema (`agent-definition.schema.json`) and this Python package
are mirrors kept in sync.

Public API:
    SCHEMA_VERSION                      int — current AgentDefinition format version (1)
    AgentDefinition                     pydantic v2 root model
    load_agent_definition(data)         version-gated parse + validate helper
    + every sub-model (AgentIdentity, AgentTenant, ... AgentObservability)

Source of truth for an agent lives in git as `<agent>/.agent.json`
(config-as-code). Loaders MUST reject unknown `version` values rather than
silently mis-parsing.
"""
from __future__ import annotations

import json
from typing import Union

from .definition import (
    AgentCanary,
    AgentContextScope,
    AgentDefinition,
    AgentGoal,
    AgentGovernance,
    AgentGuardrail,
    AgentIdentity,
    AgentKpi,
    AgentModelRouting,
    AgentObservability,
    AgentRuntime,
    AgentSkill,
    AgentTenant,
    AgentTrigger,
    AxisMemoryKnowledgeSource,
    KnowledgeSource,
    ManualTrigger,
    Neo4jKnowledgeSource,
    NeonTableKnowledgeSource,
    QueueTrigger,
    ScheduleTrigger,
    VaultKnowledgeSource,
    WebhookTrigger,
)

# Current AgentDefinition format version. Mirrors SCHEMA_VERSION in the TS
# contract. Loaders MUST reject unknown versions.
SCHEMA_VERSION = 1

__all__ = [
    "SCHEMA_VERSION",
    "AgentDefinition",
    "load_agent_definition",
    # sub-models
    "AgentIdentity",
    "AgentTenant",
    "AgentGoal",
    "AgentContextScope",
    "KnowledgeSource",
    "AxisMemoryKnowledgeSource",
    "VaultKnowledgeSource",
    "NeonTableKnowledgeSource",
    "Neo4jKnowledgeSource",
    "AgentSkill",
    "AgentModelRouting",
    "AgentCanary",
    "AgentGuardrail",
    "AgentKpi",
    "AgentRuntime",
    "AgentTrigger",
    "WebhookTrigger",
    "ScheduleTrigger",
    "QueueTrigger",
    "ManualTrigger",
    "AgentGovernance",
    "AgentObservability",
]

__version__ = "0.1.0"


def load_agent_definition(data: Union[str, dict]) -> AgentDefinition:
    """Parse and validate an AgentDefinition, gating on the format version.

    Args:
        data: A JSON string or an already-parsed dict.

    Returns:
        The validated, typed ``AgentDefinition`` model.

    Raises:
        ValueError: If ``data`` is a string that isn't valid JSON, if the
            top-level ``version`` is missing/unsupported (version-gated BEFORE
            pydantic validation), or if pydantic validation fails.
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid AgentDefinition JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"AgentDefinition must be an object, got {type(data).__name__}"
        )

    # Version-gate BEFORE pydantic validation: an unknown format version must
    # be rejected with a clear error rather than mis-parsed.
    v = data.get("version")
    if v != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported AgentDefinition version {v} (handles {SCHEMA_VERSION})"
        )

    return AgentDefinition.model_validate(data)
