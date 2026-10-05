# Agent guidance

Read the relevant project skill in `.agents/skills/` before changing architecture, running the app, or reviewing user-facing behavior.

## Improve guidance from completed work

When a task reveals a repeatable workflow, an important domain rule, a useful validation technique, or a pitfall that future agents are likely to encounter, add that knowledge to the most relevant existing skill or create a narrowly scoped skill under `.agents/skills/`. Do this as part of the task when the guidance will materially help future work; do not wait for a separate request.

Prefer updating an existing skill when the guidance fits its purpose. Create a new skill only when the workflow has a distinct recurring purpose. Keep instructions concrete, actionable, and grounded in observed behavior. Include the steps or checks that make the knowledge reusable, and state meaningful limitations. Avoid duplicating guidance across skills; link to the owning skill instead.

Validate new or changed skills using the skill format requirements and exercise any included scripts or procedures before completing the task.
