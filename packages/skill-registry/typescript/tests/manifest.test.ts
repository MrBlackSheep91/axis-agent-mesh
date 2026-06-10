import { describe, it, expect } from "vitest";
import {
  MANIFEST_VERSION,
  inferType,
  manifestVersion,
  parseSkillManifest,
  parseFrontmatter,
  validateManifest,
  type SkillManifest,
} from "../src/index.js";

const TOOL_MD = `---
name: t
description: tool skill
version: 2.1.0
type: tool
transport: { kind: mcp, server: s, tool: t }
---
body`;

const LEGACY_MD = `---
name: legacy
description: legacy skill
tools_exposed: [a, b]
allowed-tools: [Bash]
user-invocable: true
---
body`;

const DECL_MD = `---
name: d
description: declarative skill
---
body`;

describe("MANIFEST_VERSION", () => {
  it("is 1", () => expect(MANIFEST_VERSION).toBe(1));
});

describe("parseSkillManifest", () => {
  it("parses frontmatter into a manifest", () => {
    const m = parseSkillManifest(TOOL_MD);
    expect(m.name).toBe("t");
    expect(m.version).toBe("2.1.0");
    expect(m.transport).toEqual({ kind: "mcp", server: "s", tool: "t" });
  });

  it("normalizes the legacy `user-invocable` key to `user_invocable`", () => {
    const fm = parseFrontmatter(LEGACY_MD);
    expect(fm.user_invocable).toBe(true);
    expect("user-invocable" in fm).toBe(false);
  });
});

describe("inferType", () => {
  it("mcp transport → tool", () => {
    expect(inferType(parseSkillManifest(TOOL_MD))).toBe("tool");
  });
  it("tools_exposed → tool", () => {
    expect(inferType(parseSkillManifest(LEGACY_MD))).toBe("tool");
  });
  it("neither → declarative", () => {
    expect(inferType(parseSkillManifest(DECL_MD))).toBe("declarative");
  });
  it("explicit type wins", () => {
    expect(inferType({ name: "x", description: "y", type: "inprocess" } as SkillManifest)).toBe("inprocess");
  });
});

describe("manifestVersion", () => {
  it("uses the declared version", () => {
    expect(manifestVersion(parseSkillManifest(TOOL_MD))).toBe("2.1.0");
  });
  it("defaults to 0.1.0 when absent", () => {
    expect(manifestVersion(parseSkillManifest(DECL_MD))).toBe("0.1.0");
  });
});

describe("validateManifest", () => {
  it("accepts a valid manifest", () => {
    expect(validateManifest(parseSkillManifest(TOOL_MD)).valid).toBe(true);
  });
  it("tolerates legacy extra keys (additionalProperties:true)", () => {
    const r = validateManifest(parseSkillManifest(LEGACY_MD));
    expect(r.valid).toBe(true);
  });
  it("rejects a manifest missing name", () => {
    const r = validateManifest({ description: "no name" });
    expect(r.valid).toBe(false);
    expect(r.errors.length).toBeGreaterThan(0);
  });
  it("rejects a bad transport shape", () => {
    const r = validateManifest({ name: "x", description: "y", transport: { kind: "mcp" } });
    expect(r.valid).toBe(false);
  });
});
