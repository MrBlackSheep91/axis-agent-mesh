"""Unit tests for the AXIS Skills MCP server (Phase 5b).

Covers auth (token → principal claims), tool dry-run / graceful degradation, and
the tenant-from-token invariant. The full HTTP+client smoke (list_tools, real auth
rejection, cross-tenant isolation) is verified in the README's run recipe.
"""
import pytest

from axis_skills_server import auth, tools


@pytest.mark.asyncio
async def test_verify_token_exposes_principal_claims():
    v = auth.build_verifier()
    tok = await v.verify_token("dev-sophie")
    assert tok is not None
    assert tok.claims["agent"] == "sophie"
    assert tok.claims["tenant"] == "invidia"
    assert tok.claims["namespace"].startswith("customer/invidia/")


@pytest.mark.asyncio
async def test_verify_rejects_unknown_token():
    v = auth.build_verifier()
    assert await v.verify_token("not-a-token") is None


def test_load_token_map_dev_fallback(monkeypatch):
    monkeypatch.delenv("SKILLS_TOKENS", raising=False)
    m = auth._load_token_map()
    assert "dev-sophie" in m and m["dev-sophie"]["tenant"] == "invidia"


def test_load_token_map_from_env(monkeypatch):
    monkeypatch.setenv("SKILLS_TOKENS", '{"t1": {"agent": "a", "tenant": "x", "namespace": "n"}}')
    m = auth._load_token_map()
    assert m["t1"]["tenant"] == "x"


def test_load_token_map_invalid_env_raises(monkeypatch):
    monkeypatch.setenv("SKILLS_TOKENS", "not json")
    with pytest.raises(RuntimeError):
        auth._load_token_map()


@pytest.mark.asyncio
async def test_capture_dry_run_derives_agent_from_token(monkeypatch):
    monkeypatch.setenv("SKILLS_DRY_RUN", "1")
    monkeypatch.setattr(tools, "current_principal", lambda: auth.Principal("sophie", "invidia", "ns"))
    r = await tools.capture("hello", "idea", project="invidia")
    assert r["dry_run"] is True
    assert r["by"] == "sophie"  # from token, not an argument
    assert r["body"] == {"text": "hello", "type": "idea", "project": "invidia"}


@pytest.mark.asyncio
async def test_search_graceful_when_unconfigured(monkeypatch):
    monkeypatch.delenv("AXIS_MEMORY_URL", raising=False)
    monkeypatch.setattr(tools, "current_principal", lambda: auth.Principal("sophie", "invidia", "ns"))
    assert await tools.axis_memory_search("q") == []


@pytest.mark.asyncio
async def test_search_uses_namespace_from_token(monkeypatch):
    """The search namespace must come from the principal, never from an argument."""
    captured = {}

    class _Resp:
        status_code = 200
        def json(self):
            return {"results": []}

    class _Client:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, headers=None, json=None):
            captured["namespace"] = json["namespace"]
            return _Resp()

    monkeypatch.setenv("AXIS_MEMORY_URL", "http://memory.local")
    monkeypatch.setattr(tools, "current_principal", lambda: auth.Principal("sophie", "invidia", "customer/invidia/org/main/agent/sophie"))
    monkeypatch.setattr(tools.httpx, "AsyncClient", _Client)
    await tools.axis_memory_search("q")
    assert captured["namespace"] == "customer/invidia/org/main/agent/sophie"
