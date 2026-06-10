import { describe, it, expect } from "vitest";
import { fileURLToPath } from "node:url";
import { loadSkill } from "../src/index.js";

const FIXTURES = fileURLToPath(new URL("./fixtures", import.meta.url));
const roots = [FIXTURES];

describe("loadSkill", () => {
  it("resolves a tool skill, inferring type from transport", () => {
    const s = loadSkill("sample-tool", { roots });
    expect(s.type).toBe("tool");
    expect(s.version).toBe("1.0.0");
    expect(s.manifest.name).toBe("sample-tool");
    expect(s.path).toContain("sample-tool/SKILL.md");
  });

  it("resolves a declarative skill, defaulting the version", () => {
    const s = loadSkill("sample-declarative", { roots });
    expect(s.type).toBe("declarative");
    expect(s.version).toBe("0.1.0");
  });

  it("parses a legacy SKILL.md (tools_exposed → tool, legacy keys tolerated)", () => {
    const s = loadSkill("legacy-skill", { roots });
    expect(s.type).toBe("tool");
    expect(s.manifest.user_invocable).toBe(true);
    expect(s.manifest.tools_exposed).toEqual(["legacy_foo", "legacy_bar"]);
  });

  it("throws on a skill that doesn't exist", () => {
    expect(() => loadSkill("nope", { roots })).toThrow(/not found/);
  });

  it("throws on a version mismatch", () => {
    expect(() => loadSkill("sample-tool", { roots, version: "9.9.9" })).toThrow(/version/);
  });

  it("throws when no roots are given", () => {
    expect(() => loadSkill("sample-tool", { roots: [] })).toThrow(/root/);
  });
});
