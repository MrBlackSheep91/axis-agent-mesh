/**
 * Canonical AgentDefinition — the one contract every agent in the axis ecosystem
 * conforms to (MAIK, Sophie, Moltbook, Jaime, Lady, and future agents).
 *
 * Source of truth lives in git as `<agent>/.agent.json` (config-as-code). Postgres
 * may index these for queries, but the file is authoritative.
 *
 * This TS interface is the canonical shape; `agent-definition.schema.json` (JSON
 * Schema) and the pydantic `AgentDefinition` (Python) are mirrors kept in sync.
 *
 * Derived from EXPLORATION-2026-05-27 §5 (sketch validated against all 5 agents).
 */

/** Current AgentDefinition format version. Loaders MUST reject unknown versions. */
export const SCHEMA_VERSION = 1 as const;

export interface AgentDefinition {
  /**
   * AgentDefinition FORMAT version (not the agent's own version — that's
   * `identity.version`). Bumped only when this schema changes shape. A loader
   * encountering a version it doesn't know how to parse MUST reject the file
   * with a clear error rather than silently mis-parsing it.
   */
  version: number;

  identity: AgentIdentity;
  goal: AgentGoal;
  context_scope: AgentContextScope;
  skills: AgentSkill[];
  model_routing: AgentModelRouting;
  guardrails: AgentGuardrail[];
  kpis: AgentKpi[];
  runtime: AgentRuntime;
}

// ─── identity ─────────────────────────────────────────────────────────────────

export interface AgentIdentity {
  /** Stable UUID. Never changes for the life of the agent. */
  id: string;
  /** `customer/org/agent` — the axis-runtime addressing convention. */
  fqid: string;
  /** Human-readable name. */
  name: string;
  /** Brand label, e.g. "MAIK", "Sophie", "Moltbook". */
  brand?: string;
  tenant: AgentTenant;
  /** Bumped whenever THIS agent's definition changes (audit/rollback trail). */
  version: number;
}

export interface AgentTenant {
  /** e.g. "maicol", "invidia", "fer-madero". */
  customer: string;
  /** e.g. "personal", "main", "money-mastery". */
  org: string;
}

// ─── goal (GOA — Goal-Oriented Architecture) ───────────────────────────────────

export interface AgentGoal {
  /** What outcome the agent exists to achieve (not the steps). */
  objective: string;
  /** Measurable conditions that mean the objective was met. */
  success_criteria: string[];
  /** Optional references into the `kpis` section (by `kpis[].name`). */
  kpis_ref?: string[];
}

// ─── context scope ─────────────────────────────────────────────────────────────

export interface AgentContextScope {
  /** `customer/<c>/org/<o>/agent/<a>` memory partition. */
  memory_namespace: string;
  knowledge_sources: KnowledgeSource[];
  /** Cross-tenant read perms — rare, governance-gated. */
  read_only_tenants?: string[];
}

export type KnowledgeSource =
  | { type: "axis-memory"; scope: string; max_chunks?: number }
  | { type: "vault"; paths: string[] }
  | { type: "neon-table"; table: string; where?: string }
  | { type: "neo4j"; cypher: string };

// ─── skills ────────────────────────────────────────────────────────────────────

export interface AgentSkill {
  /** Matches a skill-registry id (resolved via @axis/skill-registry). */
  name: string;
  /** Semver, e.g. "1.2.0", or "*" for latest. */
  version: string;
  enabled: boolean;
  config_override?: Record<string, unknown>;
  /**
   * Optional resolution hint. Normally the skill's own manifest declares its kind
   * (tool→MCP / inprocess / declarative); this overrides it for this agent. When
   * absent, the loader resolves the kind from the skill manifest (single source of
   * truth). Added in Phase 5a — backward-compatible (optional).
   */
  source?: "mcp" | "inprocess" | "declarative";
}

// ─── model routing ─────────────────────────────────────────────────────────────

export interface AgentModelRouting {
  /** A registry role name (resolved via @axis/agent-registry) or a literal model id. */
  default: string;
  /** Per-skill override: skill name → role/model id. */
  per_skill?: Record<string, string>;
  /** Per-pipeline-stage override: stage name → role/model id. */
  per_stage?: Record<string, string>;
  /** Ordered fallback chain, e.g. retry targets on 429/404. */
  fallback_chain: string[];
  canary?: AgentCanary;
}

export interface AgentCanary {
  mode: "off" | "shadow" | "ab_split" | "on";
  /** Percent of traffic for ab_split/shadow (0–100). */
  pct?: number;
  /** The candidate model/role being canaried. */
  target?: string;
}

// ─── guardrails ────────────────────────────────────────────────────────────────

export interface AgentGuardrail {
  /** e.g. "rate-limit", "blocked-pattern", "max-tokens". */
  id: string;
  severity: "block" | "warn" | "log";
  config: Record<string, unknown>;
}

// ─── kpis (what to measure) ─────────────────────────────────────────────────────

export interface AgentKpi {
  /** e.g. "engagement_rate", "ticket_resolution_pct". */
  name: string;
  source: "langfuse" | "postgres" | "computed";
  query?: string;
  target?: number;
  direction: "higher_better" | "lower_better";
}

// ─── runtime ────────────────────────────────────────────────────────────────────

export interface AgentRuntime {
  deployment_target: "axis-runtime" | "axis-cc" | "lambda" | "local";
  trigger: AgentTrigger[];
  governance: AgentGovernance;
  observability: AgentObservability;
}

export type AgentTrigger =
  | { type: "webhook"; route: string }
  | { type: "schedule"; cron: string }
  | { type: "queue"; channel: string }
  | { type: "manual" };

export interface AgentGovernance {
  output_budget?: "default" | "tight" | "loose";
  confirmation_gate: "disabled" | "enabled" | "required";
  reflection_interval?: number;
}

export interface AgentObservability {
  /** Langfuse project, e.g. "axis-cc", "invidia", "moltbook". */
  langfuse_project: string;
  tags: string[];
}
