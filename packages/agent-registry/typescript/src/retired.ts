// Known-retired model IDs that must NEVER appear in production execution paths.
// Hand-maintained TS mirror of axis_agent_registry/catalog.py RETIRED_MODELS
// (keep both in sync — small static list). Sourced by bin/audit-models.ts
// (REG-03 CI drift gate): it greps prod paths for these substrings and exits
// non-zero on any hit. Substrings (not full IDs) so every provider-prefixed
// form is caught (openai/, openai:, bare, etc.).
export const RETIRED_MODELS: readonly string[] = [
  "gemini-2.0-flash", // google/gemini-2.0-flash-001 etc. - retired, replaced by gemini-3.1-flash-lite
  "gpt-4o-mini", // openai/gpt-4o-mini, openai:gpt-4o-mini - retired in agent paths
  "claude-3-5-sonnet", // legacy hybrid-crm agent_graph hardcode
  "grok-4.1-fast", // x-ai/grok-4.1-fast - HTTP 404 from OpenRouter (2026-05-22)
  "grok-4-fast", // x-ai/grok-4-fast - deprecated same incident
];
