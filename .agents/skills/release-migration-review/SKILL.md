---
name: daily-signal-release-migration-review
description: Check release readiness and compatibility for saved browser data, server options, dependencies, documentation, and supported startup workflows.
---

# Release and migration review

Use before a release, storage/schema change, CLI/config change, or deployment/startup documentation update. Read [project-guide](../project-guide/SKILL.md) and [run-and-debug](../run-and-debug/SKILL.md).

- Identify user-visible behavior and compatibility surfaces: saved editions, IndexedDB/localStorage keys, API payloads, CLI flags, environment variables, Python/runtime dependencies, and screenshot or export behavior.
- For persisted data changes, inspect old records and migration paths. Preserve full edition content, topic, conversation, explanations, and source context; keep theme, font, and text size browser-wide.
- Check README prerequisites, install steps, first-run configuration, LAN flag behavior, example commands, and recovery steps against the actual code. Never include real endpoint secrets or machine-specific paths.
- Verify startup fails early with a clear message when required LLM configuration is missing or invalid. Keep network exposure and data-locality statements accurate.
- Run the validation appropriate to the changed surface and user authorization. Report commands and results precisely; do not call a release ready based on syntax checks alone.
- Review git status for generated data, caches, screenshots, secrets, and unrelated edits. Follow the repository PR review and screenshot process for PRs; do not publish, release, or deploy without authorization.
