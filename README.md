# The Daily Signal

A personalized newspaper. Choose the topics you want to follow—from regional transit to developer tools, battery research, or gardening—and get recent stories, concise summaries, and the bigger picture in one place.

## Requirements

- Python 3.8 or newer. The server otherwise uses only Python's standard library.
- An OpenAI-compatible Chat Completions endpoint reachable from the machine running the server, plus a model name. `run.sh` validates the settings and exits before listening if the endpoint URL or model name is invalid; see [Configure the local model](#configure-the-local-model).
- Outbound internet access from the server for public web search and article retrieval.
- Optional, for JavaScript-heavy article pages: Playwright for Python and its matching Chromium browser. Install them with:

  ```sh
  python3 -m pip install --user playwright
  python3 -m playwright install chromium
  ```

  On Linux, Chromium also needs OS shared libraries and fonts. Playwright's `install-deps` helper installs these on supported Debian/Ubuntu systems (it may require root):

  ```sh
  sudo python3 -m playwright install-deps chromium
  ```

  On other Linux distributions, install the equivalent Chromium runtime libraries with that distribution's package manager. Playwright's [browser installation guide](https://playwright.dev/python/docs/browsers#install-system-dependencies) lists the current dependencies and supported platforms. Without Playwright, the server can still use an installed Chromium executable or its text-extraction fallback.

## Run it

From this directory, run:

```sh
./run.sh
```

Open <http://127.0.0.1:8765> in Chrome. Do not open `index.html` directly: the companion server performs web searches and retrieves source pages. To view it from a phone or another computer on the same network, run `./run.sh --lan`; the terminal prints the desktop address. You can also set `--host 0.0.0.0` and `--port 8765` separately. LAN mode has no sign-in, so use it only on a trusted network and allow TCP port 8765 through the desktop firewall if needed.

## Choose a subject

Write a topic in **What should this paper cover?** and select **Create paper**. Be broad or specific, and include useful boundaries such as a location, date range, audience, or subtopic. Examples:

- Recent changes in Rust async runtimes
- Practical home battery storage and current safety guidance
- New open-weight language models that run on consumer GPUs
- Urban gardening techniques for small balconies

The configured model plans distinct search angles and chooses relevant publisher feeds. Discovery combines DuckDuckGo, Bing News, Google News RSS, Reddit hot results, and—when appropriate—Hacker News. The built-in feed catalogue includes BBC, The Guardian, NPR, The New York Times, and NASA; the server also discovers RSS/Atom links advertised by source publishers. Results are deduplicated and filtered for relevance by your configured model, then rechecked against the retrieved article text before inclusion. For geographically restricted topics, the model identifies the named places and inclusion requires a matching quote in the retrieved source text. The model interprets the whole prompt, whether it is keywords or natural language. Punctuation is not a hard delimiter: **Killeen, Texas** remains one location, and connected phrases retain their meaning. When the prompt actually requests independent interests, a story can cover any of those interests; explicit relationships and restrictions still apply. Larger papers get more model-planned search angles, and candidates are interleaved across interests. The article count is an accepted-article target: rejected or outdated articles are replaced from the remaining candidates. If more are needed, the model plans up to three additional search rounds based on accepted coverage. Screening and reading stop when the target is filled; they are bounded to at most 1,000 distinct candidates and 300 source pages for a 100-article paper, or smaller budgets for smaller requests. The server does not pad a paper with unrelated or stale sources. An underfilled paper explains the shortfall and shows how many matches were checked and pages opened.

The date range and target article count (up to 100) are configurable in Settings. Known dates are checked during discovery and again when publisher metadata becomes available. Undated results remain labeled **Date unverified** rather than being assigned today's date.

Article retrieval first resolves search redirects to the actual publisher, including best-effort decoding of Google News links. It reads direct HTML, article-specific containers, structured article data, and RSS/Atom content. Navigation, advertisements, and related-story containers are excluded. If direct retrieval is insufficient, it tries Playwright, an installed Chromium executable (or `DAILY_SIGNAL_CHROMIUM`), then a public text extraction service. Scraping and summarization use separate worker queues, so slow publishers do not hold up summaries of readable pages. Public retrieval results are briefly cached; paper state remains isolated per browser.

Each story identifies what was available: **Full article**, **Publisher text**, **Partial article**, **Publisher page**, **Reddit discussion**, or **Summary from excerpt**. Retrieval diagnostics are available under **About this summary** instead of crowding the story. A long page or search snippet alone is not considered a full article. Paywalls, bot challenges, and unavailable pages can still prevent full retrieval; Google News's public redirect protocol is unsupported and may change. The stored source context retains up to 30,000 characters per story for later chat and explanations. Model input is bounded separately for smaller context windows. Every story links to its original publisher. Sources and model output are untrusted evidence; verify important claims at the source.

### Add publisher sources

Operators can supplement the built-in discovery with repeatable RSS/Atom feed arguments:

```sh
./run.sh --source-feed https://www.nasa.gov/feed/ \
  --source-feed https://feeds.bbci.co.uk/news/world/rss.xml
```

Alternatively set `DAILY_SIGNAL_SOURCE_FEEDS` to a comma-separated list of feed URLs. These settings belong to the server; relevance and lookback checks still apply to custom feeds. Existing model environment variables or command-line options are required as described below.

## Configure the local model

Model configuration belongs to the server process; the browser never receives the model endpoint or API key and never calls the model directly. `run.sh` validates the configuration and exits with an error before opening the web server if the endpoint or model is missing or malformed. Set these environment variables before starting the app:

```sh
export DAILY_SIGNAL_LLM_ENDPOINT=http://localhost:1234
export DAILY_SIGNAL_LLM_MODEL=qwen3.8-9b-distill
export DAILY_SIGNAL_LLM_CONTEXT_LENGTH=131072
export DAILY_SIGNAL_LLM_OUTPUT_TOKENS=16384
# Optional, if your endpoint requires authentication:
export DAILY_SIGNAL_LLM_API_KEY=your-key
./run.sh --lan
```

The same settings are available as command-line options, such as `./run.sh --llm-endpoint http://localhost:1234/v1 --llm-model qwen3.8-9b-distill`. Use `./run.sh --help` for the full list. The backend uses OpenAI-compatible Chat Completions only; for LM Studio, enable its OpenAI-compatible server and use its `/v1` endpoint. Set the context length to a size supported by the loaded model. The browser stores only the paper prompt, article limit, and lookback window.

## Reading and saving

- Generated papers are cached in the browser and automatically saved to the archive. Saved editions include the complete article/source context, topic, highlights, and chat history. Theme, font, and text size are browser-wide preferences.
- A new browser opens ready for your topic; generation starts when you press **Create paper** or Enter in the topic field. Refresh reconnects to an ongoing generation.
- On phones, chat and the archive open as full-width panels. Close them with × or Escape to return to reading.
- Select text in a paper to ask the model for a plain-English explanation. Explanations are Markdown-rendered and cached; adding one to chat is always an explicit action.
- The chat sidebar lets the configured model decide whether web research is needed, answers directly from available context when it is not, cites retrieved results, and compacts older conversation context when needed. Answers stream as they arrive, with incremental Markdown rendering (including tables). Research progress appears before the answer. **Stop** cancels the active reply and retains any text already received; interrupted replies are labeled. Submission smoothly scrolls to the bottom of the conversation after the composer layout updates. As chunks arrive, the pane follows the growing response until the question reaches the top, keeping the question and answer together. Scrolling manually immediately stops this following behavior. Endpoints that return a complete JSON response instead of a stream still work, but that answer appears all at once.
- Use **Save screenshot** to download a full-page PNG. Screenshot rendering loads html2canvas from jsDelivr, so the browser needs access to that CDN.

The page uses a locally served paper-grain texture. Playwright is optional and only used to render JavaScript-heavy publisher pages.

## Agent guidance

Project-specific agent skills live in `.agents/skills/`. Start with `project-guide` for architecture and `run-and-debug` for local operation. Use `product-review-team` to coordinate product, design, engineering, QA, and documentation reviews; use focused reviews such as `product-design-review`, `accessibility-review`, `privacy-security-review`, `generation-pipeline-review`, `source-quality-review`, `narration-quality-review`, `incident-diagnostics-review`, `release-migration-review`, and `visual-regression-review` when appropriate. `reader-e2e-review` covers real-browser validation and the independent review and screenshot requirements for PRs.

## Read aloud

Use **Read aloud** in the toolbar to listen to a separate reporter-style script that follows the paper overview, themes, and article summaries in order. During edition generation, the backend uses your configured model to rewrite the finished paper into conversational spoken copy, with a **Preparing reporter narration** progress stage. New editions include the script before they become ready. Older editions, or papers whose narration preparation failed, prepare it on first playback. The rewrite instructions preserve facts, attribution, and uncertainty; the app saves the script with the edition for replay. While preparing, the button becomes **Stop preparing**; stopping discards the pending playback (Stop also requests backend cancellation; upstream model shutdown is best-effort). Click **Stop reading** to stop; click again to restart from the beginning. Highlight a passage and choose **Read selection** in its popover to listen to just that text. Starting another reading replaces the previous one, and switching editions or generating a new paper stops playback.

In **Paper settings → Read aloud**, filter available voices by name or language, choose a voice and reading speed, and use **Preview voice** to hear both before saving. Voices are labeled **on device** or **online**; an online voice may send spoken text to the browser voice provider. Previews stop the current reading. The selection applies to both paper and highlighted-text playback, is saved per browser, and falls back to the device default if the voice becomes unavailable. Closing settings without saving discards voice and speed drafts. Saved speed applies to paper and selected-text reading; preview errors appear beside the preview button. Voice lists update when the browser makes additional voices available.

Reading uses the browser's [speech synthesis API](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis) and device voices; speech playback does not call the configured LLM, but first-time paper narration preparation does. Long papers are spoken in short chunks. The corresponding paper paragraph or heading is highlighted during narration. A transcript drawer slides up at the bottom of the viewport when whole-paper playback starts, highlights the current sentence and (when the voice provides timing) word, and fades away when playback finishes or stops. The drawer includes Pause/Resume, Previous/Next section, a saved browser-wide playback speed (0.75×–2×), and section progress with the current story title. Changing speed resumes from the last reported word boundary, or the current chunk when timing is unavailable. Skipping starts the chosen section playing. **Follow reading** in the drawer smoothly scrolls to each spoken section. Scrolling manually turns following off; use the toggle to resume. Following starts enabled for each whole-paper playback and respects reduced-motion preferences. Voices without timing events show the current spoken chunk. Selected-text reading and voice previews do not open the drawer. Selected-text reading stays verbatim and also highlights the current word when the voice supplies word boundary events. Highlights clear when playback stops or finishes. Keep the page open: background or locked-screen playback depends on your browser and operating system. Unsupported browsers show disabled controls.

## Completion notifications

In **Paper settings → Notifications**, choose **Enable completion notifications** and allow the browser permission prompt. This preference applies immediately and is saved per browser. Disable it there at any time. Paper generation sends a completion alert when its polling tab is unfocused; chat replies, explanations, screenshot exports, and on-demand narration preparation do so when they take at least five seconds. Cancelled and failed tasks do not send success alerts. Click a notification to return to its originating tab and edition; if that edition is no longer saved, the archive opens.

Notifications require HTTPS or localhost and browser support. Plain HTTP LAN URLs (such as `http://192.168.x.x:8765`) cannot request notification permission; use HTTPS to enable them from another device. Mobile browser support varies and may require installing the site as a home-screen app. The notification service worker does not cache pages or API data. This feature needs the tab to remain open and able to process results: it does not provide server push after the tab closes, and suspended/mobile tabs may delay alerts until they resume. Browser or operating-system notification settings can also suppress alerts.

## Client data isolation

The shared server uses **browser-local durable persistence and client-scoped transient execution state**. Editions, chat, highlights, narration, and preferences are stored in the browser; server jobs and cancellation are keyed to their owning consumer. Processing still sends selected client context to the backend and configured model. Consumer IDs provide logical separation, not authenticated accounts. See [Client data isolation architecture](docs/client-data-isolation.md) for storage boundaries, API ownership checks, multi-client behavior, and the trust model.

## Ownership and contributions

Copyright © 2026 Gavin Alvesteffer. All rights reserved. This is proprietary software; no use, distribution, or commercial license is granted by public availability. Commercial rights are reserved to Gavin Alvesteffer, subject to third-party rights and applicable law. See [LICENSE](LICENSE). Outside contributions require a signed rights assignment before acceptance; see [CONTRIBUTING.md](CONTRIBUTING.md) and [CONTRIBUTOR_AGREEMENT.md](CONTRIBUTOR_AGREEMENT.md).
