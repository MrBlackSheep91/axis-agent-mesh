"""AXIS Skills MCP server — FastMCP app exposing shared tool-skills over HTTP.

Run (local):
    SKILLS_DRY_RUN=1 ./.venv/bin/python -m axis_skills_server.server

Transport is Streamable HTTP (multi-client) — required for several agents (Sophie,
MAIK, Moltbook) to share one server. Auth is a bearer TokenVerifier; each token
carries the caller's tenant/namespace, which the tools read (never an argument).

Phase 5b: server + the 2 most-duplicated tools. Phase 5c: + a declarative catalog
and 2 tools ported from axis-runtime's REGISTRY (cross-repo), proven in parallel.
Sophie/MAIK are NOT pointed at it yet — that's Wave C, behind a shadow canary.
"""
from __future__ import annotations

import os

from fastmcp import FastMCP

from .auth import build_verifier
from .catalog import register_catalog


def build_server() -> FastMCP:
    mcp = FastMCP("AxisSkillsServer", auth=build_verifier())
    # All shared tools come from the declarative catalog (catalog.py) — adding a tool
    # is one ToolSpec entry there, not boilerplate here.
    register_catalog(mcp)
    return mcp


mcp = build_server()


def main() -> None:
    host = os.environ.get("SKILLS_HOST", "127.0.0.1")
    port = int(os.environ.get("SKILLS_PORT", "8300"))
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    main()
