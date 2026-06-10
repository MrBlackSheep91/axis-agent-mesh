"""The shared-tool catalog (Phase 5c).

The single, declarative list of every `type: tool` skill this server exposes. Adding
a shared tool = one `ToolSpec` entry here — no per-tool boilerplate in server.py.
This is the mechanism the mesh grows on: each entry records WHERE the tool came from
(`origin`), so the catalog doubles as the cross-repo provenance map.

FastMCP derives each tool's JSON schema from the Python function signature + docstring
(in tools.py), so the schema is defined once and never hand-copied — no schema drift.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import tools


@dataclass(frozen=True)
class ToolSpec:
    """One shared tool in the catalog."""
    name: str
    fn: Callable
    description: str
    origin: str                       # repo/registry this capability is canonicalized FROM
    writes: bool = False              # True → mutates state (honours SKILLS_DRY_RUN)
    tags: frozenset[str] = field(default_factory=frozenset)


# The catalog. `origin` makes the cross-repo story explicit: `create_task` and
# `axis_memory_remember` are PORTED from axis-runtime's REGISTRY — so when a client
# carrying Sophie's (invidia) token calls them, that IS a cross-repo skill call
# (ROADMAP criterion 5), with the tenant enforced from the token.
CATALOG: list[ToolSpec] = [
    ToolSpec(
        name="axis_memory_search",
        fn=tools.axis_memory_search,
        description="Hybrid RAG search over AXIS Memory, scoped to the caller's namespace (from token).",
        origin="mesh/axis-memory",
        writes=False,
        tags=frozenset({"memory", "rag", "shared"}),
    ),
    ToolSpec(
        name="axis_memory_remember",
        fn=tools.axis_memory_remember,
        description="Persist a memory chunk to AXIS Memory, scoped to the caller's namespace (from token).",
        origin="axis-runtime/REGISTRY:_tool_memory_remember",
        writes=True,
        tags=frozenset({"memory", "shared"}),
    ),
    ToolSpec(
        name="capture",
        fn=tools.capture,
        description="Persist a capture (idea/task/decision/resource) to AXIS Command Center.",
        origin="mesh/axis-cc",
        writes=True,
        tags=frozenset({"axis-cc", "capture", "shared"}),
    ),
    ToolSpec(
        name="create_task",
        fn=tools.create_task,
        description="Create a task in AXIS Command Center (caller identity from token).",
        origin="axis-runtime/REGISTRY:_tool_create_task",
        writes=True,
        tags=frozenset({"axis-cc", "tasks", "shared"}),
    ),
]


def register_catalog(mcp) -> list[str]:
    """Register every ToolSpec on the FastMCP server. Returns the registered names."""
    for spec in CATALOG:
        mcp.tool(spec.fn, name=spec.name, description=spec.description, tags=set(spec.tags))
    return [spec.name for spec in CATALOG]
