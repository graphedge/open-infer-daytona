# Handoff: open-infer-daytona

**Date:** 2026-07-06  
**Status:** Paused mid-flight. Ollama inference works; OpenCode process starts fine now (original 502 fixed), but the client code was calling the wrong API paths entirely (`/api/*`, `/v1/*` don't exist in this OpenCode version). The real API was discovered this session (`/global/health`, `/session`, `/session/{id}/message`, `/doc` for the OpenAPI spec) but wiring it up end-to-end is not finished — a test message POST timed out and needs investigation.

---

## What this project is

Deploy an autonomous coding agent on **Daytona** where:

| Layer | Where | Role |
|-------|-------|------|
| **Cursor CLI** | Local | Orchestrator — deploy scripts, debugging, repo work |
| **OpenCode** | Daytona sandbox | **Agent harness** — tools, code execution, prompts |
| **Ollama** | Daytona sandbox | Inference only (OpenAI-compatible `/v1`) |

**Chosen path (hybrid):** two CPU sandboxes (Ollama + OpenCode). Defer `spec1.md` 31B/GPU until quota allows.

Read first: [`AGENTS.md`](AGENTS.md), [`.cursor/rules/daytona-opencode.mdc`](.cursor/rules/daytona-opencode.mdc), [`ollama-postmortem.md`](ollama-postmortem.md).

**For granular, subject-organized task tracking** (with enough embedded context for a
lightweight model to resume without re-discovering facts), see [`tasks/README.md`](tasks/README.md)
— folders for `ollama-inference/`, `opencode-agent/`, `api-discovery/` (this session's key
finding), and `housekeeping/`.

---

## What is done

### Docs & conventions
- [`AGENTS.md`](AGENTS.md) — agent entry point
- [`.cursor/rules/daytona-opencode.mdc`](.cursor/rules/daytona-opencode.mdc) — always-on Cursor rule
- [`handoff.md`](handoff.md) — this file

### Logging (`deploy_log.py`)
- Timestamped logs under `logs/` (gitignored)
- `log_exec`, `log_poll`, `dump_sandbox_diagnostics`, `discover_binary`
- All canonical deploy scripts instrumented

### Ollama (Phase 2 — **working**)
- **Canonical script:** [`serve_ollama_main.py`](serve_ollama_main.py)
- Persistence: long-lived session + foreground wrapper (`while true; sleep 60`)
- Install: GitHub streamed tar (CPU-only, excludes CUDA/vulkan) — `ollama.com` install script **blocked** from sandboxes
- Default model changed from `gemma4:4b` (does not exist / registry blocked) to:
  - `huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF` (135M, pulled via HF — **works**)
- [`query_ollama.py`](query_ollama.py) — health + chat verification (**passing** last run)
- [`recover_ollama.py`](recover_ollama.py) — scan sandboxes for running Ollama
- [`cleanup_sandboxes.py`](cleanup_sandboxes.py) — delete sandboxes (`--all` skips info-file IDs unless files removed)

### OpenCode (Phase 3 — **partial**)
- [`deploy_opencode.py`](deploy_opencode.py) — implemented: reads `ollama_info.txt`, writes `/tmp/opencode.json`, session wrapper
- Startup hardening added:
  - resolves opencode binary path explicitly (`discover_binary`)
  - forces `opencode serve --port ...` (not `start`; `start` is parsed as a project path and exits)
  - exports PATH + `OPENCODE_PORT`/`PORT` in wrapper
  - validates API responses are not HTML before writing `opencode_info.txt`
  - removes stale `opencode_info.txt` before each deploy attempt
- Install fixed: `curl https://opencode.ai/install | bash` (not `npm install -g opencode` — wrong package)
- **`opencode_info.txt` does not exist yet** — deploy has not completed successfully

### Client (Phase 4 — **stub ready**)
- [`agent_client.py`](agent_client.py) — health check + readline loop + prompt via `/api/chat` and `/v1/chat/completions`
- Untested end-to-end (needs live OpenCode)

### Repo hygiene (partial)
- `setup_ollama_*.py` moved to [`archive/`](archive/)
- `.gitignore` updated (`logs/`, `*_info.txt`, `.env`, `.venv/`)
- [`tasks.md`](tasks.md) **not updated** — checkboxes stale
- **Nothing committed** from this session's work

---

## Current sandboxes (latest known)

| Sandbox ID | Role | State |
|------------|------|-------|
| `947233af-df33-4bf6-ade1-933d9b3a6e2e` | **Ollama** | STARTED — credentials in `ollama_info.txt` |
| `d48039ac-b9a0-48ee-b636-0e38e82ac9ad` | **OpenCode** (attempt) | STARTED — `serve` running on port 3000, but `/api/*` and `/v1/*` return SPA HTML |

**Before creating new sandboxes:** run `python cleanup_sandboxes.py --all` (remove `ollama_info.txt` / `opencode_info.txt` first if you want to delete everything). Account CPU limit is **10 vCPU** — stale sandboxes caused `Total CPU limit exceeded` earlier.

---

## Verify Ollama is still alive

```bash
cd /home/graphedge/projects/open-infer-daytona
.venv/bin/python query_ollama.py
```

Expected: `Ollama is responding.` + a short model reply.

If dead (Auth0 HTML / connection error): redeploy with `python serve_ollama_main.py` and watch `logs/serve_ollama-*.log`.

---

## Known blockers & lessons

### 1. `registry.ollama.ai` blocked from Daytona sandboxes
- `ollama pull gemma2:2b` / `gemma4:4b` → connection reset
- **Workaround:** pull via HuggingFace path:
  ```bash
  /home/daytona/.ollama-install/bin/ollama pull huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF
  ```
- `serve_ollama_main.py` should fail pull on `Error:` in log (fixed) but default model pull may still fail on fresh deploy until HF path is wired into install flow

### 2. Sandbox root disk is only ~3GB overlay
- Full Ollama tarball (~1.3GB compressed) fills disk if downloaded to `/tmp` first
- **Fix in place:** stream `curl | tar --zstd` with CUDA/vulkan excludes into `$HOME/.ollama-install`
- `Resources(disk=30)` does **not** enlarge the overlay — only affects volume API if mounted

### 3. `ollama.com` install script blocked (connection reset)
- Same network policy as registry — use GitHub binary install in `serve_ollama_main.py`

### 4. OpenCode npm package name
- **Wrong:** `npm install -g opencode` (404 — different project)
- **Right:** `opencode-ai` or `curl -fsSL https://opencode.ai/install | bash`

### 5. OpenCode API route mismatch (current blocker)
- Latest deploys start OpenCode successfully and preview returns `200`, but expected API endpoints (`/api/*`, `/v1/*`) return SPA HTML instead of JSON.
- Likely causes to investigate:
  - OpenCode 1.1.35 `serve` mode exposes web shell, not external JSON API intended for `agent_client.py`
  - API may require a different mode/flag/protocol (ACP/attach/session streaming) rather than `/v1/chat/completions`
  - Existing client assumptions (`/api/chat`, `/v1/chat/completions`) likely stale for this OpenCode version
- **First debug step on sandbox `22095c15-...`:**
  ```python
  # from local machine
  sb.process.exec("cat /tmp/opencode.log; ps aux | grep opencode; ss -tlnp | grep 3000")
  ```

### 6. Secrets
- `.env` has `DAYTONA_API_KEY` (was committed historically — rotate if repo is shared)
- `ollama_info.txt` contains preview tokens — gitignored but present locally
- Do not commit `*_info.txt`, `.env`, or `logs/`

---

## Canonical scripts (use these, not archive/)

| Script | Purpose |
|--------|---------|
| [`serve_ollama_main.py`](serve_ollama_main.py) | Deploy Ollama sandbox |
| [`deploy_opencode.py`](deploy_opencode.py) | Deploy OpenCode sandbox |
| [`query_ollama.py`](query_ollama.py) | Verify inference |
| [`agent_client.py`](agent_client.py) | Talk to OpenCode |
| [`cleanup_sandboxes.py`](cleanup_sandboxes.py) | Delete sandboxes |
| [`recover_ollama.py`](recover_ollama.py) | Recover Ollama endpoint from existing sandbox |
| [`deploy_log.py`](deploy_log.py) | Shared logging helpers |

Legacy: [`serve_ollama.py`](serve_ollama.py), [`archive/setup_ollama_*.py`](archive/) — do not use.

---

## Next steps (recommended order)

1. **Confirm Ollama:** `python query_ollama.py`
2. **Debug OpenCode sandbox** `d48039ac-b9a0-48ee-b636-0e38e82ac9ad`:
   - Use latest sandbox instead (`d48039ac-b9a0-48ee-b636-0e38e82ac9ad`)
   - Verify whether OpenCode exposes machine API in current version, and identify supported request protocol for automation
   - Reconcile `agent_client.py` with supported OpenCode interface
3. **Re-run or fix deploy:** `python deploy_opencode.py` → should write `opencode_info.txt`
4. **Smoke test:** `python agent_client.py "say hello"`
5. **E2E task** (from `tasks.md`): FastAPI primes app + preview link
6. **Housekeeping:**
   - Keep [`tasks.md`](tasks.md) checkboxes aligned as phases progress
   - Keep [`AGENTS.md`](AGENTS.md) model defaults aligned with runtime
   - Commit when ready (exclude secrets)
   - Rotate Daytona API key if needed

---

## Environment

```bash
cd /home/graphedge/projects/open-infer-daytona
python -m venv .venv   # already exists
.venv/bin/pip install daytona openai requests python-dotenv
# .env needs DAYTONA_API_KEY
```

Optional override:
```bash
export OLLAMA_MODEL="huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF"
export OPENCODE_PORT=3000
```

---

## Log files to check on failure

Always check `logs/` first — most recent file per script name:

```
logs/serve_ollama-*.log
logs/deploy_opencode-*.log
logs/query_ollama-*.log
logs/cleanup_sandboxes-*.log
```

On deploy failure, diagnostics are appended automatically: `ps`, disk (`df -h`), service log, pid check, local curl.

---

## Architecture diagram

```
Cursor CLI (local)
  ├── serve_ollama_main.py  →  Ollama sandbox  (inference)
  ├── deploy_opencode.py    →  OpenCode sandbox (agent harness)
  └── agent_client.py       →  OpenCode preview URL
                                    └── HTTP → Ollama preview URL /v1
```

---

## Deferred (do not pursue yet)

- `spec1.md` — single-sandbox Gemma 31B + dual providers
- [`serve_vllm.py`](serve_vllm.py) — GPU quota is 0
- Custom Docker image with Ollama pre-baked (good future optimization)
