/**
 * SkillManifest — the canonical description of a skill in the axis ecosystem.
 *
 * It is the EXISTING `SKILL.md` frontmatter (name, description, tools_exposed,
 * platforms, user-invocable) EXTENDED with the fields needed to route a skill to
 * the right transport: `type`, `version`, `io_schema`, `transport`, `dependencies`,
 * `tags`, `tenants`. All new fields are optional so the 19 axis-runtime SKILL.md
 * files keep parsing unchanged; `type` is inferred when absent.
 *
 * Decided in Phase 5 (05-SKILL-CONTRACT-SPEC): we extend SKILL.md rather than invent
 * a separate `skill.yaml` — one format, already adopted.
 */

/** Current manifest format version. Loaders reject unknown versions. */
export const MANIFEST_VERSION = 1 as const;

/**
 * The three kinds of skill (see the SPEC). Routing depends on this:
 *  - tool        → a callable capability, usually served via MCP (shared, cross-agent)
 *  - inprocess   → hot-path / stateful logic that stays a local function in the agent
 *  - declarative → procedural know-how injected into the LLM system prompt (Agent Skills)
 */
export type SkillType = "tool" | "inprocess" | "declarative";

export type SkillTransport =
  | { kind: "mcp"; server: string; tool: string }
  | { kind: "inproc"; module: string; export?: string }
  | { kind: "registry"; tool: string };

export interface SkillIoSchema {
  /** JSON-Schema-ish description of the input args (loose by design at v1). */
  input?: Record<string, unknown>;
  /** JSON-Schema-ish description of the output. */
  output?: Record<string, unknown>;
}

export interface SkillManifest {
  // ─── existing SKILL.md frontmatter (unchanged) ──────────────────────────────
  /** kebab-case id, unique within scope. */
  name: string;
  /** When to invoke + what it does (drives LLM tool selection). */
  description: string;
  /** Tool names this skill exposes in the host REGISTRY (axis-runtime convention). */
  tools_exposed?: string[];
  /** OS platforms the skill supports. */
  platforms?: string[];
  /** Whether a user can invoke it directly (Claude Code skills). */
  user_invocable?: boolean;

  // ─── new in the extended manifest (all optional, back-compatible) ───────────
  /** Semver of THIS skill. Defaults to "0.1.0" when absent. */
  version?: string;
  /** Skill kind. Inferred via `inferType()` when absent. */
  type?: SkillType;
  io_schema?: SkillIoSchema;
  /** How the skill resolves at runtime. Required-ish for `type: tool`. */
  transport?: SkillTransport;
  /** Names of other skills this one needs (the AGENT orchestrates; no nested MCP). */
  dependencies?: string[];
  tags?: string[];
  /** Tenants allowed to use this skill (enforced at the MCP server via token). */
  tenants?: string[];
}

/**
 * Infer the skill type when the manifest doesn't state it, so legacy SKILL.md files
 * classify correctly without edits:
 *   - has `transport.kind: mcp`           → tool
 *   - has `tools_exposed`                 → tool
 *   - otherwise                           → declarative
 * (`inprocess` must be declared explicitly — it can't be inferred from frontmatter.)
 */
export function inferType(m: SkillManifest): SkillType {
  if (m.type) return m.type;
  if (m.transport?.kind === "mcp") return "tool";
  if (m.tools_exposed && m.tools_exposed.length > 0) return "tool";
  return "declarative";
}

/** The version of a manifest, defaulting to "0.1.0" when unset. */
export function manifestVersion(m: SkillManifest): string {
  return m.version ?? "0.1.0";
}
