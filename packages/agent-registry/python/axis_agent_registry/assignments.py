"""Role -> model id assignments.

Copied verbatim from /Users/eluru/invidia-chat-api/lib/model_registry.py.
The inline comments encode Maicol-validated pricing decisions from
2026-05-10 — preserve them; future role additions follow the same pattern
(default + override candidates documented inline).
"""
from __future__ import annotations


# Pricing decisions (2026-05-10 Maicol-validated):
#
# - Gemini 3.1 Pro descartado por costo (no en CATALOG).
# - GPT-5.4-mini default agentic_master: real cost observed ~$0.003/turn
#   (output 80-200 tokens en tool calls), 1.8s latency, 0 leaks in canary.
# - Kimi K2.5 (kimi-k2-0905): retenido en catalogo con leak_risk=high.
#   Defensive parser en agentic_orchestrator captura el leak. Usable via
#   env override solo para canary, NUNCA para produccion default.
# - Kimi K2.6: incluido — Maicol prioriza calidad sobre velocidad. 14s
#   latencia ok si la calidad gana. Usable como override por rol.
# - DeepSeek V4 Pro: incluido — opcion para tareas pesadas reasoning,
#   1M context, MoE eficiente. Untested aun en Iris voice.
#
# Para hacer A/B real entre estos: setear env per rol con
# AXIS_MODEL_OVERRIDE_<ROLE>=<model_id>  (or legacy INVIDIA_MODEL_OVERRIDE_<ROLE>)


DEFAULT_ASSIGNMENTS: dict[str, str] = {
    # The LLM that drives the agentic tool-calling loop (most expensive turn-wise).
    # Default = GPT-5.4-mini (fastest, no leaks, cheap in real output).
    # Override candidates for canary:
    #   AXIS_MODEL_OVERRIDE_AGENTIC_MASTER=moonshotai/kimi-k2.6
    #   AXIS_MODEL_OVERRIDE_AGENTIC_MASTER=deepseek/deepseek-v4-pro
    #   AXIS_MODEL_OVERRIDE_AGENTIC_MASTER=google/gemini-3.1-flash-lite
    "agentic_master": "openai/gpt-5.4-mini",
    # Critic pass — short eval call after agentic produces a draft.
    "critic": "openai/gpt-5.4-nano",
    # Intent classifier — replaces 8+ regex detectors with LLM (Sprint 2).
    "intent_analyzer": "openai/gpt-5.4-nano",
    # Confirm-problem reorganization (deterministic-path final call).
    "confirm_problem": "openai/gpt-5.4-mini",
    # Greet first-turn paraphrase.
    "greet": "openai/gpt-5.4-nano",
    # General-purpose cheap default for AXIS consumers (axis-cc, hybrid-crm).
    # Decoupled from Sophie's agentic_master (D1/D6 - cost: $1.50/M vs $4.50/M).
    # NOT used by Sophie - her agentic_master stays openai/gpt-5.4-mini.
    "general_default": "google/gemini-3.1-flash-lite",
    # Multimodal image analysis (must support vision).
    "image_analyzer": "google/gemini-3.1-flash-lite",
    # Help Center match summarization.
    "search_help_center": "openai/gpt-5.4-nano",
    # Customer-context fetch summarizer.
    "cross_conv_summary": "openai/gpt-5.4-nano",
    # Resolution-tracker LLM confirm (when used).
    "resolution_tracker_llm": "openai/gpt-5.4-nano",
    # Acknowledge-escalation paraphrase.
    "acknowledge_escalation": "openai/gpt-5.4-mini",
    # F269 shift report — narrates pre-computed 4h stats into Spanish
    # prose. Internal team-facing, 6 calls/day, short output -> cheapest
    # proven sibling. Never customer-facing, no tools.
    "shift_report": "openai/gpt-5.4-nano",
}
