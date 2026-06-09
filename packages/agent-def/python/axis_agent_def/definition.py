"""Pydantic v2 mirror of the canonical AgentDefinition contract.

This module is a faithful, 1:1 mirror of the TypeScript `AgentDefinition`
interface (`typescript/src/agent-definition.ts`) and the JSON Schema
(`agent-definition.schema.json`). Every field, its optionality, and every
enum/literal is mapped exactly.

`additionalProperties: false` in the schema is mirrored with
`model_config = ConfigDict(extra="forbid")` on every model. Optional fields
(the TS `?` modifier) are typed `Optional[...] = None`.

Discriminated unions (`KnowledgeSource`, `AgentTrigger`) are modelled with a
pydantic v2 tagged union keyed on the literal `type` field.
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# ─── identity ─────────────────────────────────────────────────────────────────


class AgentTenant(BaseModel):
    """Tenant addressing — customer/org pair."""

    model_config = ConfigDict(extra="forbid")

    customer: str
    org: str


class AgentIdentity(BaseModel):
    """Stable identity of the agent (id, fqid, tenant, agent version)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    fqid: str
    name: str
    brand: Optional[str] = None
    tenant: AgentTenant
    # Bumped whenever THIS agent's definition changes (audit/rollback trail).
    version: int


# ─── goal (GOA — Goal-Oriented Architecture) ───────────────────────────────────


class AgentGoal(BaseModel):
    """What outcome the agent exists to achieve and how success is measured."""

    model_config = ConfigDict(extra="forbid")

    objective: str
    success_criteria: List[str]
    kpis_ref: Optional[List[str]] = None


# ─── context scope / knowledge sources ─────────────────────────────────────────


class AxisMemoryKnowledgeSource(BaseModel):
    """axis-memory partition source."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["axis-memory"]
    scope: str
    max_chunks: Optional[float] = None


class VaultKnowledgeSource(BaseModel):
    """Obsidian vault paths source."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["vault"]
    paths: List[str]


class NeonTableKnowledgeSource(BaseModel):
    """Neon/Postgres table source."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["neon-table"]
    table: str
    where: Optional[str] = None


class Neo4jKnowledgeSource(BaseModel):
    """Neo4j cypher source."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["neo4j"]
    cypher: str


KnowledgeSource = Annotated[
    Union[
        AxisMemoryKnowledgeSource,
        VaultKnowledgeSource,
        NeonTableKnowledgeSource,
        Neo4jKnowledgeSource,
    ],
    Field(discriminator="type"),
]


class AgentContextScope(BaseModel):
    """Memory namespace + knowledge sources + cross-tenant read perms."""

    model_config = ConfigDict(extra="forbid")

    memory_namespace: str
    knowledge_sources: List[KnowledgeSource]
    read_only_tenants: Optional[List[str]] = None


# ─── skills ────────────────────────────────────────────────────────────────────


class AgentSkill(BaseModel):
    """A skill the agent is wired to, with optional config override."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    enabled: bool
    config_override: Optional[Dict[str, Any]] = None


# ─── model routing ─────────────────────────────────────────────────────────────


class AgentCanary(BaseModel):
    """Canary rollout config for the candidate model/role."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["off", "shadow", "ab_split", "on"]
    pct: Optional[float] = None
    target: Optional[str] = None


class AgentModelRouting(BaseModel):
    """Default model/role, per-skill and per-stage overrides, fallback chain."""

    model_config = ConfigDict(extra="forbid")

    default: str
    per_skill: Optional[Dict[str, str]] = None
    per_stage: Optional[Dict[str, str]] = None
    fallback_chain: List[str]
    canary: Optional[AgentCanary] = None


# ─── guardrails ────────────────────────────────────────────────────────────────


class AgentGuardrail(BaseModel):
    """A guardrail with a severity and free-form config."""

    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Literal["block", "warn", "log"]
    config: Dict[str, Any]


# ─── kpis (what to measure) ─────────────────────────────────────────────────────


class AgentKpi(BaseModel):
    """A measurable KPI with its source, optional query/target, and direction."""

    model_config = ConfigDict(extra="forbid")

    name: str
    source: Literal["langfuse", "postgres", "computed"]
    query: Optional[str] = None
    target: Optional[float] = None
    direction: Literal["higher_better", "lower_better"]


# ─── runtime / triggers ──────────────────────────────────────────────────────────


class WebhookTrigger(BaseModel):
    """HTTP webhook trigger."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["webhook"]
    route: str


class ScheduleTrigger(BaseModel):
    """Cron schedule trigger."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["schedule"]
    cron: str


class QueueTrigger(BaseModel):
    """Queue/channel trigger."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["queue"]
    channel: str


class ManualTrigger(BaseModel):
    """Manual trigger (no extra fields)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["manual"]


AgentTrigger = Annotated[
    Union[WebhookTrigger, ScheduleTrigger, QueueTrigger, ManualTrigger],
    Field(discriminator="type"),
]


class AgentGovernance(BaseModel):
    """Output budget, confirmation gating, optional reflection interval."""

    model_config = ConfigDict(extra="forbid")

    output_budget: Optional[Literal["default", "tight", "loose"]] = None
    confirmation_gate: Literal["disabled", "enabled", "required"]
    reflection_interval: Optional[float] = None


class AgentObservability(BaseModel):
    """Langfuse project + tags."""

    model_config = ConfigDict(extra="forbid")

    langfuse_project: str
    tags: List[str]


class AgentRuntime(BaseModel):
    """Deployment target, triggers, governance, observability."""

    model_config = ConfigDict(extra="forbid")

    deployment_target: Literal["axis-runtime", "axis-cc", "lambda", "local"]
    trigger: List[AgentTrigger]
    governance: AgentGovernance
    observability: AgentObservability


# ─── root ────────────────────────────────────────────────────────────────────────


class AgentDefinition(BaseModel):
    """Canonical contract every agent in the axis ecosystem conforms to.

    `version` is the AgentDefinition FORMAT version (mirrors SCHEMA_VERSION),
    NOT the agent's own version — that lives in `identity.version`.
    """

    model_config = ConfigDict(extra="forbid")

    version: int
    identity: AgentIdentity
    goal: AgentGoal
    context_scope: AgentContextScope
    skills: List[AgentSkill]
    model_routing: AgentModelRouting
    guardrails: List[AgentGuardrail]
    kpis: List[AgentKpi]
    runtime: AgentRuntime
