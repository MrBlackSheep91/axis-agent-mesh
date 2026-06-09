# @axis/agent-def

The canonical **AgentDefinition** contract for the axis ecosystem. One schema that
every agent — MAIK, Sophie, Moltbook, Jaime, Lady, and whatever comes next —
conforms to, so the shared kernel (Wave C) can load any of them the same way.

Part of the [`axis-agent-mesh`](../../README.md) monorepo (Wave B, Phase 4).

## What's in the box

| Artifact | Path | Role |
|----------|------|------|
| TS interface | `typescript/src/agent-definition.ts` | The canonical shape (source of truth) |
| JSON Schema | `agent-definition.schema.json` | Runtime validation (draft 2020-12) |
| pydantic model | `python/axis_agent_def/definition.py` | Python mirror |
| Validator + loader | `typescript/src/index.ts` | `validateAgentDefinition`, `loadAgentDefinition` |
| CLI | `typescript/src/cli.ts` → `axis-mesh` | `axis-mesh validate <path>` |

## Storage model

`.agent.json` files live in **git, next to the agent** (config-as-code). The file is
authoritative. Postgres may index definitions for queries later, but git is the
source of truth. (Decided in Phase 4; see `.planning/.../02-EXECUTION-STATUS.md`.)

## The shape

```
AgentDefinition
├─ version            format version (currently 1; loaders reject unknown)
├─ identity           id, fqid (customer/org/agent), name, brand?, tenant, version
├─ goal               objective + success_criteria[] (GOA — outcomes, not steps)
├─ context_scope      memory_namespace, knowledge_sources[], read_only_tenants?
├─ skills[]           name@version, enabled, config_override?
├─ model_routing      default, per_skill?, per_stage?, fallback_chain[], canary?
├─ guardrails[]       id, severity (block|warn|log), config
├─ kpis[]             name, source, target?, direction
└─ runtime            deployment_target, trigger[], governance, observability
```

`model_routing.default` (and per-skill/per-stage values) may be a **registry role**
(resolved via `@axis/agent-registry`) or a literal model id.

## Usage

### TypeScript

```ts
import { loadAgentDefinition, validateAgentDefinition } from "@axis/agent-def";

const def = loadAgentDefinition(fs.readFileSync("maik.agent.json", "utf8"));
// throws on invalid JSON, unknown version, or schema failure — returns typed AgentDefinition

const { valid, errors } = validateAgentDefinition(someObject); // non-throwing
```

### Python

```python
from axis_agent_def import load_agent_definition

definition = load_agent_definition(open("maik.agent.json").read())
```

### CLI

```bash
axis-mesh validate path/to/agent.json [more.agent.json ...]
# exit 0 = all valid, 1 = a file failed, 2 = usage/IO error
```

## Versioning

- `version` (top-level) is the **format** version. A loader that doesn't recognize it
  rejects the file with a clear error rather than mis-parsing it. Current: `1`.
- `identity.version` is **this agent's** version — bump it whenever the agent's own
  definition changes, for an audit/rollback trail.

## Scope note

Validation here is **structural + version** only. Semantic checks (does the skill
exist in the registry? does the model-routing role resolve?) arrive with the skill
registry in **Phase 5**.
