---
name: daily-signal-accessibility-review
description: Review and improve Daily Signal accessibility across keyboard use, assistive technology, contrast, responsive layouts, and reading controls.
---

# Accessibility review

Use when adding or changing interactive controls, panels, themes, text scaling, narration, or responsive layouts. Read [reader-e2e-review](../reader-e2e-review/SKILL.md) for browser setup and screenshot conventions.

- Complete important tasks using keyboard only: generate or cancel where practical, open/close settings and sidebars, explain a selection, use chat, and operate read-aloud. Check visible focus, sensible tab order, Escape behavior, and focus return.
- Inspect accessible names, roles, state announcements, headings, form labels, errors, and status changes with the browser accessibility tree or a screen reader when available. Do not treat ARIA attributes alone as proof.
- Check contrast in every theme for body copy, metadata, borders, focus rings, selection highlights, disabled controls, and hover/focus states. Preserve legibility at the largest text size and browser zoom.
- At phone and tablet widths, verify targets are comfortably tappable, dialogs fit the viewport, controls do not overlap, and selection/explanation/narration remain usable. Include reduced-motion behavior.
- For read-aloud, check that visual word/section highlighting has a nonvisual counterpart and that playback state and failures are announced without stealing focus.
- Prefer semantic HTML and native controls. Keep text zoom and reflow working; do not solve overflow by clipping content or shrinking controls.
- Record the task, browser/device, exact failure, severity, and reproducible acceptance check. Use automated scanners as a supplement, not a substitute for interaction review.
