/**
 * Cross-language Python/TS parity gate — REQUIREMENT REG-01 success criterion 4.
 *
 * Loads typescript/tests/snapshot-fixtures/python-pairs.json (regenerated
 * by bin/sync-twin.ts from the Python source-of-truth) and asserts that TS
 * getModelFor returns the same model id Python's get_model_for did for
 * EVERY pair. ALL 10 MUST PASS.
 *
 * If this test starts failing, either:
 *   (a) The Python defaults shifted but the fixture wasn't regenerated
 *       -> run `npm run sync-twin` from the repo root.
 *   (b) The TS twin's resolution logic diverged from Python -> fix the
 *       bug in registry.ts; the fixture is the source of truth.
 */
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getModelFor } from "../src/index.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURE_PATH = resolve(__dirname, "snapshot-fixtures/python-pairs.json");

interface SnapshotPair {
  role: string;
  env_overrides: Record<string, string>;
  expected_model_id: string;
}

const PAIRS: SnapshotPair[] = JSON.parse(readFileSync(FIXTURE_PATH, "utf8"));

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("snapshot parity — TS twin matches Python get_model_for for all 10 pairs", () => {
  it("fixture has exactly 10 pairs", () => {
    expect(PAIRS.length).toBe(10);
  });

  // Single combined test so failure of any pair fails the whole suite
  // with a precise diagnostic line per pair (per acceptance criteria).
  it("Test 15: snapshot pair[0..9] all match Python expected_model_id", () => {
    const failures: string[] = [];

    PAIRS.forEach((pair, idx) => {
      // Apply env_overrides as process.env stubs — this is the SHAPE the
      // TS twin's process.env-iteration layer consumes, matching how
      // Sophie / axis-cc operators set these vars in Railway.
      vi.unstubAllEnvs(); // belt-and-suspenders per-pair cleanup
      for (const [key, value] of Object.entries(pair.env_overrides)) {
        vi.stubEnv(key, value);
      }
      const actual = getModelFor(pair.role);
      if (actual !== pair.expected_model_id) {
        failures.push(
          `pair[${idx}] role=${pair.role} env_overrides=${JSON.stringify(pair.env_overrides)} ` +
            `expected=${pair.expected_model_id} actual=${actual}`,
        );
      } else {
        // eslint-disable-next-line no-console
        console.log(
          `snapshot pair[${idx}] role=${pair.role} expected=${pair.expected_model_id} OK`,
        );
      }
    });

    if (failures.length > 0) {
      throw new Error(
        `Snapshot parity failed for ${failures.length}/10 pairs:\n  ${failures.join("\n  ")}`,
      );
    }
  });
});
