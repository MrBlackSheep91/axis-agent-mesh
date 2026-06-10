"""Authentication + tenant isolation for the AXIS Skills MCP server.

The security model (from 05-SKILL-CONTRACT-SPEC §6, MCP security research):
each agent gets its own bearer token; the token maps to a PRINCIPAL
(tenant + memory namespace). Tools derive the tenant/namespace **from the token**,
never from a tool argument — so a caller cannot reach another tenant's data by
passing a different `tenant_id` (confused-deputy / cross-tenant defense).

For Phase 5b (local MVP) we use FastMCP's StaticTokenVerifier with tokens loaded
from the `SKILLS_TOKENS` env var (JSON). Production swaps this for a JWTVerifier
against a real issuer without changing the tool code (tools only read claims).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.dependencies import get_access_token


@dataclass(frozen=True)
class Principal:
    """The validated identity behind a request, derived from its token's claims."""
    agent: str
    tenant: str
    namespace: str


# Dev-only fallback tokens. NEVER use in production — overridden by SKILLS_TOKENS.
_DEV_TOKENS = {
    "dev-sophie": {"agent": "sophie", "tenant": "invidia", "namespace": "customer/invidia/org/main/agent/sophie"},
    "dev-maik": {"agent": "maik", "tenant": "maicol", "namespace": "customer/maicol/org/personal/agent/maik"},
}


def _load_token_map() -> dict[str, dict]:
    """tokens: { "<bearer>": {agent, tenant, namespace} }. From SKILLS_TOKENS (JSON) or dev fallback."""
    raw = os.environ.get("SKILLS_TOKENS", "").strip()
    if not raw:
        return _DEV_TOKENS
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("SKILLS_TOKENS must be a JSON object {token: {agent, tenant, namespace}}")
        return parsed
    except Exception as e:
        raise RuntimeError(f"skills-server: invalid SKILLS_TOKENS — {e}") from e


def build_verifier() -> StaticTokenVerifier:
    """Build the StaticTokenVerifier: each token carries its principal in `claims`."""
    token_map = _load_token_map()
    # StaticTokenVerifier copies the whole per-token dict into AccessToken.claims,
    # so principal fields go at the top level (NOT nested under a "claims" key).
    tokens = {
        bearer: {
            "client_id": p["agent"],
            "scopes": [f"tenant:{p['tenant']}"],
            "agent": p["agent"],
            "tenant": p["tenant"],
            "namespace": p["namespace"],
        }
        for bearer, p in token_map.items()
    }
    return StaticTokenVerifier(tokens=tokens)


def current_principal() -> Principal:
    """Resolve the Principal for the current request from its validated token.

    Raises PermissionError if there is no authenticated token (defense in depth —
    the transport already rejects unauthenticated requests, but tools assert too).
    """
    token = get_access_token()
    if token is None:
        raise PermissionError("skills-server: no authenticated token on this request")
    claims = getattr(token, "claims", None) or {}
    agent = claims.get("agent")
    tenant = claims.get("tenant")
    namespace = claims.get("namespace")
    if not (agent and tenant and namespace):
        raise PermissionError("skills-server: token is missing agent/tenant/namespace claims")
    return Principal(agent=agent, tenant=tenant, namespace=namespace)
