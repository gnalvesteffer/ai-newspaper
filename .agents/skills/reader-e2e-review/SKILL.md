---
name: daily-signal-reader-e2e-review
description: Use when opening or updating a Daily Signal PR, reviewing the reader in a real browser, or fixing interaction and responsive-layout bugs. Requires independent subagent review and PR comparison screenshots.
---

# Reader browser review

Use the running HTTP app, usually `http://127.0.0.1:8765`, rather than opening `index.html` directly. Read the project-guide and run-and-debug skills when architecture or startup details are needed.

## Real end-user review

Use Python Playwright in a fresh context or a dedicated temporary persistent profile. Preserve that profile across review steps to test reload, archive, and highlight persistence; never reuse or clear the user's browser profile. New generation, chat, and explanations exercise the configured model and outbound search. Keep live requests bounded and cancel only jobs created by the review.

Exercise a complete paper: enter a topic, choose a modest article limit, generate, refresh during progress, read the results, explain a selection crossing a heading and paragraph, explicitly add it to chat, and reload. Reopen the archived paper and compare its topic, articles, explanation ranges, and conversation. Reading preferences belong to the browser, not each edition. Include empty prompts, cancelled settings drafts, and switching archived editions during generation when relevant.

Capture desktop, tablet, and phone layouts (for example 1440, 768, 390, and 320 pixels wide), all themes, and the largest reading size. Wait for panel transitions and fonts before screenshots. Inspect screenshots, not only DOM assertions. Check the actual downloaded screenshot separately: Playwright full-page screenshots can capture a fixed texture only over the initial viewport, unlike the app's screenshot renderer.

Collect page errors and failed app requests. Check horizontal overflow, clipped controls, touch target sizes, keyboard Escape/focus return, and whether the question and response remain navigable in a long chat. Verify explanations stay scoped to their edition and don't enter chat without an explicit action.

For cached explanations on phones, open a previously explained range by tapping it, then scroll the source passage off-screen with a touch gesture. Assert the document scrolled and the saved range is outside the viewport before checking that the explanation stays open at its last viewport position. Verify tapping a second saved range switches both quote and answer; tapping an unexplained passage, a control outside the paper, or the explicit close control should dismiss it. This catches touch-generated mouse events and scroll-anchor logic that can dismiss a useful popover during scrolling, and guards against a sticky popover that traps or obscures later interactions.

## Article yield and reader expectations

When reviewing generation, include a broad news request, a list of independent interests, a keyword-style request, a long natural-language request with editorial boundaries, and a narrow local topic including a city/state comma such as “Killeen, Texas.” Verify the model interprets punctuation and connected phrases by meaning rather than treating commas as hard delimiters. Use the same model/options for before-and-after runs. Compare requested articles with accepted output, not raw search matches: repeated index hits, rejected stories, old publisher dates, failed evidence checks, and resolved duplicate URLs can all reduce yield. Check `research_coverage` and the generation log to identify where the reduction occurs. Verify reserves replace rejected articles, reading stops at the accepted target, and bounded follow-up searches preserve geographic and date restrictions. Scarce topics should show an honest shortfall, not unrelated filler.

Use deterministic pipeline tests to cover a 100-article quota with rejected slots, a late model failure after partial acceptance, cancellation, and planned location scope reaching summary workers. Mocked UI results cannot prove ingestion yield. For live reviews, bound the requests and record elapsed time, accepted counts, retrieval coverage, runtime errors, and network limitations. Review wording as a news reader: implementation details belong in setup documentation or expandable reading details, not headline controls.

## Personalized in-depth feature

When reviewing the paper's **A closer look** article, use at least one prompt whose best shape is not a guide (for example, a local-impact topic such as “Killeen, TX”) and one prompt suited to an explainer or practical guide. Confirm the model plans focused searches, inspects what it finds, and requests another search only when evidence has a meaningful gap; supplemental sources remain outside the requested article count, and each section/visual links only to sources whose exact supporting quote is present in saved source text. Check the restrained note when supplemental searches fail or produce no cited sources. Check that older sources are presented as background with their date when available, and excerpts remain labeled honestly. Open a cited web source, highlight feature prose for an explanation, and ask chat about a supplemental source; verify the saved edition retains its source text and explanations stay scoped to that edition. Inspect the diagram, table, and timeline when returned, plus a no-visual case. Capture desktop and narrow-phone screenshots with the same deterministic paper and inspect heading hierarchy, long source labels, table reflow, workflow stacking, selection/highlight behavior, and whether the extra article overwhelms the requested news. Fixture screenshots demonstrate layout only, not research relevance or model grounding.

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

