# api-discovery — tasks

**NEW this session.** Discovering the *actual* HTTP API surface of the OpenCode server
(v1.1.35), because the original `agent_client.py`/`deploy_opencode.py` code assumed OpenAI-style
paths (`/api/chat`, `/v1/chat/completions`, `/v1/models`) that **do not exist** in this
OpenCode version. This folder documents what was verified working, what's still broken, and
exact next steps.

## Done

- [x] **Diagnosed the symptom**: every path tried — `/`, `/api/health`, `/api/session`,
  `/v1/models`, `/v1/chat/completions`, and even a deliberately made-up nonexistent path
  (`/nonexistent-route-xyz`) — all returned the **exact same 2884-byte SPA `index.html`**
  with HTTP 200. This ruled out auth/header issues (tried adding `Accept: application/json`,
  no change) and confirmed it's a **routing/path-prefix problem**, not a server or auth bug.
- [x] **Found the real API** via two sources:
  1. Official docs: https://opencode.ai/docs/server/ — documents `opencode serve` and lists
     endpoints under paths like `/global/health`, not `/api/*`.
  2. The running server's own OpenAPI 3.1 spec, fetched live:
     `curl http://localhost:3000/doc` (from inside the sandbox) returns the full spec as JSON.
- [x] **Verified working, real JSON responses** (tested against live sandbox
  `d48039ac-b9a0-48ee-b636-0e38e82ac9ad`, port 3000, from inside the sandbox via
  `sb.process.exec(...)`):
  - `GET /global/health` → `{"healthy":true,"version":"1.1.35"}`
  - `GET /doc` → full OpenAPI 3.1 JSON spec (used to enumerate every route, see below)
  - `POST /session` with body `{}` → creates a session, returns real JSON, e.g.:
    ```json
    {"id":"ses_0c590304cffej0kzgDdihnfxh0","slug":"tidy-moon","version":"1.1.35",
     "projectID":"global","directory":"/home/daytona",
     "title":"New session - 2026-07-07T02:37:14.035Z", ...}
    ```
- [x] **Captured the request schema** for sending a message, from the OpenAPI spec
  (`/session/{sessionID}/message`, POST), required field is `parts`:
  ```json
  {
    "model": {"providerID": "ollama", "modelID": "huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF"},
    "parts": [{"type": "text", "text": "Say hello in five words or fewer."}]
  }
  ```
  (`model` is optional per schema but should be passed explicitly since our config sets
  a non-default provider; `parts` is required and is an array of typed parts —
  `TextPartInput`, `FilePartInput`, `AgentPartInput`, `SubtaskPartInput`).
- [x] **Full list of every route** exposed by this OpenCode server (captured from `/doc`,
  useful so nobody needs to re-fetch it unless the OpenCode version changes):
  ```
  /agent [get]
  /auth/{providerID} [put]
  /command [get]
  /config [get, patch]
  /config/providers [get]
  /event [get]
  /experimental/resource [get]
  /experimental/tool [get]
  /experimental/tool/ids [get]
  /experimental/worktree [post, get, delete]
  /experimental/worktree/reset [post]
  /file [get]
  /file/content [get]
  /file/status [get]
  /find [get]
  /find/file [get]
  /find/symbol [get]
  /formatter [get]
  /global/dispose [post]
  /global/event [get]
  /global/health [get]
  /instance/dispose [post]
  /log [post]
  /lsp [get]
  /mcp [get, post]
  /mcp/{name}/auth [post, delete]
  /mcp/{name}/auth/authenticate [post]
  /mcp/{name}/auth/callback [post]
  /mcp/{name}/connect [post]
  /mcp/{name}/disconnect [post]
  /path [get]
  /permission [get]
  /permission/{requestID}/reply [post]
  /project [get]
  /project/current [get]
  /project/{projectID} [patch]
  /provider [get]
  /provider/auth [get]
  /provider/{providerID}/oauth/authorize [post]
  /provider/{providerID}/oauth/callback [post]
  /pty [get, post]
  /pty/{ptyID} [get, put, delete]
  /pty/{ptyID}/connect [get]
  /question [get]
  /question/{requestID}/reject [post]
  /question/{requestID}/reply [post]
  /session [get, post]
  /session/status [get]
  /session/{sessionID} [get, delete, patch]
  /session/{sessionID}/abort [post]
  /session/{sessionID}/children [get]
  /session/{sessionID}/command [post]
  /session/{sessionID}/diff [get]
  /session/{sessionID}/fork [post]
  /session/{sessionID}/init [post]
  /session/{sessionID}/message [get, post]
  /session/{sessionID}/message/{messageID} [get]
  /session/{sessionID}/message/{messageID}/part/{partID} [delete, patch]
  /session/{sessionID}/permissions/{permissionID} [post]
  /session/{sessionID}/prompt_async [post]
  /session/{sessionID}/revert [post]
  /session/{sessionID}/share [post, delete]
  /session/{sessionID}/shell [post]
  /session/{sessionID}/summarize [post]
  /session/{sessionID}/todo [get]
  /session/{sessionID}/unrevert [post]
  /skill [get]
  /tui/append-prompt [post]
  /tui/clear-prompt [post]
  /tui/control/next [get]
  /tui/control/response [post]
  /tui/execute-command [post]
  /tui/open-help [post]
  /tui/open-models [post]
  /tui/open-sessions [post]
  /tui/open-themes [post]
  /tui/publish [post]
  /tui/select-session [post]
  /tui/show-toast [post]
  /tui/submit-prompt [post]
  /vcs [get]
  ```

