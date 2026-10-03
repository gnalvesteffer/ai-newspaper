---
name: daily-signal-incident-diagnostics-review
description: Improve diagnosis and recovery for failed paper generation, web retrieval, article reading, model calls, streaming, persistence, and notifications.
---

# Incident and diagnostics review

Use when users report hangs, partial papers, confusing failures, or when adding progress, retry, cancellation, or error reporting. Read [project-guide](../project-guide/SKILL.md) for pipeline and client-scope ownership.

- Reproduce using a bounded, isolated request when authorized. Capture the user-visible state, server logs, request/job identifiers, stage timings, and relevant coverage counters.
- Distinguish search outage/no matches, duplicate or out-of-window candidates, blocked publisher access, partial article text, model configuration/request/response failures, cancellation, timeout, and browser storage errors.
- Give the user a concise status that says what completed, what failed, whether partial results were kept, and the next useful action. Keep diagnostics expandable or in logs when implementation detail would clutter the reading experience.
- Ensure progress is truthful, stale jobs do not overwrite a newly selected edition, retries do not duplicate accepted stories or chat text, and cancellation reaches only the requesting client/job.
- Log enough to correlate a failure and locate its stage, but redact API keys, authorization headers, private prompts, article bodies, and unnecessary client identifiers. Avoid swallowing exceptions without a recovery state.
- Add deterministic fault-injection coverage for changed error paths when authorized. Verify recovery as well as the failure message; do not rely on a screenshot or a successful happy path.
- Report a reproduction, root cause if established, partial-data effects, fix, validation evidence, and remaining uncertainty. Label suspected causes as hypotheses.
