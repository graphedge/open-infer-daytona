# housekeeping — tasks

Repo hygiene, documentation sync, secrets handling, and committing. Mirrors the "Repo
hygiene" section from root `handoff.md` and the general housekeeping items from root
`tasks.md`.

## Done

- [x] Moved legacy `setup_ollama_*.py` variants into `archive/` — canonical scripts are
  `serve_ollama_main.py`, `deploy_opencode.py`, `query_ollama.py`, `agent_client.py`,
  `cleanup_sandboxes.py`, `recover_ollama.py`, `deploy_log.py` (all at repo root).
- [x] `.gitignore` updated to exclude `logs/`, `*_info.txt`, `.env`, `.venv/`.
- [x] Root `tasks.md` checkboxes brought up to date this session (Phase 2 Ollama items
  marked done; Phase 3 OpenCode items marked done/in-progress accurately instead of all
  blank).
- [x] `AGENTS.md` model reference corrected — no longer says "Gemma 4 4B" (that was never
  actually used); now reflects the real default,
  `huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF`.
- [x] `handoff.md` updated with current sandbox IDs, current blocker (API path mismatch,
  not the original 502 — that's fixed), and next-steps ordering.
- [x] This `tasks/` folder created and backfilled (this session) — subject-organized,
  self-contained task tracking to supplement the flat root `tasks.md`.
- [x] Stale/failed sandboxes cleaned up via `cleanup_sandboxes.py` during this session's
  iterative debugging (kept only the live Ollama sandbox + the OpenCode sandbox being
  actively debugged).

## Open

- [ ] **Nothing has been committed yet.** `git status` shows the working tree has extensive
  uncommitted changes: new canonical scripts (`agent_client.py`, `cleanup_sandboxes.py`,
  `deploy_log.py`, `deploy_opencode.py`, `serve_ollama_main.py`, `AGENTS.md`, `handoff.md`,
  `.cursor/`, `archive/`, `tasks/`), modifications to `query_ollama.py`, `recover_ollama.py`,
  `tasks.md`, `.gitignore`, `ollama_info.txt`, and deletions of legacy scripts
  (`setup_ollama_*.py`, `get-pip.py`). **Before committing**:
  1. Double-check `ollama_info.txt` is `.gitignore`'d (it is, per `.gitignore` — but git
     shows it as "M" meaning it was tracked historically; consider `git rm --cached
     ollama_info.txt` so it stops being tracked going forward, since it contains a live
     preview token).
  2. Verify `.env` (contains `DAYTONA_API_KEY`) is NOT staged.
  3. Verify `logs/` is NOT staged.
  4. Write a commit message describing the OpenCode startup hardening + API discovery work.
- [ ] **Rotate the Daytona API key** if this repo is ever shared/pushed publicly —
  `handoff.md` flags that `.env` was committed historically in the repo's past, so the key
  in current local `.env` should be treated as potentially exposed.
- [ ] Once `api-discovery` and `opencode-agent` open items are resolved (see those folders),
  do a final housekeeping pass: update root `tasks.md` Phase 3/4/5 checkboxes to fully done,
  and update `handoff.md`'s "Status" line to reflect full end-to-end success.

## Context for next agent

- **Repo root**: `/home/graphedge/projects/open-infer-daytona`
- **Never commit**: `.env`, `*_info.txt`, `logs/`, `__pycache__/` — all should already be
  gitignored; double-check with `git status --short` before any commit.
- **Canonical vs legacy**: anything under `archive/` or named `setup_ollama_*.py` /
  `serve_ollama.py` (no `_main` suffix) is legacy — do not use or maintain it.
- **Suggested commit message** (once ready): something like
  `"Harden OpenCode deploy startup, discover correct API routes, update docs and add
  subject-organized tasks/ tracker"` — adjust once the api-discovery open items are actually
  resolved, since right now the OpenCode integration is still not fully working end-to-end.