## Read-aloud controls

When changing listening behavior, exercise the real player controls with prepared narration and no extra narration request. Verify pause/resume, section navigation across multi-chunk paragraphs, browser-wide speed persistence, cancelled-utterance callbacks after skips, and restart after stopping while paused. Advance mocked utterance callbacks to below-fold sections; assert following moves the page, manual scrolling stops later movement, and resuming returns to the current section. Inspect the drawer on short phone viewports as well as desktop. Keep touch targets usable without hiding most of the news. Simulated speech proves player state and UI behavior; report real voice/device timing as unverified unless actually checked.

Use `scripts/voice_smoke.py --base-url http://127.0.0.1:8765 --output-dir /tmp/daily-signal-voice-review` for voice controls (`--chromium-path` selects a browser). It records the native voice inventory, then uses simulated voices/utterances in isolated storage to check filtering, draft previews, saved voice/rate, multi-block selection offsets, missing/late voices, error feedback, and mobile settings. It makes no model or external voice requests. An empty native inventory cannot establish audible voice quality or provider availability. Do not label simulated playback as a real-device listening test.

For selected-text reading regressions, include partial ranges from a heading into its summary and from inline emphasis into surrounding text; assert punctuation/pauses and exact selected words. Include a long selection split over multiple utterances, word highlighting at chunk boundaries, stop/restart with a late callback, playback error cleanup, and the selection popover plus Read selection control within a phone viewport. Use the same voice smoke script; it verifies that partial selections keep their offsets and don't accidentally read adjacent text.

## Independent PR review loop

For every new PR and every subsequent change to that PR (including fixes and documentation), obtain an independent review from a subagent before publishing the update. Give the reviewer the base branch, current diff, user requirements, and relevant project guidance; have it inspect correctness, persistence, cancellation, security, responsive behavior, and validation gaps as applicable. Provide the comparison images and relevant validation results as well as code. Ask for a critical reader/product review: discoverability, wording, clutter, mobile space, trust, and whether the evidence demonstrates the user's requested outcome. The reviewer should inspect the images, not infer usability solely from CSS or passing tests. State any unavailable runtime or image checks explicitly. The reviewer must review independently rather than implement the change it reviews. Respect the user's testing authorization; review does not itself authorize adding or running tests.

Address each finding with a fix or a concrete explanation supported by code or evidence. After any fix, ask for another independent review of the updated diff. Repeat review and fixes until no actionable findings remain. Complete this loop before pushing the change or opening/updating the PR, and summarize the review outcome and any remaining limitations in the PR description. Do not describe a review as complete when findings remain unresolved. This instruction explicitly authorizes delegating these reviews to a subagent.

## Pull request comparison screenshots

When opening or updating a PR with visible reader changes, attach before-and-after screenshots to the PR description. For layout/control changes, capture the base and proposed versions using the same paper or deterministic fixture, theme, viewport, reading size, scroll position, and interaction state. For generation, ingestion, or article-yield changes, also capture actual before/after generated results for the same prompt, article target, and date range. Show requested versus accepted counts; record elapsed time and retrieval coverage. A two-article layout fixture cannot demonstrate improved fulfillment of a larger target. Label archived-result replays and sample data clearly, and acknowledge that live searches/model output vary. Include the views that demonstrate the changes, such as phone generation controls, tablet status text, or an open chat panel. Wait for fonts and transitions, inspect both images, and label each pair with its viewport and state.

Use image URLs that reviewers can access and render in the PR, with before/after images next to each other in a Markdown table. Verify the links after publishing. Local filesystem paths are not attachments. Preserve the existing PR description and state whether the comparison uses sample data. Keep browser profiles and incidental screenshots out of the feature diff; if repository hosting is needed, a dedicated screenshot artifact branch can hold the selected images.

Treat screenshot artifact branches as temporary. When a PR is merged or closed and branch cleanup is requested, delete its remote screenshot branch along with its feature branch. Keep screenshot branches only for open PRs, and mention that deleting them can affect long-term availability of the image links in historical PR descriptions. Avoid leaving a separate artifact branch behind for every completed review.

Report concrete findings, changes, and the limits of validation. A new skill/helper should be validated with skill-creator's validator and exercised before completion.