## Open — top priority for next agent

- [ ] **UNRESOLVED: `POST /session/{sessionID}/message` timed out.** When tested end-to-end
  (create session → send message with the Ollama model/parts payload above), the request hung
  and `curl -m 40` timed out with **0 bytes received** (not even a partial response — the
  connection just never completed). This was NOT re-investigated further before the session
  ended. Next steps, in order:
  1. Re-verify Ollama is still healthy: `cd /home/graphedge/projects/open-infer-daytona &&
     .venv/bin/python query_ollama.py`. If Ollama itself is dead/slow, that would fully
     explain the hang (OpenCode calling out to a dead/slow backend).
  2. If Ollama is healthy, retry the same `POST /session/{sessionID}/message` call with a much
     longer timeout (e.g. 120s) and watch `~/.local/share/opencode/log/*.log` (tail the newest
     file) and `/tmp/opencode.log` inside the OpenCode sandbox **while the request is in
     flight**, to see if OpenCode logs any outbound HTTP call to the Ollama provider or any
     error.
  3. Check whether the small model (SmolLM2-135M) name/format is actually accepted by
     OpenCode's `@ai-sdk/openai-compatible` provider — it's possible the `modelID` string
     (`huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF`) needs different escaping/encoding
     when embedded in OpenCode's own provider-routing logic vs. Ollama's native API (which
     accepts it fine per `query_ollama.py`).
  4. Consider testing with `GET /session/{sessionID}/message` (list messages) after a timeout
     to see if the message was actually created server-side but the HTTP response itself never
     flushed (streaming/SSE issue) — compare with `/event` or `/global/event` (SSE endpoints)
     which might be the *intended* way to observe the reply instead of waiting on the POST
     response directly.
- [ ] Once resolved, update `../opencode-agent/tasks.md`'s corresponding open items
  (`deploy_opencode.py` health checks, `agent_client.py` rewrite) using the exact working
  request/response shapes confirmed here.
- [ ] Consider using `GET /doc` output directly at deploy time (fetch once, cache) rather than
  hardcoding this endpoint list, in case future OpenCode versions change paths again.

## Root cause of timeout (discovered in session 2)

**Session 2 findings (2026-07-06/07):**
- The `POST /session/{id}/message` timeout was caused by a **TLS connection reset** when OpenCode tried to reach Ollama via the Daytona preview proxy (`https://11434-947233af-df33-4bf6-ade1-933d9b3a6e2e.daytonaproxy01.net/v1/chat/completions`).
- **Key evidence**:
  - Ollama streaming works fine when called from outside the sandboxes (local machine) with correct `x-daytona-preview-token` header.
  - From within the OpenCode sandbox, the same preview URL raises a TLS handshake error: `error:00000000:lib(0)::reason(0); Recv failure: Connection reset by peer`.
  - Non-streaming requests and general internet egress from the OpenCode sandbox work fine (tested to `https://github.com`, `https://app.daytona.io`).
- **Likely explanation**: Daytona's preview proxy may not support streaming responses or long-held connections across sandboxes, or there's a connection-pooling/timeout issue specific to streaming within Daytona's network boundary.
- **Next investigation path**:
  - Test if non-streaming (unary) request to Ollama works from OpenCode sandbox (i.e., without `stream: true`).
  - If unary works, use that for now and accept slower response times (no token-by-token streaming).
  - If even unary fails, suspect a provider-configuration issue in OpenCode (e.g., `baseURL` mismatch, auth header format).
  - Check if OpenCode v1.2+ has proxy streaming fixes.

## Context for next agent

- **Test sandboxes (may still be running)**:
  - OpenCode: `d48039ac-b9a0-48ee-b636-0e38e82ac9ad` (port 3000)
  - Ollama: `947233af-df33-4bf6-ade1-933d9b3a6e2e` (port 11434)
- **If redeploying**: remember the `/start` binary bug is fixed; `deploy_opencode.py` now forces `opencode serve --port N`.
- **How tests were run**: inside the sandbox via `sb.process.exec("curl ...")` (Python + `daytona` SDK) OR from outside via preview URL + `x-daytona-preview-token` header. Both methods confirmed to reach their targets; the issue is mid-proxy streaming only.
- **Key files to update once this is resolved**: `/home/graphedge/projects/open-infer-daytona/deploy_opencode.py`
  (health check functions `local_health_ready`, `preview_ready` — currently poll wrong `/v1/models` path) and
  `/home/graphedge/projects/open-infer-daytona/agent_client.py` (rewrite to use `/session` + `/session/{id}/message` with correct model ID and `parts` array).
