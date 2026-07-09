# ollama-inference — tasks

Deploying and verifying the Ollama inference sandbox on Daytona. Mirrors the "Ollama"
sections from root `handoff.md` and Phase 2 of root `tasks.md`, backfilled as done.

## Done

- [x] Implement `serve_ollama_main.py` (repo root, canonical script — not `serve_ollama.py`
  or anything in `archive/`):
  - Creates a 4vCPU / 8GB RAM / 30GB-disk CPU sandbox (`ephemeral=True`, `auto_stop_interval=0`)
  - Installs Ollama with a **resilient two-path install**:
    1. Try `curl -fsSL https://ollama.com/install.sh | sh`
    2. If that fails, stream the GitHub release tarball directly into
       `$HOME/.ollama-install` via `curl | tar --zstd -xf -` (excludes CUDA/vulkan libs —
       CPU only), because `ollama.com`/`registry.ollama.ai` are **blocked from Daytona
       sandboxes** (connection reset). See `ollama-postmortem.md` for the full failure history.
  - Starts `ollama serve` via a **long-lived session wrapper** (`bash` script backgrounds
    the process, writes a PID file, then loops `sleep 60` forever in the foreground) —
    this is required because transient `sb.process.exec()` calls and bare `nohup` get
    killed when the shell exits (see `ollama-postmortem.md`).
  - Pulls the default model **from HuggingFace, not the Ollama registry** (registry blocked):
    `huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF` (135M params — deliberately tiny
    for fast CPU inference). Override with env var `OLLAMA_MODEL`.
  - Polls local health (`curl localhost:11434/api/tags`) before pulling, and preview health
    (via Daytona preview URL + `x-daytona-preview-token` header) before declaring ready.
  - Writes `OLLAMA_ENDPOINT`, `OLLAMA_TOKEN`, `SANDBOX_ID` to `ollama_info.txt` (repo root,
    gitignored).
- [x] Verified via `query_ollama.py` (repo root) — does a health check (`/api/tags`) then a
  real chat completion (`/api/chat`) and prints the model's reply.
- [x] `recover_ollama.py` — can scan existing sandboxes to recover endpoint/token if
  `ollama_info.txt` is lost but the sandbox is still running.
- [x] `cleanup_sandboxes.py --all` — deletes all sandboxes; without `--all` it preserves
  sandbox IDs referenced in `ollama_info.txt`/`opencode_info.txt`.

## Open / not needed right now

- [ ] Nothing outstanding for Ollama itself. If it ever goes dead (Auth0 HTML response or
  connection error from `query_ollama.py`), just re-run `python serve_ollama_main.py` — it's
  idempotent (creates a fresh sandbox each time).

## Context for next agent

- **Canonical script**: `serve_ollama_main.py`. Do NOT use `serve_ollama.py` (legacy) or
  anything under `archive/setup_ollama_*.py`.
- **Verify command**: `cd /home/graphedge/projects/open-infer-daytona && .venv/bin/python query_ollama.py`
  Expected output ends with `Ollama is responding.` and a short model reply.
- **Current live sandbox** (check `ollama_info.txt` for the *actual* current value — this
  changes every redeploy): as of this session, `947233af-df33-4bf6-ade1-933d9b3a6e2e`,
  endpoint `https://11434-947233af-df33-4bf6-ade1-933d9b3a6e2e.daytonaproxy01.net`.
- **Known blockers** (all solved, kept for reference):
  1. `registry.ollama.ai` blocked — use HF pull path instead (`ollama pull huggingface.co/...`).
  2. Sandbox root disk is only ~3GB overlay — must stream-install, never download the full
     tarball to `/tmp` first.
  3. `ollama.com/install.sh` sometimes blocked too — GitHub binary fallback handles this.
- **Model override**: `export OLLAMA_MODEL="huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF"`
  (this is already the default, only needed if you want a different model).
- **Logs**: `logs/serve_ollama-*.log` (timestamped, newest = most recent run). On failure,
  diagnostics (`ps`, `df -h`, service log, local curl) are auto-appended via `deploy_log.py`'s
  `dump_sandbox_diagnostics`.
- **Full path reference**: `/home/graphedge/projects/open-infer-daytona/serve_ollama_main.py`,
  `/home/graphedge/projects/open-infer-daytona/query_ollama.py`,
  `/home/graphedge/projects/open-infer-daytona/ollama-postmortem.md`.
