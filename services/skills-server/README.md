# axis-skills-server

The **AXIS Skills MCP server** (Wave B, Phase 5b). A FastMCP server that exposes
the ecosystem's shared **`type: tool`** skills over **Streamable HTTP**, so any agent
(Sophie, MAIK, Moltbook) can consume them as an MCP client — defining each shared
capability **once** instead of N times per repo.

> ⚠️ **Not deployed.** Phase 5b builds + proves this server locally, in parallel.
> Sophie/MAIK are **not** pointed at it yet — that cutover is Wave C, behind a shadow
> canary. Deploying to Contabo is a separate, explicitly-approved step (see below).

## Tools (the two most-duplicated capabilities)

| Tool | Replaces | Writes? |
|------|----------|---------|
| `axis_memory_search(query, mode?, limit?)` | 3 copies (Py skill, Py REGISTRY, TS unified-memory) | no (read-only) |
| `capture(text, type?, project?)` | 2 copies (Py `create_capture`, TS `createCapture`) | yes (→ AXIS CC `/api/capture`) |

## Security model (tenant isolation)

Each agent has its own **bearer token**; the token carries its principal
(`agent` / `tenant` / `namespace`). **Tools read the tenant/namespace from the token,
never from an argument** — so a caller cannot reach another tenant's data by passing
a different value (confused-deputy / cross-tenant defense, per the MCP security
research). `current_principal()` enforces this; `axis_memory_search` scopes its
namespace from the token.

- **5b (local):** `StaticTokenVerifier` with tokens from `SKILLS_TOKENS` (JSON) or a
  dev fallback.
- **Production:** swap to a `JWTVerifier` against a real issuer — tool code is
  unchanged (it only reads claims).

## Run (local)

```bash
python3.11 -m venv .venv && ./.venv/bin/pip install -e .
# DRY_RUN=1 makes `capture` return a preview instead of writing to prod:
PYTHONPATH=. SKILLS_DRY_RUN=1 ./.venv/bin/python -m axis_skills_server.server
# → Streamable HTTP on http://127.0.0.1:8300/mcp
```

Smoke test (auth + tenant isolation, with the server running):
```python
from fastmcp import Client
import asyncio
async def main():
    async with Client("http://127.0.0.1:8300/mcp", auth="dev-sophie") as c:
        print([t.name for t in await c.list_tools()])             # ['axis_memory_search', 'capture']
        print((await c.call_tool("capture", {"text": "hi"})).data) # by: 'sophie' (from token)
asyncio.run(main())
```
Verified: `dev-sophie` → `by: sophie`; `dev-maik` → `by: maik` (same tool, isolation
holds); an invalid token is rejected with 401.

## Environment

| Var | For | Notes |
|-----|-----|-------|
| `SKILLS_TOKENS` | auth | JSON `{token: {agent, tenant, namespace}}`. Dev fallback if unset. |
| `SKILLS_HOST` / `SKILLS_PORT` | transport | default `127.0.0.1:8300` |
| `SKILLS_DRY_RUN` | safety | `1` → `capture` previews instead of writing |
| `AXIS_MEMORY_URL` / `AXIS_MEMORY_API_KEY` | `axis_memory_search` | AXIS Memory base + bearer key |
| `AXIS_CC_URL` / `AXIS_API_KEY` | `capture` | AXIS CC base + `x-api-key` |

## Deploy to Contabo (Phase 5b cutover — NOT done here, do with explicit approval)

Recommended (reuses the existing infra): a systemd unit on Contabo running the server
on `127.0.0.1:8300`, fronted by the existing nginx (`axishub.duckdns.org/skills/mcp`),
`SKILLS_TOKENS` with real per-agent tokens, `SKILLS_DRY_RUN` unset. Then point ONE
non-critical consumer at it first; Sophie's cutover stays in Wave C.

## Tests

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/ -q
```
