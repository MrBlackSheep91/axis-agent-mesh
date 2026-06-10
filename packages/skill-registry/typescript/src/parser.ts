/**
 * Parse a SKILL.md file's YAML frontmatter into a SkillManifest.
 *
 * Tolerant of the legacy frontmatter (name/description/tools_exposed/platforms/
 * user-invocable): it normalizes the kebab-case `user-invocable` key to
 * `user_invocable` and leaves unknown legacy keys out of the typed manifest.
 */
import matter from "gray-matter";
import type { SkillManifest } from "./manifest.js";

/** Extract the frontmatter object from SKILL.md text (no validation). */
export function parseFrontmatter(text: string): Record<string, unknown> {
  const fm = matter(text).data ?? {};
  // Normalize the one kebab-case legacy key seen in the wild.
  if ("user-invocable" in fm && !("user_invocable" in fm)) {
    (fm as Record<string, unknown>).user_invocable = (fm as Record<string, unknown>)["user-invocable"];
    delete (fm as Record<string, unknown>)["user-invocable"];
  }
  return fm as Record<string, unknown>;
}

/**
 * Parse SKILL.md text into a SkillManifest shape (structural cast — validate
 * separately with `validateManifest`). Does not throw on unknown extra keys.
 */
export function parseSkillManifest(text: string): SkillManifest {
  const fm = parseFrontmatter(text);
  return fm as unknown as SkillManifest;
}
