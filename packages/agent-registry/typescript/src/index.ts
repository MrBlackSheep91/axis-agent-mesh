/**
 * @axis/agent-registry — canonical model registry for the axis ecosystem (TS twin).
 *
 * Public API:
 *   CATALOG                          Record<string, ModelSpec>
 *   DEFAULT_ASSIGNMENTS              Record<string, string>
 *   ModelSpec                        type
 *   OVERRIDE_PREFIXES                readonly [string, string] in priority order
 *   getModelFor(role, opts?)         resolve role -> model id
 *   getSpec(modelId)                 lookup ModelSpec
 *   allAssignments()                 diagnostic dump
 *   setHybridCrmOverrideLookup(fn)   wire host-side CRM override callback
 *   DEFAULT_MODEL_FOR                ergonomic alias of getModelFor
 *   GetModelForOptions               type
 *
 * Resolution order: explicit envOverrides > AXIS_MODEL_OVERRIDE_<ROLE> >
 * INVIDIA_MODEL_OVERRIDE_<ROLE> > hybridCrmLookup (per-call or module-level) >
 * DEFAULT_ASSIGNMENTS.
 *
 * Mirrors axis_agent_registry (Python) — verified byte-for-byte across 10
 * representative (role, env_overrides) pairs via the snapshot test.
 */
export { CATALOG, type ModelSpec } from "./catalog.js";
export { DEFAULT_ASSIGNMENTS } from "./assignments.js";
export {
  getModelFor,
  getSpec,
  allAssignments,
  setHybridCrmOverrideLookup,
  OVERRIDE_PREFIXES,
  DEFAULT_MODEL_FOR,
  type GetModelForOptions,
} from "./registry.js";
