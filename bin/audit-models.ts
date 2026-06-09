#!/usr/bin/env tsx
/**
 * audit-models — REG-03 drift gate (Wave A).
 *
 * Greps a repo's source for retired model IDs (axis_agent_registry RETIRED_MODELS)
 * and exits non-zero on any hit, so CI fails before a retired model reaches prod.
 *
 * Usage:
 *   npx tsx bin/audit-models.ts [--root <dir>] [path ...]
 *     --root <dir>   repo root to scan (default: cwd)
 *     [path ...]     optional explicit files/dirs (relative to root); default: scan root
 *
 * Exit: 0 = clean, 1 = retired model id found, 2 = usage/IO error.
 *
 * Source of truth for the retired list: packages/agent-registry RETIRED_MODELS
 * (Python catalog.py + TS retired.ts). This script imports the TS copy.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, basename, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";
import { RETIRED_MODELS } from "../packages/agent-registry/typescript/src/retired.js";

const HERE = dirname(fileURLToPath(import.meta.url));

const SCAN_EXT = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".prisma"]);
const SKIP_DIRS = new Set([
  "node_modules", ".git", "dist", "build", ".next", ".turbo", "coverage",
  "vendor", ".planning", "__pycache__", ".venv", "venv", "migrations",
  "tests", "__tests__", "test", "e2e", ".cache",
  ".claude", // git worktrees + agent scratch carry their own copies; scanning them double-counts
]);
// Files that legitimately CONTAIN retired ids as data/definitions, not as usage.
function isExempt(path: string): boolean {
  const b = basename(path);
  if (b === "audit-models.ts") return true;
  if (b.endsWith(".test.ts") || b.endsWith(".test.tsx") || b.endsWith(".spec.ts")) return true;
  if (b === "package-lock.json" || b.endsWith(".lock")) return true;
  // the registry's own retired-list definition files
  if (path.includes("agent-registry") && (b === "retired.ts" || b === "retired.js" || b === "catalog.py" || b === "catalog.ts")) return true;
  return false;
}

// Heuristic: is the retired substring on a comment line (doc/history reference,
// not a live model selection)? Skip those to avoid false positives.
function isCommentHit(line: string, idx: number): boolean {
  // Explicit per-line allowlist: `// audit-models-ignore` (e.g. cost-tracking literals).
  if (line.includes("audit-models-ignore")) return true;
  const trimmed = line.trimStart();
  if (trimmed.startsWith("//") || trimmed.startsWith("*") || trimmed.startsWith("#") || trimmed.startsWith("/*")) return true;
  const before = line.slice(0, idx);
  if (before.includes("//") || before.includes("#")) return true;
  return false;
}

function* walk(dir: string): Generator<string> {
  let entries;
  try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    const full = join(dir, e.name);
    if (e.isDirectory()) {
      if (SKIP_DIRS.has(e.name)) continue;
      yield* walk(full);
    } else if (e.isFile() && SCAN_EXT.has(extname(e.name))) {
      yield full;
    }
  }
}

function main(): number {
  const args = process.argv.slice(2);
  let root = process.cwd();
  const targets: string[] = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--root") { root = args[++i]; }
    else if (args[i] === "-h" || args[i] === "--help") {
      console.log("Usage: tsx bin/audit-models.ts [--root <dir>] [path ...]");
      return 0;
    } else { targets.push(args[i]); }
  }

  const scanRoots = targets.length ? targets.map((t) => join(root, t)) : [root];
  const hits: { file: string; line: number; col: number; id: string; text: string }[] = [];

  for (const sr of scanRoots) {
    let files: string[] = [];
    try {
      if (statSync(sr).isFile()) files = [sr];
      else files = [...walk(sr)];
    } catch { continue; }
    for (const file of files) {
      if (isExempt(file)) continue;
      let content: string;
      try { content = readFileSync(file, "utf8"); } catch { continue; }
      // Whole-file allowlist: a `audit-models-ignore-file` marker near the top
      // (e.g. pricing/cost tables that reference historical model IDs by design).
      if (content.slice(0, 600).includes("audit-models-ignore-file")) continue;
      const lines = content.split("\n");
      for (let li = 0; li < lines.length; li++) {
        const line = lines[li];
        for (const id of RETIRED_MODELS) {
          const idx = line.indexOf(id);
          if (idx === -1) continue;
          if (isCommentHit(line, idx)) continue;
          hits.push({ file: relative(root, file), line: li + 1, col: idx + 1, id, text: line.trim().slice(0, 120) });
        }
      }
    }
  }

  if (hits.length === 0) {
    console.log(`audit-models: OK — no retired model IDs in ${relative(process.cwd(), root) || "."} (${RETIRED_MODELS.length} patterns checked)`);
    return 0;
  }
  console.error(`audit-models: FAIL — ${hits.length} retired model reference(s) found:\n`);
  for (const h of hits) console.error(`  ${h.file}:${h.line}:${h.col}  [${h.id}]  ${h.text}`);
  console.error(`\nReplace with a registry call: DEFAULT_MODEL_FOR('<role>') / get_model_for('<role>') from @axis/agent-registry.`);
  return 1;
}

process.exit(main());
