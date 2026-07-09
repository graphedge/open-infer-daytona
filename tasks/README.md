# tasks/ — Subject-organized task tracker

This folder supplements the root-level `tasks.md`, `handoff.md`, and `AGENTS.md` with
**self-contained, per-subject task files**. Each `tasks/<subject>/tasks.md` is written so
that a smaller/cheaper model (e.g. a Haiku-class model) can open **just that one file**
and resume work without needing the rest of the session history.

## How to use this folder (for any agent, especially lightweight models)

1. Read `AGENTS.md` at the repo root first — it explains the overall architecture
   (Cursor CLI orchestrates, OpenCode is the agent harness on Daytona, Ollama is inference).
2. Pick the subject folder that matches your task:
   - `ollama-inference/` — deploying/verifying the Ollama sandbox
   - `opencode-agent/` — deploying/hardening the OpenCode sandbox
   - `api-discovery/` — the correct OpenCode HTTP API surface (routes, schemas, known bugs)
   - `housekeeping/` — docs, repo hygiene, committing, secret rotation
3. Open that folder's `tasks.md`. Each file has:
   - `- [x]` items already done (with enough detail you don't need to redo them)
   - `- [ ]` items still open — do these next, top to bottom, unless marked BLOCKED
   - A **"Context for next agent"** section with concrete facts (sandbox IDs, verified
     commands, schemas, exact error messages) so you don't have to re-discover anything
4. Sandbox IDs and endpoints change every time scripts are re-run — always double check
   `ollama_info.txt` / `opencode_info.txt` (gitignored, local only) for the *current* live
   values before trusting an ID written in a task file from a past session.
5. Update the relevant `tasks.md` (`[ ]` → `[x]`, add new facts to "Context for next agent")
   as you complete work, so the next agent (of any size) benefits.

## Relationship to other docs

- `handoff.md` (repo root) — the live, single-page "what's the current status / what's
  blocked right now" doc. Updated each session. It is the fastest way to see the big picture.
- `tasks.md` (repo root) — the original flat phased checklist (Phase 1–5). Still accurate,
  but not subject-organized and doesn't carry granular context.
- `tasks/` (this folder) — deeper, subject-organized, self-contained detail. Completed-work
  descriptions from `handoff.md` are **mirrored** here (not just linked), so each subject
  folder can be used on its own.
- `ollama-postmortem.md` — failure modes specifically for Ollama sandbox setup, referenced
  from `tasks/ollama-inference/tasks.md`.

## Current overall status (as of this session)

- Ollama: **working**. Live sandbox deployed, verified via `query_ollama.py`.
- OpenCode: **process runs, but client integration was wired to the wrong API paths**.
  This session discovered the real API (see `api-discovery/tasks.md`) but has not yet
  finished wiring `deploy_opencode.py` / `agent_client.py` to use it, and hit one unresolved
  timeout when sending a test message — that's the top priority open item.
