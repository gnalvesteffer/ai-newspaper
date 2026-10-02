# The Daily Signal

A local, topic-driven newspaper. Tell it what you want to follow—anything from new developer tools to regional transit, battery research, or balcony gardening—and it searches the public web, reads the available source pages, summarizes each source with your configured local model, and synthesizes a concise overview.

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

The server searches DuckDuckGo and Google News RSS for the subject. The search window and maximum number of articles are configurable in the settings menu. The date window is best-effort for general search results; when a source has no verifiable publication date, the paper labels it as unverified. It deduplicates results, limits repeated publishers, and retrieves article text where available. For JavaScript-heavy pages, it can render the source with headless Chromium when Chromium is installed (or set `DAILY_SIGNAL_CHROMIUM` to its executable path); it then falls back to a public text extraction service. Sources that still cannot provide readable text are labeled as feed excerpts. The model summarizes articles in parallel and then creates an aggregate overview from those summaries. Every story links to its original publisher. Search results and article text are treated as untrusted evidence; verify important claims at the source.

## Configure the local model

Open ⚙ settings to configure the LM Studio URL (for example `http://your-lm-studio-host:1234`), the loaded model name, context length, per-call output budget, articles per paper, search window, and optional API key. The default protocol is LM Studio's native REST API; the OpenAI-compatible Chat Completions option is also available. Context length must be supported by the loaded model. Settings are stored in the current browser; generation requests and source text go from the companion server to the configured model endpoint.

## Reading and saving

- Generated papers are cached in the browser and automatically saved to the archive. Saved editions include the complete article/source context, topic, highlights, chat history, and reading preferences.
- Select text in a paper to ask the model for a plain-English explanation. Explanations are Markdown-rendered and cached; adding one to chat is always an explicit action.
- The chat sidebar can search the web, cites the supplied results, and compacts older conversation context when needed.
- Use **Save screenshot** to download a full-page PNG. Screenshot rendering loads html2canvas from jsDelivr, so the browser needs access to that CDN.

The page uses a locally served paper-grain texture. The server uses Python's standard library and does not need a package install.

## Agent guidance

Project-specific agent skills live in `.agents/skills/`: `project-guide` covers architecture and safe changes; `run-and-debug` covers startup, LAN access, and troubleshooting.
