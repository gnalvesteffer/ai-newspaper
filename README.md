# The Daily Signal

A local AI engineering digest that reads publisher pages and Reddit discussions, summarizes each selected story, then synthesizes those summaries into a concise daily overview. It prioritizes new and open/local models, developer tools, coding agents and harnesses, and practical techniques. General business, funding, and corporate adoption stories are filtered out, and each publisher is capped to keep one source from dominating the edition.

## Run it

From this directory, run:

```sh
./run.sh
```

Then open <http://127.0.0.1:8765> in Chrome. Keep the terminal running while the edition is generated. Do not open `index.html` directly; the local server fetches RSS feeds and article text for the page.

Use the gear menu to configure the LM Studio URL (for example `http://your-lm-studio-host:1234`), the loaded model name, context length, per-call output token budget, stories per edition, and an optional API key. The default protocol is LM Studio's native REST API, which accepts per-request `context_length` and reasoning controls. The context value must be supported by the loaded model. The OpenAI-compatible option is also available, but its Chat Completions endpoint cannot set context length per request. The browser stores settings locally, and the companion server sends article text to the configured model endpoint.

The reader checks official and technical feeds, selected newsroom searches, and Reddit's public hot RSS feeds for r/LocalLLaMA, r/LocalLLM, r/MachineLearning, r/AI_Agents, and r/ClaudeAI. Reddit posts are ranked using each community's hot-list order and limited to the same four-day collection window as other stories. It also attempts to retrieve full article text and, for Reddit posts, the thread and top comments. If a publisher blocks retrieval, the page labels the result as feed excerpt only rather than claiming the full article was read.

Select text in the overview, a theme, or a story to ask your configured local model for a plain-English explanation. The selected passage and its nearby card context are sent only to the configured model endpoint.

After a successful generation, press **Save screenshot** to download a full-page PNG to Chrome’s configured download location. Filenames include the local date/time and a short unique ID. Screenshot rendering loads html2canvas from jsDelivr, so the browser needs access to that CDN.

Article retrieval and summaries run three stories at a time. The companion server keeps generation running independently of the browser page, so refreshing reconnects to the existing job and restores its progress. The most recent finished edition is cached in browser storage and restored when no job is running. Use **Generate edition** when you want a fresh roundup.

The page uses a locally served, generated paper-grain texture at low opacity. The text-explanation action allows a larger output budget so models with longer reasoning traces can still return a final explanation.
