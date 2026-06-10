---
name: legacy-skill
description: A legacy axis-runtime-style SKILL.md — tools_exposed + legacy keys, no type/version.
tools_exposed: [legacy_foo, legacy_bar]
platforms: [linux, darwin, windows]
allowed-tools: [Bash, Read]
user-invocable: true
---

# Legacy Skill

Mirrors the real axis-runtime frontmatter: declares `tools_exposed`, carries the
legacy `allowed-tools` key, and the kebab-case `user-invocable`. Must parse + infer
`type: tool` without edits.
