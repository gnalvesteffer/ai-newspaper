# The Daily Signal

A local, topic-driven newspaper. Tell it what you want to follow—anything from new developer tools to regional transit, battery research, or balcony gardening—and it searches the public web, reads the available source pages, summarizes each source with your configured local model, and synthesizes a concise overview.

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

Write a topic in **What should this paper cover?** and select **Generate edition**. Be broad or specific, and include useful boundaries such as a location, date range, audience, or subtopic. Examples:

- Recent changes in Rust async runtimes
- Practical home battery storage and current safety guidance
- New open-weight language models that run on consumer GPUs
- Urban gardening techniques for small balconies

The configured model plans distinct search angles and chooses relevant publisher feeds. Discovery combines DuckDuckGo, Bing News, Google News RSS, Reddit hot results, and—when appropriate—Hacker News. The built-in feed catalogue includes BBC, The Guardian, NPR, The New York Times, and NASA; the server also discovers RSS/Atom links advertised by source publishers. Results are deduplicated and filtered for relevance by your configured model, then rechecked against the retrieved article text before inclusion. For geographically restricted topics, the model identifies the named places and inclusion requires a matching quote in the retrieved source text. If the paper is underfilled, the model plans one additional bounded search round. The article count is a maximum: the server does not pad a paper with unrelated or stale sources.

The search window and maximum article count (up to 100) are configurable in Settings. Known dates are checked during discovery and again when publisher metadata becomes available. Undated results remain labeled **Date unverified** rather than being assigned today's date.

Article retrieval first resolves search redirects to the actual publisher, including best-effort decoding of Google News links. It reads direct HTML, article-specific containers, structured article data, and RSS/Atom content. Navigation, advertisements, and related-story containers are excluded. If direct retrieval is insufficient, it tries Playwright, an installed Chromium executable (or `DAILY_SIGNAL_CHROMIUM`), then a public text extraction service. Scraping and summarization use separate worker queues, so slow publishers do not hold up summaries of readable pages. Public retrieval results are briefly cached; paper state remains isolated per browser.

Each story identifies what was available: **Full article read**, **Publisher feed text**, **Partial article text**, **Publisher page text**, **Reddit post and discussion**, or **Feed excerpt only**. A long page or search snippet alone is not considered a full article. Paywalls, bot challenges, and unavailable pages can still prevent full retrieval; Google News's public redirect protocol is unsupported and may change. The stored source context retains up to 30,000 characters per story for later chat and explanations. Model input is bounded separately for smaller context windows. Every story links to its original publisher. Sources and model output are untrusted evidence; verify important claims at the source.

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
- A new browser opens ready for your topic; generation starts when you press **Generate edition** or Enter in the topic field. Refresh reconnects to an ongoing generation.
- On phones, chat and the archive open as full-width panels. Close them with × or Escape to return to reading.
- Select text in a paper to ask the model for a plain-English explanation. Explanations are Markdown-rendered and cached; adding one to chat is always an explicit action.
- The chat sidebar lets the configured model decide whether web research is needed, answers directly from available context when it is not, cites retrieved results, and compacts older conversation context when needed. Answers stream as they arrive, with incremental Markdown rendering (including tables). Research progress appears before the answer. **Stop** cancels the active reply and retains any text already received; interrupted replies are labeled. Submission smoothly scrolls to the bottom of the conversation after the composer layout updates. As chunks arrive, the pane follows the growing response until the question reaches the top, keeping the question and answer together. Scrolling manually immediately stops this following behavior. Endpoints that return a complete JSON response instead of a stream still work, but that answer appears all at once.
- Use **Save screenshot** to download a full-page PNG. Screenshot rendering loads html2canvas from jsDelivr, so the browser needs access to that CDN.

The page uses a locally served paper-grain texture. Playwright is optional and only used to render JavaScript-heavy publisher pages.

## Agent guidance

Project-specific agent skills live in `.agents/skills/`: `project-guide` covers architecture and safe changes; `run-and-debug` covers startup, LAN access, and troubleshooting; `reader-e2e-review` covers real browser reviews and repeatable UI regression checks.

## Read aloud

Use **Read aloud** in the toolbar to listen to the paper overview, themes, and article summaries in order. Click **Stop reading** to stop; click again to restart from the beginning. Highlight a passage and choose **Read selection** in its popover to listen to just that text. Starting another reading replaces the previous one, and switching editions or generating a new paper stops playback.

In **Paper settings → Read aloud**, choose an available voice and use **Preview voice** to hear it before saving. The selection applies to both paper and highlighted-text playback, is saved per browser, and falls back to the device default if the voice becomes unavailable. Closing settings without saving discards the voice change.

Reading uses the browser's [speech synthesis API](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis) and device voices; it does not call the configured LLM. Long papers are spoken in short chunks. The current paragraph or heading is highlighted during playback; voices that provide word boundary events also highlight the current word. Highlights clear when playback stops or finishes. Keep the page open: background or locked-screen playback depends on your browser and operating system. Unsupported browsers show disabled controls.
