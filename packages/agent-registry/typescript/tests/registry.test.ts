/**
 * Unit tests for the TS twin registry. 14 tests; the 15th (snapshot
 * parity vs Python) lives in snapshot.test.ts.
 *
 * Convention: every test that touches env vars uses vi.stubEnv +
 * vi.unstubAllEnvs in afterEach. setHybridCrmOverrideLookup is reset
 * to null in afterEach so module-level hook leakage is impossible.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  CATALOG,
  DEFAULT_ASSIGNMENTS,
  DEFAULT_MODEL_FOR,
  OVERRIDE_PREFIXES,
  allAssignments,
  getModelFor,
  getSpec,
  setHybridCrmOverrideLookup,
} from "../src/index.js";

afterEach(() => {
  vi.unstubAllEnvs();
  setHybridCrmOverrideLookup(null);
  vi.restoreAllMocks();
});

describe("getModelFor — defaults", () => {
  it("Test 1: default-path resolves agentic_master to openai/gpt-5.4-mini", () => {
    expect(getModelFor("agentic_master")).toBe("openai/gpt-5.4-mini");
  });

  it("Test 2: unknown role throws Error with role name in message", () => {
    expect(() => getModelFor("not_a_role")).toThrowError(/not_a_role/);
  });
});

describe("getModelFor — env override resolution", () => {
  it("Test 3: legacy INVIDIA prefix override honored", () => {
    vi.stubEnv("INVIDIA_MODEL_OVERRIDE_AGENTIC_MASTER", "moonshotai/kimi-k2.6");
    expect(getModelFor("agentic_master")).toBe("moonshotai/kimi-k2.6");
  });

  it("Test 4: canonical AXIS prefix override honored", () => {
    vi.stubEnv("AXIS_MODEL_OVERRIDE_AGENTIC_MASTER", "deepseek/deepseek-v4-pro");
    expect(getModelFor("agentic_master")).toBe("deepseek/deepseek-v4-pro");
  });

  it("Test 5: AXIS prefix wins on conflict with INVIDIA", () => {
    vi.stubEnv("AXIS_MODEL_OVERRIDE_AGENTIC_MASTER", "deepseek/deepseek-v4-pro");
    vi.stubEnv("INVIDIA_MODEL_OVERRIDE_AGENTIC_MASTER", "moonshotai/kimi-k2.6");
    expect(getModelFor("agentic_master")).toBe("deepseek/deepseek-v4-pro");
  });

  it("Test 6: explicit envOverrides option wins over process.env", () => {
    vi.stubEnv("AXIS_MODEL_OVERRIDE_AGENTIC_MASTER", "deepseek/deepseek-v4-pro");
    vi.stubEnv("INVIDIA_MODEL_OVERRIDE_AGENTIC_MASTER", "moonshotai/kimi-k2.6");
    expect(
      getModelFor("agentic_master", {
        envOverrides: { AGENTIC_MASTER: "openai/gpt-5.4-nano" },
      }),
    ).toBe("openai/gpt-5.4-nano");
  });

  it("Test 7: unknown override id warns and falls through to default", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.stubEnv("AXIS_MODEL_OVERRIDE_AGENTIC_MASTER", "nope/not-a-model");
    expect(getModelFor("agentic_master")).toBe("openai/gpt-5.4-mini");
    expect(warnSpy).toHaveBeenCalled();
    expect(warnSpy.mock.calls.flat().join(" ")).toMatch(/nope\/not-a-model/);
  });
});

describe("getModelFor — hybridCrmLookup", () => {
  it("Test 8: per-call hybridCrmLookup honored", () => {
    expect(
      getModelFor("agentic_master", {
        hybridCrmLookup: () => "qwen/qwen3.6-flash",
      }),
    ).toBe("qwen/qwen3.6-flash");
  });

  it("Test 9: setHybridCrmOverrideLookup wires + clears module-level hook", () => {
    setHybridCrmOverrideLookup(() => "moonshotai/kimi-k2.6");
    expect(getModelFor("agentic_master")).toBe("moonshotai/kimi-k2.6");
    setHybridCrmOverrideLookup(null);
    expect(getModelFor("agentic_master")).toBe("openai/gpt-5.4-mini");
  });

  it("Test 9b: hybrid-crm lookup that throws is caught and falls through", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    setHybridCrmOverrideLookup(() => {
      throw new Error("simulated CRM outage");
    });
    expect(getModelFor("agentic_master")).toBe("openai/gpt-5.4-mini");
    expect(warnSpy).toHaveBeenCalled();
  });
});

describe("public surface invariants", () => {
  it("Test 10: OVERRIDE_PREFIXES is exported in priority order", () => {
    expect(OVERRIDE_PREFIXES[0]).toBe("AXIS_MODEL_OVERRIDE_");
    expect(OVERRIDE_PREFIXES[1]).toBe("INVIDIA_MODEL_OVERRIDE_");
    expect(OVERRIDE_PREFIXES.length).toBe(2);
  });

  it("Test 11: DEFAULT_MODEL_FOR is an alias of getModelFor (same return)", () => {
    expect(DEFAULT_MODEL_FOR).toBe(getModelFor);
    expect(DEFAULT_MODEL_FOR("agentic_master")).toBe(getModelFor("agentic_master"));
  });

  it("Test 12: getSpec returns ModelSpec or undefined", () => {
    const spec = getSpec("openai/gpt-5.4-mini");
    expect(spec).toBeDefined();
    expect(spec!.id).toBe("openai/gpt-5.4-mini");
    expect(spec!.family).toBe("openai");
    expect(getSpec("nope/not-a-model")).toBeUndefined();
  });

  it("Test 13: allAssignments returns 12 roles with fromOverride flag", () => {
    const dump = allAssignments();
    expect(Object.keys(dump).length).toBe(12);
    // No env set in this test -> fromOverride is false everywhere
    for (const [role, entry] of Object.entries(dump)) {
      expect(entry.modelId).toBe(DEFAULT_ASSIGNMENTS[role]);
      expect(entry.fromOverride).toBe(false);
      expect(entry.inPricePerM).not.toBeNull();
    }
  });

  it("Test 13b: allAssignments flips fromOverride=true when AXIS env set", () => {
    vi.stubEnv("AXIS_MODEL_OVERRIDE_AGENTIC_MASTER", "deepseek/deepseek-v4-pro");
    const dump = allAssignments();
    expect(dump.agentic_master.fromOverride).toBe(true);
    expect(dump.agentic_master.modelId).toBe("deepseek/deepseek-v4-pro");
    expect(dump.critic.fromOverride).toBe(false);
  });

  it("Test 14: public surface importable from index", () => {
    // Smoke check: imports compiled at top of file. Confirm runtime
    // identity / shape so a missing re-export fails this test fast.
    expect(typeof getModelFor).toBe("function");
    expect(typeof getSpec).toBe("function");
    expect(typeof allAssignments).toBe("function");
    expect(typeof setHybridCrmOverrideLookup).toBe("function");
    expect(typeof DEFAULT_MODEL_FOR).toBe("function");
    expect(Array.isArray(OVERRIDE_PREFIXES)).toBe(true);
    expect(typeof CATALOG).toBe("object");
    expect(typeof DEFAULT_ASSIGNMENTS).toBe("object");
    expect(Object.keys(CATALOG).length).toBe(9);
    expect(Object.keys(DEFAULT_ASSIGNMENTS).length).toBe(12);
  });
});

describe("invariants — catalog/assignments shape", () => {
  it("every assignment maps to a registered model", () => {
    for (const [role, modelId] of Object.entries(DEFAULT_ASSIGNMENTS)) {
      expect(modelId in CATALOG, `role=${role} -> ${modelId} not in CATALOG`).toBe(true);
    }
  });
});
