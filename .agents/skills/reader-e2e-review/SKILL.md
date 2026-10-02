---
name: daily-signal-reader-e2e-review
description: Review The Daily Signal as a reader in a real browser, reproduce interaction or responsive-layout bugs, and verify UI fixes with isolated Playwright sessions.
---

# Reader browser review

Use the running HTTP app, usually `http://127.0.0.1:8765`, rather than opening `index.html` directly. Read the project-guide and run-and-debug skills when architecture or startup details are needed.

## Real end-user review

Use Python Playwright in a fresh context or a dedicated temporary persistent profile. Preserve that profile across review steps to test reload, archive, and highlight persistence; never reuse or clear the user's browser profile. New generation, chat, and explanations exercise the configured model and outbound search. Keep live requests bounded and cancel only jobs created by the review.

Exercise a complete paper: enter a topic, choose a modest article limit, generate, refresh during progress, read the results, explain a selection crossing a heading and paragraph, explicitly add it to chat, and reload. Reopen the archived paper and compare its topic, articles, explanation ranges, and conversation. Reading preferences belong to the browser, not each edition. Include empty prompts, cancelled settings drafts, and switching archived editions during generation when relevant.

Capture desktop, tablet, and phone layouts (for example 1440, 768, 390, and 320 pixels wide), all themes, and the largest reading size. Wait for panel transitions and fonts before screenshots. Inspect screenshots, not only DOM assertions. Check the actual downloaded screenshot separately: Playwright full-page screenshots can capture a fixed texture only over the initial viewport, unlike the app's screenshot renderer.

Collect page errors and failed app requests. Check horizontal overflow, clipped controls, touch target sizes, keyboard Escape/focus return, and whether the question and response remain navigable in a long chat. Verify explanations stay scoped to their edition and don't enter chat without an explicit action.

## Repeatable UI regression pass

Run the bundled script against the running app:

```sh
python3 .agents/skills/reader-e2e-review/scripts/reader_smoke.py \
  --base-url http://127.0.0.1:8765 --output-dir /tmp/daily-signal-reader-review
```

It uses isolated browser storage and intercepts `/api/*` with deterministic paper, generation, explanation, and chat responses. It never submits requests to the real model. It checks observable interactions and writes screenshots. These results prove UI behavior, not search relevance, scraping reliability, or model quality; validate those with a bounded live run when the task needs it.

Playwright and its Chromium installation must be available in the Python environment. Use `--chromium-path` to select an existing browser executable if necessary. If Chromium shows empty text or crashes in FontConfig while computed styles and text nodes are present, verify the browser environment before diagnosing the app. A minimal temporary `FONTCONFIG_FILE` using installed font directories can isolate host font issues. Do not commit host-specific font paths or change the app's font stack to conceal that failure.

## Form and streaming regressions

Syntax checks and simulated screenshots do not establish that an event handler works. When the user authorizes interaction testing, submit through the actual controls: click **Send** and press Enter in the composer. Assert exactly one chat API request, an unchanged document token, no main-frame navigation, and no page errors/unhandled promise rejections. Shift+Enter and IME composition must not submit. Fixture setup may seed papers/history; calling the submit callback or inserting an answer directly is not a submission test.

For streaming changes, use the local integration helper:

```sh
python3 .agents/skills/reader-e2e-review/scripts/chat_stream_smoke.py \
  --output-dir /tmp/daily-signal-chat-stream-review
```

It starts isolated reader and fake OpenAI-compatible servers on ephemeral loopback ports, uses the real chat form/backend, and makes no external model or search requests. `--chromium-path` selects an existing browser. `--html-revision <commit>` serves an older frontend to confirm a regression is detected. Check partial content before completion, fragmented Unicode, Markdown tables, hidden reasoning, cancellation with retained text, interrupted streams, context retries without replayed text, and model-chosen browsing versus direct answers. A supplied-text explanation should skip research; the web-search-off setting must prevent tool use even when the model would otherwise search.

Verify scrolling with short and long histories: submission reaches the actual pane bottom after composer layout changes. Incoming chunks follow only until the question reaches the top. Wheel, touch, scrollbar, or keyboard scrolling stops that follow behavior for the current reply. Continue receiving chunks after manual scrolling to establish that the reader's position remains stable.

Run the authorized interaction checks before describing a PR as functionally verified. If only syntax or screenshot checks were performed, clearly label the changed interaction as unverified and do not treat screenshots as evidence of request/stream behavior.

## Pull request comparison screenshots

When opening or updating a PR with visible reader changes, attach before-and-after screenshots to the PR description. Capture the base and proposed versions using the same paper or deterministic fixture, theme, viewport, reading size, scroll position, and interaction state. Include the views that demonstrate the changes, such as phone generation controls, tablet status text, or an open chat panel. Wait for fonts and transitions, inspect both images, and label each pair with its viewport and state.

Use image URLs that reviewers can access and render in the PR, with before/after images next to each other in a Markdown table. Verify the links after publishing. Local filesystem paths are not attachments. Preserve the existing PR description and state whether the comparison uses sample data. Keep browser profiles and incidental screenshots out of the feature diff; if repository hosting is needed, a dedicated screenshot artifact branch can hold the selected images.

Report concrete findings, changes, and the limits of validation. A new skill/helper should be validated with skill-creator's validator and exercised before completion.
