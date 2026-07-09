# Agent Guide: open-infer-daytona

This repo deploys an autonomous coding agent on **Daytona** using **OpenCode** (agent harness) and **Ollama** (inference).

## You are probably in Cursor CLI

Cursor CLI is the **local orchestrator** — it writes deploy scripts, provisions sandboxes, and debugs the stack. The **agent harness on Daytona is OpenCode**, not Cursor.

## Architecture

```
Cursor CLI (local)
  ├── serve_ollama_main.py  →  Ollama sandbox  (HF SmolLM2 135M inference by default)
  ├── deploy_opencode.py    →  OpenCode sandbox (agent harness)
  └── agent_client.py       →  talks to OpenCode preview URL
                                    └── calls Ollama via OpenAI-compatible API
```

## Persistent rules

Read and follow: [`.cursor/rules/daytona-opencode.mdc`](.cursor/rules/daytona-opencode.mdc)

That rule covers canonical scripts, Daytona process persistence, OpenCode config, and what is deferred.

## Task tracker

See [`tasks.md`](tasks.md) for the flat phased checklist, or [`tasks/`](tasks/) for a
subject-organized, self-contained breakdown (Ollama, OpenCode, API discovery, housekeeping) —
start with [`tasks/README.md`](tasks/README.md) if you're picking up work on a specific area.
[`ollama-postmortem.md`](ollama-postmortem.md) documents known Daytona pitfalls.

## Quick start (when sandboxes are up)

1. `python query_ollama.py` — verify inference
2. `python deploy_opencode.py` — deploy OpenCode (needs ollama_info.txt)
3. `python agent_client.py` — interact with OpenCode

See [`handoff.md`](handoff.md) for current status, blockers, and sandbox IDs.
