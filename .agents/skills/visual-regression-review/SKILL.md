---
name: daily-signal-visual-regression-review
description: Capture and compare consistent Daily Signal screenshots for visual changes across themes, viewports, reading sizes, and panel states.
---

# Visual regression review

Use for visual UI changes and PRs that alter layout, typography, color, texture, controls, or responsive behavior. Follow [reader-e2e-review](../reader-e2e-review/SKILL.md) for its screenshot attachment requirements.

- Use the running HTTP app, isolated browser storage, and the same deterministic paper or saved edition for each comparison. Match theme, viewport, text size/font, scroll position, and open/closed panels.
- Capture relevant desktop, tablet, and phone states; include maximum text size and all affected themes when those can expose layout failures. Wait for fonts and transitions, and inspect the images directly.
- Check clipping, overlap, horizontal overflow, line wrapping, touch targets, focus visibility, tooltip/popover placement, and whether overlays obscure reading content.
- For generated comparison tables, do not squeeze a multi-column table into the narrow visual sidebar. Place it at the feature's full content width; on phones, keep the native table for wide layouts and render an explicitly labeled `<dl>` card layout instead of changing table elements to `display: block/grid`. Inspect both layouts for complete values and assistive-technology semantics.
- For screenshot export changes, inspect the downloaded/generated artifact itself, including full-page backgrounds and texture continuity; a browser viewport screenshot is not equivalent.
- For PRs with visible changes, attach accessible before/after images to the PR description. Use the same fixture and state, label dimensions and sample-data status, verify the links, and clean up temporary screenshot branches when the PR is complete.
- Keep screenshot artifacts out of feature commits unless requested. Report what the images demonstrate and the viewports or themes not covered.
