# opencode-agent — tasks

Deploying and hardening the OpenCode agent-harness sandbox on Daytona. Mirrors the
"OpenCode" sections from root `handoff.md` and Phase 3 of root `tasks.md`, backfilled
as done, plus this session's startup-hardening work.

## Done

- [x] Implement `deploy_opencode.py` (repo root, canonical script):
  - Reads `ollama_info.txt` for `OLLAMA_ENDPOINT`/`OLLAMA_TOKEN` (fails fast with a clear
    error if missing — run `serve_ollama_main.py` first).
  - Builds an OpenCode provider config pointing at Ollama's OpenAI-compatible `/v1` API,
    with the `x-daytona-preview-token` header injected, and writes it to `/tmp/opencode.json`
    inside the OpenCode sandbox.
  - Creates a 2vCPU / 4GB RAM CPU sandbox.
  - Installs OpenCode via `curl -fsSL https://opencode.ai/install | bash` (NOT
    `npm install -g opencode` — that's a different, wrong package; fallback is
    `npm install -g opencode-ai` if the install script fails).
- [x] **Startup hardening (this session)** — fixes the original "preview 502" blocker:
  - `discover_opencode_binary()` — explicitly searches known install locations
    (`$HOME/.local/bin`, `$HOME/.opencode/bin`, `$HOME/.npm-global/bin`, `/usr/local/bin`)
    instead of trusting a bare `command -v opencode`, because PATH wasn't reliably set in
    all execution contexts. Root cause of the original 502: the wrapper script's PATH did
    not include the directory where OpenCode actually got installed
    (`/usr/local/share/nvm/current/bin/opencode` in observed sandboxes).
  - **Launch command is forced to `opencode serve --port <PORT>`, never `opencode start`.**
    `opencode start` is NOT a server-start command in this OpenCode version (v1.1.35) — it's
    parsed as `opencode [project]` (the TUI's positional "project path" argument), so passing
    `start` as if it were a subcommand makes OpenCode try to `cd` into a literal directory
    named `start`, which fails immediately (`Error: Failed to change directory to
    /home/daytona/start`) and exits. **This was a real bug in the original script** (it tried
    `start` first believing tasks.md's old wording), now fixed to always use `serve`.
  - `supports_port_flag()` — probes `opencode serve --help` for a `--port` flag before
    relying on it (defensive; v1.1.35 does support `--port`).
  - Removes any stale `opencode_info.txt` at the start of every deploy attempt, so a failed
    run never leaves behind stale/misleading credentials for `agent_client.py` to pick up.
  - Local health check now execs into the sandbox and greps `/tmp/opencode.log` for the
    actual listening port, then curls that port directly — previously it assumed the
    configured port always matched what OpenCode actually bound to.
  - Preview + local health checks reject any HTML-looking response body (see
    `api-discovery/tasks.md` — this check needs one more update, see Open items below).
- [x] Diagnosed and fixed the literal "OpenCode preview 502" from the original handoff:
  root cause was PATH/binary-discovery, not port binding or a Daytona proxy issue. Once the
  binary was found correctly and `serve` was used (not `start`), the process started reliably
  and both local and preview HTTP health checks passed (HTTP 200).

## Open (in progress this session)

- [ ] **`deploy_opencode.py`'s health-check functions still poll the wrong path.**
  They currently check `/v1/models` (an OpenAI-style path) for JSON-vs-HTML, but the real
  OpenCode API doesn't expose `/v1/*` at all — see `../api-discovery/tasks.md` for the actual
  routes. Update `local_health_ready()` and `preview_ready()` in `deploy_opencode.py` to poll
  `GET /global/health` instead, and check for `"healthy":true` in the JSON body rather than
  just "not HTML".
- [ ] Once health checks are fixed, re-run `python deploy_opencode.py` end-to-end and confirm
  it writes `opencode_info.txt` successfully (it currently does NOT exist because deploy
  intentionally aborts before writing it when health checks fail).
- [ ] `agent_client.py` needs to be rewritten to use the real session/message API — see
  `../api-discovery/tasks.md` for exact endpoint shapes. Do this together with the health
  check fix above since they touch the same underlying misunderstanding.

## Context for next agent

- **Canonical script**: `deploy_opencode.py` at repo root.
- **OpenCode version observed**: 1.1.35 (installed via the official install script into
  `/usr/local/share/nvm/current/bin/opencode` in the sandboxes seen so far — this path can
  vary, always use `discover_opencode_binary()`'s logic rather than hardcoding).
- **Correct launch invocation**: `opencode serve --port <PORT>` — confirmed via
  `opencode serve --help`. Do NOT use `opencode start`.
- **Current/most-recent OpenCode sandbox** (check for a live one — sandboxes are ephemeral
  and get cleaned up between sessions): `d48039ac-b9a0-48ee-b636-0e38e82ac9ad`, port 3000,
  process was alive and serving. **There is no current `opencode_info.txt`** — you'll need to
  redeploy or use `sb.get_preview_link(3000)` against that sandbox ID directly to get a fresh
  preview token if it's still running (Daytona SDK: `Daytona(DaytonaConfig()).get(<id>)`).
- **Verify command** (once health checks are fixed):
  `cd /home/graphedge/projects/open-infer-daytona && .venv/bin/python deploy_opencode.py`
  then `.venv/bin/python agent_client.py "say hello"`.
- **Logs**: `logs/deploy_opencode-*.log` at repo root, plus inside the sandbox itself:
  `/tmp/opencode.log` (stdout/stderr of the server process) and
  `~/.local/share/opencode/log/*.log` (OpenCode's own structured logs, timestamped).
- **Storage for debugging**: OpenCode persists session/message state under
  `~/.local/share/opencode/storage/{session,message,part}/...` as JSON files inside the
  sandbox — useful for inspecting what a test message actually did even if the HTTP response
  timed out.
