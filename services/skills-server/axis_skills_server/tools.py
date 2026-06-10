"""The shared tool-skills served by the AXIS Skills MCP server (Phase 5b/5c).

Four shared (type A) tools — the ecosystem's reusable, I/O capabilities, each
defined ONCE here instead of N times per repo:
  - axis_memory_search    (read)   — replaces 3 copies (Py skill, Py REGISTRY, TS)
  - axis_memory_remember  (write)  — ported from axis-runtime REGISTRY `_tool_memory_remember` (5c)
  - capture               (write)  — replaces 2 copies (Py create_capture, TS createCapture)
  - create_task           (write)  — ported from axis-runtime REGISTRY `_tool_create_task` (5c)

Each derives its tenant/namespace from the request's token via `current_principal()`
— never from a tool argument. Faithful to the originals (axis-runtime/core/integrations):
  - search:    POST {AXIS_MEMORY_URL}/search,        Bearer {AXIS_MEMORY_API_KEY}, graceful → []
  - remember:  POST {AXIS_MEMORY_URL}/ingest/text,   Bearer {AXIS_MEMORY_API_KEY}
  - capture:   POST {AXIS_CC_URL}/api/capture,       header x-api-key {AXIS_API_KEY}
  - create_task: POST {AXIS_CC_URL}/api/tasks,       header x-api-key {AXIS_API_KEY}

Write tools honour SKILLS_DRY_RUN (return a preview, never hit prod) — so the
cross-repo / tenant-isolation tests can run without creating junk in prod.
"""
from __future__ import annotations

import os

import httpx

from .auth import current_principal

_TEXT_MAX = 2000  # cap hit text (parity with the original skill)


def _memory_url() -> str:
    return (os.environ.get("AXIS_MEMORY_URL") or "").rstrip("/")


def _cc_url() -> str:
    return (os.environ.get("AXIS_CC_URL") or "").rstrip("/")


def _dry_run() -> bool:
    return os.environ.get("SKILLS_DRY_RUN", "").strip() in ("1", "true", "yes")


async def axis_memory_search(query: str, mode: str = "hybrid", limit: int = 5) -> list[dict]:
    """Hybrid RAG search over AXIS Memory, scoped to the caller's namespace.

    The namespace is taken from the authenticated token, NOT from an argument.
    Returns citation-ready hits `{text, score, metadata}`. Graceful degradation:
    returns [] (without raising) if AXIS_MEMORY_URL is unset, the query is empty,
    or the service errors.
    """
    principal = current_principal()  # raises if unauthenticated
    base = _memory_url()
    if not base or not query:
        return []

    headers = {"Content-Type": "application/json"}
    key = os.environ.get("AXIS_MEMORY_API_KEY", "")
    if key:
        headers["Authorization"] = f"Bearer {key}"

    body = {"query": query, "namespace": principal.namespace, "mode": mode, "limit": limit}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{base}/search", headers=headers, json=body)
            if resp.status_code >= 400:
                return []
            data = resp.json()
    except Exception:
        return []

    hits = data.get("results") or data.get("hits") or data if isinstance(data, (list, dict)) else []
    if isinstance(hits, dict):
        hits = hits.get("results") or hits.get("hits") or []
    out: list[dict] = []
    for h in hits or []:
        if not isinstance(h, dict):
            continue
        text = str(h.get("text", ""))[:_TEXT_MAX]
        out.append({"text": text, "score": h.get("score"), "metadata": h.get("metadata", {})})
    return out


async def capture(text: str, type: str = "idea", project: str | None = None) -> dict:
    """Persist a capture (idea/task/decision/resource) to AXIS Command Center.

    Writes via POST /api/capture (x-api-key auth). When SKILLS_DRY_RUN is set,
    does NOT hit the API — returns a preview — so tests never create junk captures.
    """
    principal = current_principal()  # raises if unauthenticated
    body: dict = {"text": text, "type": type}
    if project:
        body["project"] = project

    if _dry_run():
        return {"dry_run": True, "would_post": "/api/capture", "by": principal.agent, "body": body}

    base = _cc_url()
    key = os.environ.get("AXIS_API_KEY", "")
    if not base or not key:
        raise RuntimeError("skills-server: AXIS_CC_URL / AXIS_API_KEY not configured")

    headers = {"x-api-key": key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{base}/api/capture", headers=headers, json=body)
        resp.raise_for_status()
        return resp.json() if resp.text else {}


async def axis_memory_remember(text: str, type: str = "fact", tags: list[str] | None = None) -> dict:
    """Persist a memory chunk to AXIS Memory, scoped to the caller's namespace.

    Ported from axis-runtime REGISTRY `_tool_memory_remember` (5c). The namespace
    is taken from the authenticated token, NOT an argument — a caller can only write
    into its own tenant's memory. Writes via POST /ingest/text (Bearer auth). Honours
    SKILLS_DRY_RUN (returns a preview instead of writing).
    """
    principal = current_principal()  # raises if unauthenticated
    body = {"content": text, "namespace": principal.namespace, "type": type, "tags": tags or []}

    if _dry_run():
        return {"dry_run": True, "would_post": "/ingest/text", "by": principal.agent,
                "tenant": principal.tenant, "body": body}

    base = _memory_url()
    if not base:
        raise RuntimeError("skills-server: AXIS_MEMORY_URL not configured")
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("AXIS_MEMORY_API_KEY", "")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{base}/ingest/text", headers=headers, json=body)
        resp.raise_for_status()
        return resp.json() if resp.text else {}


async def create_task(title: str, project: str | None = None, priority: str = "medium",
                      due: str | None = None) -> dict:
    """Create a task in AXIS Command Center.

    Ported from axis-runtime REGISTRY `_tool_create_task` (5c). The caller's identity
    (agent/tenant) is recorded from the token, never an argument. Writes via
    POST /api/tasks (x-api-key auth). Honours SKILLS_DRY_RUN (returns a preview).
    """
    principal = current_principal()  # raises if unauthenticated
    body: dict = {"title": title, "priority": priority}
    if project:
        body["project"] = project
    if due:
        body["due"] = due

    if _dry_run():
        return {"dry_run": True, "would_post": "/api/tasks", "by": principal.agent,
                "tenant": principal.tenant, "body": body}

    base = _cc_url()
    key = os.environ.get("AXIS_API_KEY", "")
    if not base or not key:
        raise RuntimeError("skills-server: AXIS_CC_URL / AXIS_API_KEY not configured")
    headers = {"x-api-key": key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{base}/api/tasks", headers=headers, json=body)
        resp.raise_for_status()
        return resp.json() if resp.text else {}
