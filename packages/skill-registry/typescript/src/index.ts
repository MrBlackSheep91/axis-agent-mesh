/**
 * @axis/skill-registry — the skill manifest standard + resolver.
 *
 * Public API:
 *   SkillManifest, SkillType, SkillTransport (+ MANIFEST_VERSION)   the shape
 *   inferType, manifestVersion                                      helpers
 *   parseSkillManifest(text)                                        SKILL.md -> manifest
 *   getSchema()                                                     the JSON Schema object
 *   validateManifest(obj)                                           structural validation
 *   loadSkill(name, opts)                                           resolve a skill by name (+optional version)
 */
import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { Ajv2020, type ValidateFunction } from "ajv/dist/2020.js";

export * from "./manifest.js";
export * from "./parser.js";
import { inferType, manifestVersion, type SkillManifest, type SkillType } from "./manifest.js";
import { parseSkillManifest } from "./parser.js";

let _schema: object | null = null;
let _validate: ValidateFunction | null = null;

export function getSchema(): object {
  if (_schema) return _schema;
  const candidates = ["../skill-manifest.schema.json", "../../skill-manifest.schema.json"];
  for (const rel of candidates) {
    try {
      _schema = JSON.parse(readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8"));
      return _schema!;
    } catch {
      /* try next */
    }
  }
  throw new Error("skill-registry: could not locate skill-manifest.schema.json next to the module");
}

function getValidator(): ValidateFunction {
  if (_validate) return _validate;
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  _validate = ajv.compile(getSchema());
  return _validate;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

/** Structural validation of a (parsed) manifest object against the JSON Schema. */
export function validateManifest(obj: unknown): ValidationResult {
  const validate = getValidator();
  const valid = validate(obj) as boolean;
  if (valid) return { valid: true, errors: [] };
  const errors = (validate.errors ?? []).map(
    (e) => `${e.instancePath || "(root)"} ${e.message ?? "invalid"}`,
  );
  return { valid: false, errors };
}

export interface ResolvedSkill {
  manifest: SkillManifest;
  /** Resolved type (inferred if the manifest didn't state it). */
  type: SkillType;
  /** Resolved version (defaults to "0.1.0"). */
  version: string;
  /** Absolute path to the SKILL.md it came from. */
  path: string;
}

export interface LoadSkillOptions {
  /** Directories to search; each is checked for `<root>/<name>/SKILL.md`. */
  roots: string[];
  /** If set, require the resolved manifest version to equal this (exact match). */
  version?: string;
}

/**
 * Resolve a skill by name: find `<root>/<name>/SKILL.md` in the first matching root,
 * parse + validate it, infer type/version. Throws with a clear message on not-found,
 * invalid manifest, or version mismatch.
 */
export function loadSkill(name: string, opts: LoadSkillOptions): ResolvedSkill {
  if (!opts?.roots?.length) {
    throw new Error("skill-registry: loadSkill requires at least one search root");
  }
  let found: string | null = null;
  for (const root of opts.roots) {
    const candidate = join(root, name, "SKILL.md");
    try {
      if (statSync(candidate).isFile()) {
        found = candidate;
        break;
      }
    } catch {
      /* not here, try next root */
    }
  }
  if (!found) {
    throw new Error(`skill-registry: skill "${name}" not found under roots [${opts.roots.join(", ")}]`);
  }

  const manifest = parseSkillManifest(readFileSync(found, "utf8"));
  const { valid, errors } = validateManifest(manifest);
  if (!valid) {
    throw new Error(`skill-registry: "${name}" manifest invalid:\n  - ${errors.join("\n  - ")}`);
  }

  const version = manifestVersion(manifest);
  if (opts.version && opts.version !== version) {
    throw new Error(`skill-registry: "${name}" is version ${version}, requested ${opts.version}`);
  }

  return { manifest, type: inferType(manifest), version, path: found };
}
