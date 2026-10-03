---
name: product-review-team
description: Orchestrate a specialist subagent team to review and improve The Daily Signal when the user requests a multidisciplinary product review, role-based critique, or a team-led improvement pass. Consolidate findings, implement authorized fixes, and obtain independent re-review.
---

# Product review team

Use for a requested team review. For a narrow fix or a single product/design critique, use the existing project or product-design-review guidance without assembling a full team. Creating or editing this skill does not itself initiate a product review.

Read project-guide, product-design-review, and reader-e2e-review. Follow their client-isolation, testing authorization, screenshot, independent-review, and ownership requirements. This skill explicitly instructs delegation to specialist subagents when invoked for a team review; it does not authorize unrelated actions or expand the user's scope.

## Frame the review

Record the reader goal, feature/product scope, user constraints, branch/base, running app URL, intended devices, and success measures. Identify relevant reader archetypes. Distinguish review-only requests from requests to review and improve: review-only ends with findings; an improvement request continues through implementation and validation.

Prepare a common evidence packet: current code/diff, relevant architecture/skills, reader task steps, captured desktop/mobile states, observed errors, and available results. State what was mocked and what was exercised live. Do not give reviewers the expected verdict or tell them to defend the implementation.

When browser interaction is authorized, use an isolated profile and preserve it for persistence checks. Coordinate a single browser operator or separate profiles/client IDs for specialist interactions. Bound live generation/model requests; do not let reviewers restart the shared server, cancel other clients' work, clear user storage, or run competing costly jobs. Tests and additional network actions still need the user's existing authorization.

## Assemble specialists

Spawn separate subagents with the role briefs in [references/roles.md](references/roles.md):

| Role | Primary question |
| --- | --- |
| Product owner | Does this solve the reader's real need, and what should be prioritized? |
| UI/UX designer | Can readers discover, understand, and control it across devices? |
| Engineer | Is the implementation correct, maintainable, and consistent with architecture? |
| QA / testability reviewer | How can we observe success and detect regressions? |
| Copywriter / documentation reviewer | Are labels, explanations, and documentation accurate and useful? |

Use the available concurrency slots; run remaining roles in later waves rather than dropping them. Pass each reviewer the common packet, its role brief, and explicit read-only boundaries. Preserve specialist independence: they review and return findings, not edit the code being reviewed. If delegation is unavailable, report that limitation and distinguish a single-agent pass from an independent team review.

Require a response from each role. Share a relevant question or conflict for follow-up when needed; avoid polling agents repeatedly or duplicating their work. Each report should identify evidence, reader impact, confidence, proposed improvement, and an observable acceptance check. “No findings” is valid when supported by the inspected evidence; do not demand invented criticisms.

## Synthesize and decide

Maintain a finding ledger in the work log or PR, with role, location/repro, impact, evidence, proposed fix, acceptance check, and disposition. Deduplicate the same issue across roles, preserve differing evidence, and resolve conflicting recommendations using reader goals, user constraints, and implementation cost. Do not use a vote as a substitute for reasoning.

Prioritize broken tasks, misleading claims, data loss/isolation, and inaccessible controls, then recovery, comprehension, and polish. Select a coherent set of improvements within scope. Label hypotheses and untested claims; avoid adding features just to satisfy a role. Every actionable finding needs a fix or a concrete, evidence-backed reason it is not applicable. Record dependencies, authorization needs, and genuinely deferred optional suggestions.

## Implement and close the loop

For an authorized improvement request, implement the selected changes on the requested branch/worktree or an appropriately scoped feature branch. Do not stop after a critique report. The orchestrator may implement; delegated implementation must use a separate task/agent from the reviewer, with clear file ownership to prevent conflicting edits.

Exercise acceptance checks within the user's testing authorization. Use real controls for UI behavior, actual generated results for ingestion claims, and matched before/after screenshots for visible changes. Simulated speech cannot prove device voice quality. Update documentation and reusable regressions when supported by observed failures.

Send the updated diff, finding ledger, images, and results to independent reviewers. Include the relevant original specialists for fixes in their area and follow reader-e2e-review's mandatory PR review/fix/re-review loop before publishing each update. Reviewers must check that their findings were addressed and look for regressions. Repeat until no actionable findings remain; unresolved blockers are not a completed review.

When opening/updating a PR, summarize reader problems, changes, accepted/rejected suggestions with reasons, validation and limitations, and the independent review outcome. Attach accessible comparison screenshots and verify links. Preserve the existing PR description and clean up temporary screenshot branches with completed PRs when authorized. Do not merge or contact people merely because a team review was requested.
