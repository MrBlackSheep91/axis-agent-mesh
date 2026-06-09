/**
 * Fixture conformance — proves ROADMAP criterion 4: the 5 real axis agents
 * (MAIK, Sophie, Moltbook, Jaime, Lady) each express as a valid AgentDefinition.
 *
 * Reads every `*.agent.json` under fixtures/ and asserts:
 *   - loadAgentDefinition(text) does NOT throw (parse + version-gate + validate)
 *   - validateAgentDefinition(parsed) returns valid: true with no errors
 */
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  loadAgentDefinition,
  validateAgentDefinition,
} from "../src/index.js";

const fixturesDir = join(dirname(fileURLToPath(import.meta.url)), "fixtures");

const fixtureFiles = readdirSync(fixturesDir)
  .filter((f) => f.endsWith(".agent.json"))
  .sort();

const EXPECTED_AGENTS = ["jaime", "lady", "maik", "moltbook", "sophie"] as const;

describe("real-agent fixtures", () => {
  it("ships exactly the 5 expected agent fixtures", () => {
    const names = fixtureFiles.map((f) => f.replace(/\.agent\.json$/, "")).sort();
    expect(names).toEqual([...EXPECTED_AGENTS]);
  });

  it.each(fixtureFiles)("%s loads without throwing and validates true", (file) => {
    const text = readFileSync(join(fixturesDir, file), "utf8");

    // loadAgentDefinition does parse + version gate + schema validation; must not throw.
    const def = loadAgentDefinition(text);
    expect(def.version).toBe(1);
    expect(def.identity.fqid).toMatch(/^[a-z0-9-]+\/[a-z0-9-]+\/[a-z0-9-]+$/);

    // And the structural validator must independently report valid.
    const result = validateAgentDefinition(JSON.parse(text));
    expect(result.errors).toEqual([]);
    expect(result.valid).toBe(true);
  });
});
