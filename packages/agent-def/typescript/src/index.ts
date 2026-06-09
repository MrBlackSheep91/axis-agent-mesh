/**
 * @axis/agent-def — canonical AgentDefinition schema + validator.
 *
 * Public API:
 *   AgentDefinition (+ sub-types)   the canonical TS shape
 *   SCHEMA_VERSION                  current format version (loaders reject others)
 *   getSchema()                     the JSON Schema object (single source: the .json file)
 *   validateAgentDefinition(obj)    structural validation -> { valid, errors }
 *   loadAgentDefinition(text|obj)   validate + version-check -> typed AgentDefinition (throws on invalid)
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { Ajv2020, type ValidateFunction } from "ajv/dist/2020.js";

export * from "./agent-definition.js";
import { SCHEMA_VERSION, type AgentDefinition } from "./agent-definition.js";

let _schema: object | null = null;
let _validate: ValidateFunction | null = null;

/** The JSON Schema object. Read once from the package's `.json` (single source of truth). */
export function getSchema(): object {
  if (_schema) return _schema;
  // Resolve the schema relative to this module, working from either layout:
  //   dist/index.js          -> ../agent-definition.schema.json   (shipped)
  //   typescript/src/index.ts -> ../../agent-definition.schema.json (vitest in-place)
  const candidates = ["../agent-definition.schema.json", "../../agent-definition.schema.json"];
  for (const rel of candidates) {
    try {
      _schema = JSON.parse(readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8"));
      return _schema!;
    } catch {
      /* try next candidate */
    }
  }
  throw new Error("agent-def: could not locate agent-definition.schema.json next to the module");
}

function getValidator(): ValidateFunction {
  if (_validate) return _validate;
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  _validate = ajv.compile(getSchema());
  return _validate;
}

export interface ValidationResult {
  valid: boolean;
  /** Human-readable `instancePath: message` strings; empty when valid. */
  errors: string[];
}

/** Structural validation against the JSON Schema. Does not touch the filesystem/registry. */
export function validateAgentDefinition(obj: unknown): ValidationResult {
  const validate = getValidator();
  const valid = validate(obj) as boolean;
  if (valid) return { valid: true, errors: [] };
  const errors = (validate.errors ?? []).map(
    (e) => `${e.instancePath || "(root)"} ${e.message ?? "invalid"}${e.params && Object.keys(e.params).length ? ` ${JSON.stringify(e.params)}` : ""}`,
  );
  return { valid: false, errors };
}

/**
 * Parse + validate + version-check. Accepts a JSON string or an already-parsed object.
 * Throws with a descriptive message on invalid JSON, unknown version, or schema failure.
 * Returns the value typed as AgentDefinition.
 */
export function loadAgentDefinition(input: string | object): AgentDefinition {
  let obj: unknown;
  if (typeof input === "string") {
    try {
      obj = JSON.parse(input);
    } catch (e) {
      throw new Error(`agent-def: invalid JSON — ${(e as Error).message}`);
    }
  } else {
    obj = input;
  }

  // Version gate FIRST, with a clear message, before structural validation noise.
  const v = (obj as { version?: unknown })?.version;
  if (typeof v !== "number") {
    throw new Error(`agent-def: missing or non-numeric "version" field (expected ${SCHEMA_VERSION})`);
  }
  if (v !== SCHEMA_VERSION) {
    throw new Error(`agent-def: unsupported AgentDefinition version ${v} (this loader handles version ${SCHEMA_VERSION})`);
  }

  const { valid, errors } = validateAgentDefinition(obj);
  if (!valid) {
    throw new Error(`agent-def: schema validation failed:\n  - ${errors.join("\n  - ")}`);
  }
  return obj as AgentDefinition;
}
