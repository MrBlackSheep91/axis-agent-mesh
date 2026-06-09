/**
 * Unit tests for the @axis/agent-def public API:
 *   - validateAgentDefinition (structural validation against the JSON Schema)
 *   - loadAgentDefinition     (parse + version-gate + validate, throws on invalid)
 *   - SCHEMA_VERSION          (the format version loaders accept)
 *
 * These test the CONTRACT, not the fixtures. A minimal hand-built valid object is
 * the baseline; each case mutates one thing to assert the validator/loader reacts.
 */
import { describe, it, expect } from "vitest";
import {
  validateAgentDefinition,
  loadAgentDefinition,
  SCHEMA_VERSION,
  type AgentDefinition,
} from "../src/index.js";

/** Smallest object that satisfies every `required` in the schema. */
function minimalValid(): AgentDefinition {
  return {
    version: 1,
    identity: {
      id: "00000000-0000-4000-8000-000000000000",
      fqid: "acme/main/bot",
      name: "Bot",
      tenant: { customer: "acme", org: "main" },
      version: 1,
    },
    goal: {
      objective: "Do the thing well.",
      success_criteria: ["The thing is done."],
    },
    context_scope: {
      memory_namespace: "customer/acme/org/main/agent/bot",
      knowledge_sources: [],
    },
    skills: [],
    model_routing: {
      default: "general_default",
      fallback_chain: [],
    },
    guardrails: [],
    kpis: [],
    runtime: {
      deployment_target: "axis-runtime",
      trigger: [{ type: "manual" }],
      governance: { confirmation_gate: "disabled" },
      observability: { langfuse_project: "axis-cc", tags: [] },
    },
  };
}

describe("SCHEMA_VERSION", () => {
  it("is the current format version (1)", () => {
    expect(SCHEMA_VERSION).toBe(1);
  });
});

describe("validateAgentDefinition", () => {
  it("accepts a minimal valid definition", () => {
    const result = validateAgentDefinition(minimalValid());
    expect(result.valid).toBe(true);
    expect(result.errors).toEqual([]);
  });

  it("rejects a missing required field with non-empty errors", () => {
    const obj = minimalValid() as Partial<AgentDefinition>;
    delete obj.goal;
    const result = validateAgentDefinition(obj);
    expect(result.valid).toBe(false);
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it("rejects unknown extra properties (additionalProperties: false)", () => {
    const obj = { ...minimalValid(), surprise: "nope" } as unknown;
    const result = validateAgentDefinition(obj);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => /additional/i.test(e))).toBe(true);
  });

  it("rejects a malformed fqid (pattern violation)", () => {
    const obj = minimalValid();
    obj.identity.fqid = "AcmeMainBot"; // no slashes, uppercase
    const result = validateAgentDefinition(obj);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.includes("/identity/fqid"))).toBe(true);
  });

  it("rejects a non-const version value (structural check)", () => {
    const obj = { ...minimalValid(), version: 2 };
    const result = validateAgentDefinition(obj);
    expect(result.valid).toBe(false);
  });
});

describe("loadAgentDefinition", () => {
  it("returns a typed AgentDefinition for a valid JSON string", () => {
    const def = loadAgentDefinition(JSON.stringify(minimalValid()));
    expect(def.identity.fqid).toBe("acme/main/bot");
    expect(def.version).toBe(SCHEMA_VERSION);
  });

  it("accepts an already-parsed object", () => {
    const def = loadAgentDefinition(minimalValid());
    expect(def.identity.name).toBe("Bot");
  });

  it("throws on an unknown version (2)", () => {
    const obj = { ...minimalValid(), version: 2 };
    expect(() => loadAgentDefinition(obj)).toThrow(/version 2/);
  });

  it("throws on a missing/non-numeric version", () => {
    const obj = minimalValid() as Partial<AgentDefinition>;
    delete obj.version;
    expect(() => loadAgentDefinition(obj as object)).toThrow(/version/i);
  });

  it("throws on invalid JSON text", () => {
    expect(() => loadAgentDefinition("{ not json ")).toThrow(/invalid JSON/i);
  });

  it("throws on a structurally invalid (but version-1) object", () => {
    const obj = minimalValid() as Partial<AgentDefinition>;
    delete obj.runtime;
    expect(() => loadAgentDefinition(obj as object)).toThrow(/schema validation failed/i);
  });
});
