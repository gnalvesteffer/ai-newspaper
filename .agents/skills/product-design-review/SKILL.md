---
name: product-design-review
description: Critique and improve The Daily Signal as a product manager and interaction designer when asked for an end-user review, usability improvements, or feature enhancements. Connect observed reader problems to prioritized changes and evidence.
---

# Reader product and design review

Use for open-ended product critique or feature improvements. Keep narrow bug fixes narrow unless the user asks for a broader review. Read the project-guide for architecture and reader-e2e-review for authorized browser checks, independent PR review, and comparison screenshots.

## Start with the reader's job

Identify what the user is trying to accomplish and how success is visible. Choose relevant archetypes, such as a busy reader catching up, a local resident checking nearby news, a specialist following several connected interests, a phone reader, or someone listening while doing another task. These are review lenses, not a requirement to test every archetype on every change.

Use the app through real controls in isolated browser storage when interaction testing is authorized. Record the prompt, options, steps, observed behavior, and impact. Distinguish a reproducible defect from a design judgment or an untested hypothesis. Do not infer success from implementation alone.

## Critique as a reader

- **Discoverability:** Can a first-time reader find the action and understand its result? Are important options visible at the point of use?
- **Control:** Can the reader pause, cancel, recover, switch papers, and override automation without losing work? Does the app interrupt manual navigation?
- **Orientation:** Is the current paper, task, progress, reading section, or answer clear? Are counts accepted results or raw candidates?
- **Trust:** Are summaries, uncertain dates, excerpts, shortfalls, and research limitations represented honestly? Avoid promises the pipeline cannot fulfill.
- **Language:** Use familiar news-reader terms. Put technical retrieval/model details in setup documentation or expandable diagnostics when appropriate.
- **Layout:** Inspect phone and desktop screenshots. Measure how much usable space drawers, toolbars, and dialogs consume. Check clipping, touch targets, contrast, reduced motion, and keyboard operation; passing overflow checks alone do not establish usability.
- **Attention:** Avoid repeated motion, aggressive auto-scroll, and needless interruptions. Automation must have a discoverable override.

For listening, assess interruption/resumption, speed, section navigation, current-story context, transcript visibility, and device limitations. A bottom drawer that hides the story undermines follow-along reading even if every control fits horizontally.

## Choose and implement improvements

Describe each significant finding as: reader goal → observed friction → proposed change → expected benefit → validation. Prioritize blocked tasks and misleading feedback, then recovery/control, then comprehension and polish. Prefer a small coherent set of improvements over adding controls without a reader need. Preserve the newspaper's visual character and the user's chosen behavior.

State assumptions and relevant tradeoffs in the work log or PR. Browser-wide reading preferences must stay browser-wide; edition content and explanations remain edition-scoped. Do not add analytics, external services, legal terms, or sharing behavior merely to support a review without user authorization.

Implement the authorized improvements, exercise the actual interactions, and compare before/after under matched conditions. For ingestion changes, use actual generated outcomes with requested/accepted counts as required by reader-e2e-review; layout fixtures do not establish yield. For speech checks, simulated utterance callbacks establish player state handling, not voice quality or real device timing. Label this limitation.

## Independent critique and handoff

Follow reader-e2e-review's independent subagent review/fix/re-review loop before each PR update. Include images and observations so the reviewer can critique the experience, not just code correctness. Address findings with changes or concrete evidence. A review that finds a mobile drawer too tall should result in a compact redesign and fresh screenshots before publishing.

Report the reader problems addressed, implementation, validation, and remaining limitations. Attach accessible comparison screenshots to the PR, preserving its description. Keep screenshot branches temporary and delete them with completed PR branches when cleanup is authorized.
