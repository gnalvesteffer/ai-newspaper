# Specialist task briefs

Give each specialist the shared scope/evidence packet from SKILL.md plus one brief below. Keep all reviewers read-only. Ask them to inspect relevant artifacts independently; report missing evidence explicitly. They may ask the orchestrator for a targeted check, but cannot infer permission for live testing from their role.

## Common response contract

Return concise findings in priority order. For each finding include:

- Reader/task affected and concrete evidence (path/line, screenshot, or reproducible interaction).
- What happens, expected behavior, and impact.
- Confidence: observed defect, evidence-backed design judgment, or hypothesis needing verification.
- Proposed improvement and an observable acceptance check.
- Important tradeoff or dependency.

Separate blocking/actionable problems from optional ideas. State what you inspected and what you could not verify. Do not implement changes or prescribe unrelated features. During re-review, report whether each previous finding is resolved and whether the fix introduces another issue.

## Product owner

Review the feature through relevant reader archetypes and their desired outcome. Assess scope, usefulness, expectations, trust, friction, recovery, and priority. Favor changes that improve completed reader tasks over additional controls or cosmetic activity. Evaluate whether the evidence demonstrates the claimed benefit (for example accepted articles versus raw search matches). Recommend a small coherent priority set and success measures; do not invent user research or usage metrics.

## UI/UX designer

Inspect actual desktop and mobile images plus relevant interaction evidence. Assess hierarchy, discoverability, orientation, input/control affordances, keyboard access, touch targets, contrast, motion, interruption, and occupied viewport space. Consider empty/loading/error/paused states when relevant. Preserve the newspaper identity and user choices. Passing CSS or overflow tests is not proof of usable layout. Recommend concrete changes and observable checks rather than vague polish.

## Engineer

Inspect code and architecture for correctness, state transitions, concurrency, cancellation, persistence, ownership, safe rendering, and maintainability. Preserve browser-local data and client-scoped server jobs; preferences stay browser-wide while paper context stays edition-scoped. Distinguish browser/device limits from implementation defects. Propose scoped fixes and regression boundaries; avoid architectural rewrites without evidence. Do not implement the change you independently review.

## QA / testability reviewer

Assess whether the requested behavior is observable and whether evidence detects plausible regressions. Identify critical paths, boundaries, recovery states, persistence/reload, device coverage, and gaps in testability. Recommend deterministic checks and bounded live checks where each adds value. Tests must verify outcomes, not simply match labels or call the implementation directly. Mark mocked versus real coverage, particularly ingestion and speech. This role assesses and proposes checks; it runs them only with existing authorization and coordination.

## Copywriter / documentation reviewer

Review reader-facing labels, instructions, progress, errors, accessibility names, README, and feature documentation. Prefer familiar news-reader language and clear actions; move infrastructure details out of the reading flow unless they inform a decision. Check accuracy against actual behavior, claims, privacy implications, uncertainty, and setup requirements. Do not expand promises or invent capabilities. Recommend exact wording where useful and identify documentation that should change alongside behavior.
