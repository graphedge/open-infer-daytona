# Project: OpenCode Agent on Daytona (CPU Optimized)

## Goal
Deploy an autonomous coding agent using OpenCode, powered by a self-hosted Ollama model on Daytona CPU sandboxes.

## Architecture
- **Inference**: Ollama running on a Daytona CPU Sandbox (default model: `huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF`).
- **Agent**: OpenCode server running on a Daytona CPU Sandbox.
- **Client**: Local Python/TS script interacting with the OpenCode server.
- **Execution**: OpenCode uses Daytona's process execution to run generated code in isolated environments.

---

## Phase 1: Setup & Configuration (Local)
- [x] Install required Python packages in `.venv` (`daytona`, `openai`, `requests`, `python-dotenv`).
- [x] Create `.env` file with `DAYTONA_API_KEY` and `HF_TOKEN`.

## Phase 2: Deploy Model Inference (Ollama)
- [x] Implement `serve_ollama_main.py` `(Local)`:
    - Create a CPU Sandbox (4vCPU, 8GB RAM).
    - Install Ollama with resilient fallback (install script -> GitHub streamed tarball).
    - Start `ollama serve` in a long-lived Daytona session wrapper.
    - Pull the default HF model.
- [x] Execute `serve_ollama_main.py` to launch the sandbox `(Local -> CPU Sandbox)`
- [x] Extract and save `OLLAMA_ENDPOINT` and `OLLAMA_TOKEN` `(Local)`
- [x] Verify inference via `query_ollama.py` `(Local -> CPU Sandbox)`

## Phase 3: Deploy OpenCode Agent
- [x] Implement `deploy_opencode.py` `(Local)`
- [x] Create a second `(CPU Sandbox)` `(Local -> CPU Sandbox)`
- [x] Install OpenCode CLI in the sandbox.
- [ ] Start OpenCode as a background session in the `(CPU Sandbox)` (process starts; API route behavior still blocked)
- [ ] Configure OpenCode to use the Ollama endpoint `(CPU Sandbox)` (config wiring is implemented; deploy remains blocked on API route mismatch):
    - Set provider to `openai` (Ollama is OpenAI-compatible).
    - Set `baseUrl` to `OLLAMA_ENDPOINT/v1`.
    - Inject `x-daytona-preview-token` into headers.
- [ ] Extract `OPENCODE_ENDPOINT` and `OPENCODE_TOKEN` `(Local)`

## Phase 4: Integration & Interaction (Local)
- [x] Implement `agent_client.py` `(Local)`
- [ ] Connect to OpenCode server `(Local -> CPU Sandbox)`
- [ ] Create a new session `(Local -> CPU Sandbox)` (blocked by successful OpenCode deploy)
- [x] Implement a readline loop for user prompts `(Local)`
- [ ] Test the connection: send a simple prompt and verify the agent can "think" (via Ollama) and "act" (via Daytona tools) `(Local -> CPU Sandbox -> CPU Sandbox)`

## Phase 5: Verification & Cleanup
- [ ] **End-to-End Test**: Perform a complex task (e.g., "Create a FastAPI app that calculates primes and provide a preview link") `(Local -> CPU Sandbox -> CPU Sandbox)`
- [ ] Verify that:
    - Inference is happening on the `(Ollama Sandbox)`
    - Code is executing in the `(OpenCode Sandbox)`
    - The preview link works
- [x] Implement a cleanup script to delete all created sandboxes `(Local -> CPU Sandboxes)` (`cleanup_sandboxes.py`)
