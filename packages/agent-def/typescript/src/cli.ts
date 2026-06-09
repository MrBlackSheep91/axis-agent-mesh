#!/usr/bin/env node
/**
 * axis-mesh — CLI for @axis/agent-def.
 *
 *   axis-mesh validate <path> [<path> ...]
 *     Validate one or more `.agent.json` files against the canonical schema +
 *     version gate. Exit 0 if all valid, 1 if any fails, 2 on usage/IO error.
 *
 * Note: structural + version validation only. Semantic checks (skill existence,
 * model-routing role resolution) land with the skill registry in Phase 5.
 */
import { readFileSync, statSync } from "node:fs";
import { loadAgentDefinition } from "./index.js";

function usage(): number {
  console.error("Usage: axis-mesh validate <path> [<path> ...]");
  return 2;
}

function validateFile(path: string): { ok: boolean; msg: string } {
  let text: string;
  try {
    if (!statSync(path).isFile()) return { ok: false, msg: `${path}: not a file` };
    text = readFileSync(path, "utf8");
  } catch (e) {
    return { ok: false, msg: `${path}: ${(e as Error).message}` };
  }
  try {
    const def = loadAgentDefinition(text);
    return { ok: true, msg: `${path}: OK (${def.identity.fqid}, v${def.identity.version})` };
  } catch (e) {
    return { ok: false, msg: `${path}: FAIL\n  ${(e as Error).message.replace(/\n/g, "\n  ")}` };
  }
}

function main(argv: string[]): number {
  const [cmd, ...rest] = argv;
  if (cmd !== "validate") return usage();
  if (rest.length === 0) return usage();

  let allOk = true;
  for (const path of rest) {
    const { ok, msg } = validateFile(path);
    if (ok) console.log(msg);
    else {
      console.error(msg);
      allOk = false;
    }
  }
  return allOk ? 0 : 1;
}

process.exit(main(process.argv.slice(2)));
