# axis-agent-mesh

Unified agent build/config/deploy layer across Maicol's ecosystem. Three repos hold the best implementations of three different layers — `invidia-chat-api` owns the model registry, `axis-runtime` owns the kernel + multi-tenant SOUL loader, `axis-cc` owns observability + cost intelligence. This monorepo stitches them into a shared package layer so every new agent or tenant is configuration, not a rewrite.

Full project context: `.planning/projects/axis-agent-mesh/PROJECT.md` in `axis-command-center`.

## Purpose

Kill drift of retired models in production execution paths (~38 prod files today). New agents (MAIK, Sophie, Moltbook, EUTENEA, Lady, plus every future tenant) become deployable from a single canonical `AgentDefinition` JSON. Hybrid CRM becomes the canonical builder UI. AXIS CC becomes the canonical observability surface. `axis-runtime` becomes the canonical runtime. No more parallel reimplementations.

## Layout

```
axis-agent-mesh/
  package.json                              # Node workspace (packages/*)
  pyproject.toml                            # Shared black/ruff/pytest config
  README.md
  .gitignore
  packages/
    agent-registry/                         # Phase 1 — Wave A — SHIPPED
      pyproject.toml                        # axis-agent-registry@0.1.0
      python/
        axis_agent_registry/
          __init__.py
          catalog.py                        # CATALOG + ModelSpec
          assignments.py                    # DEFAULT_ASSIGNMENTS
          registry.py                       # get_model_for + overrides
        tests/
          __init__.py
          test_registry.py                  # 12 tests
    agent-def/                              # Phase 4 (Wave B) — STUB
    skill-registry/                         # Phase 5 (Wave B) — STUB
    agent-kernel/                           # Phase 7 (Wave C) — STUB
```

Packages 2-4 land in Waves B and C. Each package is independently versionable.

## Conventions

- **Python primary, TS twin.** The Python source-of-truth (e.g. `packages/agent-registry/python/`) is authoritative. The TS mirror (added in Plan 02) is generated from Python via `bin/sync-twin.ts`.
- **Kebab-case package names** at the npm/PyPI level (`axis-agent-registry`); snake_case Python module names (`axis_agent_registry`).
- **Local path deps during dev.** Consumers (Sophie via `invidia-chat-api`, axis-cc, hybrid-crm) install with `pip install -e file:///Users/eluru/axis-agent-mesh/packages/<pkg>`. Phase 2-9 promote to a registry.
- **Multi-model routing must survive.** OpenRouter is policy. No framework that forces single-provider.
- **Branch convention:** `BlackSheep` matches the ecosystem (axis-command-center, vault, axis-runtime).

## How to add a package

1. Create the directory `packages/<name>/` with `pyproject.toml` (if Python) and/or `package.json` (if TS).
2. Python package source goes in `packages/<name>/python/<snake_module>/`; tests in `packages/<name>/python/tests/`.
3. TS package source goes in `packages/<name>/src/`; tests in `packages/<name>/tests/`.
4. Append the package to `packages/` enumeration in this README's Layout section.
5. Update the project ROADMAP at `.planning/projects/axis-agent-mesh/ROADMAP.md` to reflect the shipped capability.
6. If the package mirrors a Python source-of-truth in TS (twin pattern), wire `bin/sync-twin.ts` to regenerate the TS surface on demand.

For the registry-package precedent, read `packages/agent-registry/python/axis_agent_registry/registry.py` and `tests/test_registry.py`.
