---
name: daily-signal-run-and-debug
description: Use when starting, configuring, or diagnosing The Daily Signal, its local AI generation, browser access, or LAN mode.
---

# Run and debug The Daily Signal

## Start the service

Run commands from the repository root so the server can find `index.html` and `assets/`.

```sh
./run.sh
```

Open `http://127.0.0.1:8765` in Chrome. Keep the terminal open while using the page. Do not open `index.html` as a `file://` URL; feed retrieval, article reading, chat, and explanations use the HTTP service.

## View it from another device on the LAN

```sh
./run.sh --lan
```

The server prints LAN addresses to try. Open one from the phone or other computer. The same options can be set explicitly, for example `./run.sh --host 0.0.0.0 --port 8765`. LAN mode has no sign-in, so use it only on a trusted network. If another device cannot connect, check the desktop firewall for the selected TCP port.

Configure the model on the server process, not in the browser. For example:

```sh
export DAILY_SIGNAL_LLM_ENDPOINT=http://localhost:1234/v1
export DAILY_SIGNAL_LLM_MODEL=qwen3.8-9b-distill
./run.sh --lan
```

The backend supports OpenAI-compatible Chat Completions only; in LM Studio, enable its OpenAI-compatible server. The browser sends prompt/options and conversation text to this app's backend; it never sees model credentials or calls the model endpoint directly. A phone can use the desktop's `localhost` model endpoint because requests originate from the desktop server.

## Diagnose common issues

- **Page unavailable:** confirm the process is running, use the printed address and port, and check the firewall when connecting over the LAN.
- **Feeds unavailable:** generation needs outbound internet access. Feed errors are reported separately from model errors.
- **Model connection failure:** verify `DAILY_SIGNAL_LLM_ENDPOINT`, `DAILY_SIGNAL_LLM_MODEL`, and the optional API key in the server process environment. LM Studio must have the model loaded and its OpenAI-compatible server enabled.
- **Context overflow:** confirm `DAILY_SIGNAL_LLM_CONTEXT_LENGTH` is supported by the loaded model. Chat history is compacted server-side when needed; very small context windows can still reject a long current question or attached source context.
- **No recent generation after refresh:** generation state is held by the running server process. Refresh reconnects while that process remains alive; restarting the process ends the in-memory job.
- **Saved data missing on another device:** local storage and IndexedDB are browser-local, not shared by the server.
