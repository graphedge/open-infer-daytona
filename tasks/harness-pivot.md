# Harness Pivot: Sonnet Review → Codex CLI Decision

**Date:** 2026-07-08  
**Decision:** Option B — **Codex CLI** (local inference via existing Ollama)  
**Status:** First checkpoint ready for validation

---

## 🎯 Revised Recommendation: Codex CLI

### Key findings from Unsloth Codex docs
1. **Codex CLI connects to any OpenAI-compatible local server** via `~/.codex/config.toml` — just needs `wire_api = "responses"`, `base_url`, `model`, `requires_openai_auth = false`.
2. **Ollama v0.13.3+ natively serves `/v1/responses`** (confirmed via docs.ollama.com) — stateless variant, no `previous_response_id` chaining, but sufficient for single-turn agent calls.
3. **Gemma 4 exists as `unsloth/gemma-4-26B-A4B-it-GGUF`** — a **MoE model: 26B total params, 4B active** — exactly the "CPU class" sweet spot: much cheaper than dense 26B, comparable inference cost to dense ~4B.
4. Codex needs **GGUF** specifically for Responses wire protocol — **but Ollama already exposes `/v1/responses` directly**, so skip llama.cpp/Unsloth Studio entirely. Point Codex straight at **your existing, already-validated Ollama sandbox**.

### Why Codex CLI beats Goose now

| Criterion | Goose (prior pick) | **Codex CLI (revised)** |
|---|---|---|
| New server needed | No (Ollama reused) | No (Ollama reused) |
| New agent binary | Goose CLI (new install) | Codex CLI (`npm install -g @openai/codex`) |
| Config complexity | provider YAML | Single `config.toml` + profile file |
| Protocol maturity | OpenAI-compatible chat | **Official OpenAI Responses API, directly supported by Ollama** |
| Tooling ecosystem | Smaller | Backed by OpenAI, actively maintained |
| Model reuse | Any Ollama model | Gemma 4 MoE explicitly documented reference |

---

## ✅ First 30-min Checkpoint

**Objective:** validate Codex CLI + Ollama `/v1/responses` + Gemma 4 end-to-end

1. **Confirm Ollama version ≥ 0.13.3:**
   ```bash
   /home/daytona/.ollama-install/bin/ollama --version
   ```
   If < 0.13.3, upgrade by re-running install + `ollama serve` restart.

2. **Pull Gemma 4 MoE via HF fallback pattern** (existing `serve_ollama_main.py` logic):
   ```bash
   /home/daytona/.ollama-install/bin/ollama pull unsloth/gemma-4-26B-A4B-it-GGUF
   ```

3. **Install Codex CLI in same sandbox:**
   ```bash
   npm install -g @openai/codex
   ```

4. **Write `~/.codex/config.toml`:**
   ```toml
   oss_provider = "local_ollama"
   [model_providers.local_ollama]
   base_url = "http://localhost:11434/v1"
   env_key = "OLLAMA_KEY"
   wire_api = "responses"
   requires_openai_auth = false
   
   [profiles.local_ollama]
   model_provider = "local_ollama"
   model = "unsloth/gemma-4-26B-A4B-it-GGUF"
   ```

5. **Test single prompt:**
   ```bash
   export OLLAMA_KEY="dummy"
   codex --oss --profile local_ollama
   ```
   Send a short prompt (e.g., "say hello"). Expect text response from Gemma 4.

**Success condition:** Codex returns a non-empty response from Gemma 4 without timeout or auth errors.

**Remaining risk to test:** Verify tool-calling works under stateless Responses API for real agentic tasks (single-turn agent calls may require more than stateless `input`/`output` semantics).

---

## Migration Path

If checkpoint succeeds:
1. Deprecated `deploy_opencode.py` → move to `archive/`
2. Revise `serve_ollama_main.py` to ensure model pull includes Gemma 4 (update default or add config)
3. New `deploy_codex.py` (analogous to `deploy_opencode.py`): co-locate Codex CLI + Ollama on one sandbox
4. New `codex_client.py` or adapt `agent_client.py` to use Codex CLI subprocess or direct prompt loop
5. Update `handoff.md` + `AGENTS.md` with new harness choice
6. Commit with `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`

---

## Archive: Prior Analysis

### Initial Recommendation (before Unsloth docs review): Option C — Goose Agent

**Context:** First Sonnet pass recommended Goose over OpenCode due to streaming/proxy blockers.

**Reasoning then:**
- OpenCode had custom `/session/{id}/message` protocol — undocumented, no evidence of tool support
- Goose could be co-located with Ollama on same sandbox, bypassing Daytona preview proxy
- Codex CLI appeared cloud-only (error in prior web search)

**Why this was incomplete:**
- Missed that **Codex CLI now has official local model support** via Unsloth integration
- Did not discover **Ollama's native `/v1/responses` endpoint** (v0.13.3+) — would have short-circuited the "need Unsloth Studio" assumption
- Did not realize Codex CLI is now backed by OpenAI's official Responses API, a more stable protocol than custom router approaches

**Lessons:**
- Always verify cloud-vs-local capability status with latest official docs, not prior assumptions
- Ollama's OpenAI compatibility surface area is broader than expected (chat + responses)
- Gemma 4 MoE is a stronger baseline model than SmolLM2-135M for agentic tasks

---

## Next Steps

1. **Run checkpoint** (30 min) → capture results in logs
2. **If success:** proceed to migration path (deploy_codex.py, client refresh)
3. **If failure:** troubleshoot `/v1/responses` compatibility or fall back to Goose (archive reasoning above)
4. **If tool-calling fails:** may need to patch Ollama's responses endpoint or use Codex's tool fallback mode

