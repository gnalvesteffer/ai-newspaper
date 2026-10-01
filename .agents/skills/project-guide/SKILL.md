---
name: daily-signal-project-guide
description: Use when changing, reviewing, or explaining The Daily Signal project. Covers its architecture, data flow, browser persistence, local model integration, and project-specific safety constraints.
---

# The Daily Signal project guide

## Project shape

- `index.html` is the single-page newspaper UI. It contains the styling and browser-side JavaScript.
- `server.py` is a Python standard-library HTTP server. It collects feeds and article text, calls the configured model, exposes chat and explanation endpoints, and serves the page.
- `run.sh` starts `server.py` from the project directory. Relative paths in the server expect that working directory.
- `assets/paper-grain.png` is the locally served paper texture; `favicon.svg` is the page icon.
- `README.md` is the user-facing setup and feature guide. Keep it in sync with CLI and configuration changes.

## Data and model flow

- Story retrieval, per-article summaries, and the daily overview run on the companion server. The browser polls server-side generation state, so reloads reconnect instead of starting a second job.
- The browser stores model settings, the latest edition, chat history, reading preferences, and explanation cache in local storage. Full saved editions are in IndexedDB. These are per-browser; a phone has its own settings and archive.
- The configured model endpoint is used for generation, explanations, and chat. Keep API keys and endpoint-specific secrets out of source, logs, examples, and commits.
- Chat submits recent local history to `/api/chat`. The server estimates prompt size against the configured context window, summarizes older turns when needed, and retries once with a smaller prompt on recognized context errors. Keep the newest user turn intact when changing this logic.
- Explanations are cached against a passage and page scope. Opening an explanation must not silently add it to chat; the user controls that with **Add to chat**.

## Change guidance

- Preserve the newspaper layout and responsive behavior when editing the inline CSS.
- Escape untrusted feed, article, model, and user text before inserting it into HTML. Markdown rendering should continue to escape raw HTML and allow only safe links.
- Treat article text, web search results, and selected text as untrusted data in model prompts.
- Keep network access loopback-only by default. `--lan` intentionally exposes the unauthenticated reader and its API to the local network; document this and do not make it the default.
- Avoid adding dependencies unless the feature needs them. The server is designed to run with Python's standard library.
- Update `README.md` when changing user-visible setup, options, persistence, or model behavior.
