---
name: daily-signal-privacy-security-review
description: Review client data isolation, browser storage, model credentials, network exposure, and risks from untrusted web or model content.
---

# Privacy and security review

Use for changes to client identity, persistence, APIs, settings, external retrieval, model calls, or LAN exposure. Read [project-guide](../project-guide/SKILL.md) and [client data isolation architecture](../../../docs/client-data-isolation.md).

- Trace a request from browser `client_id` to jobs, cancellation, status, chat history, explanations, and saved editions. Confirm one browser cannot read, cancel, or overwrite another browser's transient work; durable editions remain browser-local.
- Treat client IDs as namespace keys, not authentication. Preserve loopback-only defaults and disclose that `--lan` exposes an unauthenticated service to the local network.
- Keep endpoint credentials, API keys, prompts, article bodies, and private user data out of browser code, logs, errors, screenshots, and committed examples. Check that server configuration remains environment/CLI owned.
- Treat web pages, feeds, prompts, selected text, and model output as untrusted. Check prompt-injection boundaries, HTML escaping, Markdown link handling, URL schemes, redirect destinations, and server-side request protections.
- Review storage boundaries and retention: localStorage, IndexedDB, caches, generated paper state, archive deletion, and migrations. Avoid sending browser-local history to unrelated requests.
- Test isolation with separate browser contexts/client IDs and include cancellation and reconnect cases when relevant. Do not probe public systems, attack endpoints, or expose the LAN service beyond the user's authorized scope.
- Document concrete threats, affected data, reproduction, mitigation, and residual risk. Distinguish code inspection from runtime security testing.
