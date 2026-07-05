# Project: OpenCode Agent powered by Gemma 4 on Daytona (CPU Optimized)

## Goal
Deploy an autonomous coding agent using the OpenCode SDK, powered by a self-hosted Gemma 4 4B model served via Ollama, all running on Daytona CPU infrastructure.

## Architecture
- **Inference**: Ollama running on a Daytona CPU Sandbox (serving Gemma 4 4B).
- **Agent**: OpenCode server running on a Daytona CPU Sandbox.
- **Client**: Local Python/TS script interacting with the OpenCode server.
- **Execution**: OpenCode uses Daytona's process execution to run generated code in isolated environments.

---

## Phase 1: Setup & Configuration (Local)
- [x] Install required Python packages in `.venv` (`daytona`, `openai`, `requests`, `python-dotenv`).
- [x] Create `.env` file with `DAYTONA_API_KEY` and `HF_TOKEN`.

## Phase 2: Deploy Model Inference (Ollama)
- [ ] Implement `serve_ollama.py` `(Local)`:
    - Create a CPU Sandbox (4vCPU, 8GB RAM).
    - Install Ollama in the sandbox via shell script.
    - Start `ollama serve` as a background session.
    - Run `ollama pull gemma4:4b` in the sandbox.
- [ ] Execute `serve_ollama.py` to launch the sandbox `(Local -> CPU Sandbox)`
- [ ] Extract and save `OLLAMA_ENDPOINT` and `OLLAMA_TOKEN` `(Local)`
- [ ] Verify inference via `curl` or `query_ollama.py` `(Local -> CPU Sandbox)`

## Phase 3: Deploy OpenCode Agent
- [ ] Implement `deploy_opencode.py` `(Local)`
- [ ] Create a second `(CPU Sandbox)` `(Local -> CPU Sandbox)`
- [ ] Install `opencode` globally in the sandbox.
- [ ] Start `opencode serve` as a background session in the `(CPU Sandbox)`
- [ ] Configure `OPENCODE_CONFIG_CONTENT` to use the Ollama endpoint `(CPU Sandbox)`:
    - Set provider to `openai` (Ollama is OpenAI-compatible).
    - Set `baseUrl` to `OLLAMA_ENDPOINT/v1`.
    - Inject `x-daytona-preview-token` into headers.
- [ ] Extract `OPENCODE_ENDPOINT` and `OPENCODE_TOKEN` `(Local)`

## Phase 4: Integration & Interaction (Local)
- [ ] Implement `agent_client.py` `(Local)`
- [ ] Connect to OpenCode server `(Local -> CPU Sandbox)`
- [ ] Create a new session `(Local -> CPU Sandbox)`
- [ ] Implement a readline loop for user prompts `(Local)`
- [ ] Test the connection: send a simple prompt and verify the agent can "think" (via Ollama) and "act" (via Daytona tools) `(Local -> CPU Sandbox -> CPU Sandbox)`

## Phase 5: Verification & Cleanup
- [ ] **End-to-End Test**: Perform a complex task (e.g., "Create a FastAPI app that calculates primes and provide a preview link") `(Local -> CPU Sandbox -> CPU Sandbox)`
- [ ] Verify that:
    - Inference is happening on the `(Ollama Sandbox)`
    - Code is executing in the `(OpenCode Sandbox)`
    - The preview link works
- [ ] Implement a cleanup script to delete all created sandboxes `(Local -> CPU Sandboxes)`
