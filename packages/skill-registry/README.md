# @axis/skill-registry

The **skill manifest standard + resolver** for the axis ecosystem (Wave B, Phase 5a).

A skill is described by an **extended `SKILL.md` frontmatter** — the existing format
(`name`, `description`, `tools_exposed`, `platforms`) plus the fields needed to route
it: `type`, `version`, `io_schema`, `transport`, `dependencies`, `tags`, `tenants`.
All new fields are optional, so the 19 axis-runtime `SKILL.md` files keep parsing
unchanged; `type` is inferred when absent.

> Decided in Phase 5: extend `SKILL.md` rather than invent a separate `skill.yaml`
> — one format, already adopted. See `.planning/.../05-SKILL-CONTRACT-SPEC.md`.

## The three kinds of skill

| `type` | What it is | Transport |
|--------|-----------|-----------|
| `tool` | callable capability, reused across agents, usually I/O | **MCP** (shared server) or host `registry` |
| `inprocess` | hot-path / stateful logic local to one agent | in-process function |
| `declarative` | procedural know-how injected into the LLM prompt (Agent Skills) | the `SKILL.md` itself |

When `type` is absent it's inferred: `transport.kind: mcp` or non-empty
`tools_exposed` → `tool`; otherwise → `declarative`. (`inprocess` must be explicit.)

## Manifest (extended SKILL.md frontmatter)

```yaml
---
name: axis-memory-search
description: Hybrid RAG search over AXIS Memory, tenant-scoped.
version: 1.0.0
type: tool
transport: { kind: mcp, server: axis-skills, tool: axis_memory_search }
io_schema:
  input:  { query: string, namespace: string }
  output: { hits: array }
tags: [memory, rag, shared]
tenants: [invidia, maicol]
---
# axis-memory-search
...markdown body (the skill's docs / declarative instructions)...
```

## Usage

```ts
import { loadSkill, parseSkillManifest, validateManifest, inferType } from "@axis/skill-registry";

// Resolve a skill by name from one or more search roots:
const skill = loadSkill("axis-memory-search", {
  roots: ["/path/to/axis-runtime/skills", "/path/to/agent/skills"],
  version: "1.0.0", // optional exact-match gate
});
// -> { manifest, type, version, path }

// Or parse/validate a manifest directly:
const m = parseSkillManifest(skillMdText);
const { valid, errors } = validateManifest(m);
```

`loadSkill` searches `<root>/<name>/SKILL.md` in order, parses + validates the
frontmatter, infers `type`/`version`, and throws a clear error on not-found, invalid
manifest, or version mismatch.

## Scope (Phase 5a)

This package is the **manifest standard + resolver** only. It does not run skills.
- `type: tool` skills are served by the **AXIS Skills MCP server** (Phase 5b).
- Porting axis-runtime's tool-like skills + exposing Sophie's tool-dispatch skills
  (in parallel, no cutover) is **Phase 5c**.
- A Python mirror (`axis_skill_registry`) ships alongside for Python consumers
  (axis-runtime, the MCP server).
