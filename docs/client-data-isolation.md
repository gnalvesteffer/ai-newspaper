# Client data isolation architecture

The Daily Signal is a shared processing backend with browser-local durable persistence and client-scoped transient execution state. One server process can serve multiple browsers/devices using a shared model endpoint. Each consumer owns its archive and conversation state; the backend computes results on that consumer's behalf.

## Persistence and execution boundaries

| Data | Storage/owner | Isolation mechanism |
| --- | --- | --- |
| Complete saved editions, source context, narration, explanations, chat snapshots | Browser IndexedDB | Per browser profile and web origin; each archive record contains its own edition state |
| Active chat, explanation cache, last paper, topic/options | Browser localStorage | Browser/profile/origin namespace; explanations additionally scoped to edition ID and text location |
| Theme, font, size, voice, notification preferences | Browser localStorage | User/browser-wide preferences, excluded from per-edition restore |
| Generation progress and results | Server memory (`JOBS`) | Every job stores its owning `client_id`; current/status/cancel endpoints restrict access to that owner |
| Generation cancellation | Server memory | Job ownership checked before touching its cancellation event |
| Streaming chat/narration cancellation | Server memory | Registry keys are `(client_id, request_id)`, protected by locks; completing requests remove their own entries |
| Public web source results | Shared server memory (`SOURCE_CACHE`) | Reusable source data only, returned as deep copies; never cache client chat history, saved editions, or explanations here |
| Model endpoint, credentials, inference limits | Server process configuration | Backend-only; not returned to browsers |

“Browser-local” describes durable app storage, not local-only processing. Topics, messages, selected passages, source context, and paper text are sent to the server for generation, chat, explanations, or narration and may be passed to the configured model. Search queries and source requests reach external services. The server operator can inspect process memory and logs; job results remain in memory for reconnect, with per-client completed-history pruning. Restarting the server clears that transient state. There is no server-side user archive or conversation database.

## Client identity and API invariants

`index.html` creates a random consumer ID and persists it under `daily-signal-consumer-id-v1`. It falls back to session storage or an ephemeral ID when persistent storage is unavailable. IDs must match `[A-Za-z0-9_-]{16,64}`. Tabs in the same browser profile and origin normally share this ID, storage, and ongoing generation; a phone or different profile has a separate identity. Different hostnames, schemes, or ports create different storage origins, even when they reach the same server.

- `/api/generate` validates `client_id`, copies server model configuration into request-owned configuration, and creates a job owned by that client.
- `/api/current` validates `client_id` and selects the newest job only from that client's namespace. New clients receive no existing paper.
- `/api/status` and `/api/cancel` validate `client_id` and use the shared `owned_job` check. Another client's job is indistinguishable from a nonexistent job (404).
- Streaming `/api/chat` and `/api/narration` register cancellation state with a validated `(client_id, request_id)` pair. Cancellation endpoints use the same validation/key construction. A request ID alone cannot cancel another client's task.
- Explanations and legacy non-streaming chat are request-scoped computations over explicitly submitted context; the server does not retrieve a global conversation or infer the current paper from another client.
- Model calls receive fresh explicit message lists; conversations are not accumulated in global state. Public-source caches return copies so one task's article processing cannot mutate another task's retrieved input.
- Edition switches stop old chat/narration playback and requests. Late chat/narration results are guarded against writing into another edition. Explanation responses that no longer match their initiating edition, passage, and scope are discarded.
- Notification clicks target the originating service-worker client and saved edition; workers do not cache application pages or API data.

## Trust model

The consumer ID is an opaque client namespace supplied by the browser, not an authenticated account. Ownership checks prevent accidental cross-client mixing and reject other namespaces when the supplied IDs differ. They do not establish authenticated tenant security: someone who obtains or deliberately reuses another consumer's ID can impersonate that namespace. Browser profiles shared by people also share local app data. Browser storage clearing/eviction can remove the archive; it is not a server backup.

`--lan` exposes an unauthenticated backend to reachable hosts. Use a trusted network, or put authenticated access and HTTPS in front of it before relying on this as a hostile multi-user deployment. Adding accounts or server-side durable user storage requires a separate authenticated ownership model; do not treat the current consumer ID as an account credential.

## Requirements for changes

Preserve these boundaries when adding features: client-owned records remain browser-local; transient shared registries always include the owning client; job reads/cancels go through ownership checks; generated client content never enters the shared public-source cache; and asynchronous UI results must remain scoped to their originating edition/request. Review new endpoints and background tasks for these invariants. Request-scoped endpoints may use submitted context only, not any process-wide “current user” or “current edition.”
