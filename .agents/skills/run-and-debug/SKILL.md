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

Configure the model separately in each browser. On a phone, the model endpoint must use the desktop's LAN address, such as `http://192.168.1.109:1234`; `localhost` on the phone refers to the phone itself. The page sends model requests through the companion service, so browser CORS is not needed for that path.

## Diagnose common issues

- **Page unavailable:** confirm the process is running, use the printed address and port, and check the firewall when connecting over the LAN.
- **Feeds unavailable:** generation needs outbound internet access. Feed errors are reported separately from model errors.
- **Model connection failure:** verify the configured host, port, model name, and API mode from the device's browser settings. LM Studio must have the model loaded and its server enabled.
- **Context overflow:** confirm the configured context length is supported by the loaded model. Chat history is compacted server-side when needed; very small context windows can still reject a long current question or attached source context.
- **No recent generation after refresh:** generation state is held by the running server process. Refresh reconnects while that process remains alive; restarting the process ends the in-memory job.
- **Saved data missing on another device:** local storage and IndexedDB are browser-local, not shared by the server.
