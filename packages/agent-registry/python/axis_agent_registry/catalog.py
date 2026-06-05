"""Model catalog — every LLM that the axis ecosystem is ALLOWED to invoke.

Copied verbatim from /Users/eluru/invidia-chat-api/lib/model_registry.py
(2026-05-10 origin, Maicol-validated; updated through 2026-05-27).

Mutating an entry here = changing what production can call. Add new models
to CATALOG before any assignment can reference them. Removing an entry is
a hard break and requires a Wave A audit run (bin/audit-models.ts, Plan 03).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    id: str
    in_price_per_m: float    # USD per 1M input tokens
    out_price_per_m: float   # USD per 1M output tokens
    ctx_tokens: int
    supports_tools: bool
    released: str            # YYYY-MM-DD
    family: str              # openai, anthropic, deepseek, kimi, google, qwen
    notes: str = ""
    leak_risk: str = "low"   # low | medium | high  (tool-format leak in content)


# ---------------------------------------------------------------------------
# CATALOG — every model the bot is ALLOWED to invoke must appear here.
# ---------------------------------------------------------------------------

CATALOG: dict[str, ModelSpec] = {
    "openai/gpt-5.4-mini": ModelSpec(
        id="openai/gpt-5.4-mini",
        in_price_per_m=0.75, out_price_per_m=4.50,
        ctx_tokens=400_000, supports_tools=True, family="openai",
        released="2026-03-17",
        notes="Currently default for supervisor chat. Tool calling reliable. Output usually short -> real cost low.",
    ),
    "openai/gpt-5.4-nano": ModelSpec(
        id="openai/gpt-5.4-nano",
        in_price_per_m=0.20, out_price_per_m=1.25,
        ctx_tokens=400_000, supports_tools=True, family="openai",
        released="2026-03-17",
        notes="Cheaper sibling of gpt-5.4-mini. Useful for intent_analyzer / critic.",
    ),
    "anthropic/claude-4.5-haiku": ModelSpec(
        id="anthropic/claude-4.5-haiku",
        in_price_per_m=1.00, out_price_per_m=5.00,
        ctx_tokens=200_000, supports_tools=True, family="anthropic",
        released="2025-10-15",
        notes="Currently used by critic (langfuse default route). Expensive vs alternatives.",
    ),
    "deepseek/deepseek-v4-flash": ModelSpec(
        id="deepseek/deepseek-v4-flash",
        in_price_per_m=0.14, out_price_per_m=0.28,
        ctx_tokens=1_048_576, supports_tools=True, family="deepseek",
        released="2026-04-23",
        notes="Cheapest credible option. 1M context. Untested for Iris voice yet.",
    ),
    "deepseek/deepseek-v4-pro": ModelSpec(
        id="deepseek/deepseek-v4-pro",
        in_price_per_m=0.43, out_price_per_m=0.87,
        ctx_tokens=1_048_576, supports_tools=True, family="deepseek",
        released="2026-04-23",
        notes="Mid-tier DeepSeek. Reasoning toggle.",
    ),
    "moonshotai/kimi-k2-0905": ModelSpec(
        id="moonshotai/kimi-k2-0905",
        in_price_per_m=0.40, out_price_per_m=2.00,
        ctx_tokens=262_144, supports_tools=True, family="kimi",
        released="2025-09-04",
        notes=("Confirmed tool-format leak under large prompts "
               "(SOUL+13 tools+history). Emits raw "
               "'send_message_to_customer:N{...}' as content "
               "intermittently. 2026-05-10 incident."),
        leak_risk="high",
    ),
    "moonshotai/kimi-k2.6": ModelSpec(
        id="moonshotai/kimi-k2.6",
        in_price_per_m=0.75, out_price_per_m=3.50,
        ctx_tokens=262_144, supports_tools=True, family="kimi",
        released="2026-04-20",
        notes="Newer Kimi. Tool calling clean in tests but ~14s latency.",
    ),
    "google/gemini-3.1-flash-lite": ModelSpec(
        id="google/gemini-3.1-flash-lite",
        in_price_per_m=0.25, out_price_per_m=1.50,
        ctx_tokens=1_048_576, supports_tools=True, family="google",
        released="2026-05-07",
        notes="Multimodal (vision). Clean tools in test. Good for image_analyzer.",
    ),
    "qwen/qwen3.6-flash": ModelSpec(
        id="qwen/qwen3.6-flash",
        in_price_per_m=0.25, out_price_per_m=1.50,
        ctx_tokens=1_000_000, supports_tools=True, family="qwen",
        released="2026-04-26",
        notes="Alibaba. Strong Spanish. Untested for Iris.",
    ),
}
