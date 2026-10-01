# The Daily Signal

A local AI engineering digest that reads publisher pages and Reddit discussions, summarizes each selected story, then synthesizes those summaries into a concise daily overview. It prioritizes new and open/local models, developer tools, coding agents and harnesses, and practical techniques. General business, funding, and corporate adoption stories are filtered out, and each publisher is capped to keep one source from dominating the edition.

## Run it

From this directory, run:

```sh
./run.sh
```

Then open <http://127.0.0.1:8765> in Chrome. To view the page from a phone or another computer on the same network, run `./run.sh --lan`; the terminal prints the desktop address to open. You can also use `--host 0.0.0.0` and `--port 8765` separately. LAN mode has no sign-in, so use it only on a trusted network and allow TCP port 8765 through the desktop firewall if needed. On another device, set the model endpoint to the desktop’s LAN address (for example `http://192.168.1.109:1234`), not `localhost`. Keep the terminal running while the edition is generated. Do not open `index.html` directly; the local server fetches RSS feeds and article text for the page.

Use the gear menu to configure the LM Studio URL (for example `http://your-lm-studio-host:1234`), the loaded model name, context length, per-call output token budget, stories per edition, and an optional API key. The default protocol is LM Studio's native REST API, which accepts per-request `context_length` and reasoning controls. The context value must be supported by the loaded model. The OpenAI-compatible option is also available, but its Chat Completions endpoint cannot set context length per request. The browser stores settings locally, and the companion server sends article text to the configured model endpoint.

The reader checks official and technical feeds, selected newsroom searches, and Reddit's public hot RSS feeds for r/LocalLLaMA, r/LocalLLM, r/MachineLearning, r/AI_Agents, and r/ClaudeAI. Reddit posts are ranked using each community's hot-list order and limited to the same four-day collection window as other stories. It also attempts to retrieve full article text and, for Reddit posts, the thread and top comments. If a publisher blocks retrieval, the page labels the result as feed excerpt only rather than claiming the full article was read.

Select text in the overview, a theme, or a story to ask your configured local model for a plain-English explanation. The selected passage and nearby context are paired with up to three relevant source articles when available; the popover links the sources it used. For older cached editions, the local server tries to retrieve the linked article on demand. This context is sent only to the configured model endpoint.

Explanation results are rendered as Markdown and saved in this browser. Re-selecting a passage shows the saved explanation without another model call; saved passages are highlighted and reveal a short preview on hover. The **Chat** button opens a local-model conversation pane. You can attach a highlighted passage to your next message or explicitly add an explanation with the popover button. Chat history and explanation cache stay in browser storage. The server summarizes older chat turns when the configured context budget is reached and retries once with a smaller context if the model still reports an overflow. Chat includes an optional web search tool (DuckDuckGo, with Google News RSS fallback); search result links are shown below answers, and your search query is sent to the search provider when the tool is enabled.

After a successful generation, press **Save screenshot** to download a full-page PNG to Chrome’s configured download location. Filenames include the local date/time and a short unique ID. Screenshot rendering loads html2canvas from jsDelivr, so the browser needs access to that CDN.

Generated editions are automatically saved to the archive. Open the bookmark icon in the upper-left corner to browse saved editions or save the current edition again. Saved editions are stored in this browser’s IndexedDB and include the complete article/source context, explanation highlights, chat history, and the theme, reading font, size, and scroll position. Each archive entry is labeled with its date and a one-sentence summary of the edition.

Article retrieval and summaries run three stories at a time. The companion server keeps generation running independently of the browser page, so refreshing reconnects to the existing job and restores its progress. The most recent finished edition is cached in browser storage and restored when no job is running. Use **Generate edition** when you want a fresh roundup.

The page uses a locally served, generated paper-grain texture at low opacity. The text-explanation action allows a larger output budget so models with longer reasoning traces can still return a final explanation.

## Agent guidance

Project-specific agent skills live in `.agents/skills/`: `project-guide` covers architecture and safe changes, and `run-and-debug` covers startup, LAN access, and common troubleshooting.
