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

The configured model plans several focused searches from the subject; the server searches DuckDuckGo, Google News RSS, and Reddit hot results for each angle. Reddit results use the hot ranking and are limited to the selected lookback window. The search window and maximum number of articles are configurable in the settings menu. The date window is best-effort for general search results; when a source has no verifiable publication date, the paper labels it as unverified. It deduplicates results, limits repeated publishers, filters relevance with the configured model, keeps Reddit results ranked by hotness within the selected time slice, and retrieves article text where available. For JavaScript-heavy pages, it first tries Playwright with Chromium if the Python Playwright package is installed, then a headless Chromium executable (or `DAILY_SIGNAL_CHROMIUM`), followed by a public text extraction service. To enable Playwright, install `playwright` in the Python environment running the server and run `playwright install chromium`. Sources that still cannot provide readable text are labeled as feed excerpts. The model summarizes articles in parallel and then creates an aggregate overview from those summaries. Every story links to its original publisher. Search results and article text are treated as untrusted evidence; verify important claims at the source.

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

- Generated papers are cached in the browser and automatically saved to the archive. Saved editions include the complete article/source context, topic, highlights, chat history, and reading preferences.
- Select text in a paper to ask the model for a plain-English explanation. Explanations are Markdown-rendered and cached; adding one to chat is always an explicit action.
- The chat sidebar can search the web, cites the supplied results, and compacts older conversation context when needed.
- Use **Save screenshot** to download a full-page PNG. Screenshot rendering loads html2canvas from jsDelivr, so the browser needs access to that CDN.

The page uses a locally served paper-grain texture. Playwright is optional and only used to render JavaScript-heavy publisher pages.

## Agent guidance

Project-specific agent skills live in `.agents/skills/`: `project-guide` covers architecture and safe changes; `run-and-debug` covers startup, LAN access, and troubleshooting.
