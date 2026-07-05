# Ollama Setup Post-Mortem: Daytona CPU Sandbox

## 🚫 Quick Guide for the Next Agent
**DO:**
- Use **absolute paths** for all binaries (e.g., `/usr/local/bin/ollama`) to avoid `PATH` issues.
- Verify the server is healthy via `curl localhost:11434/api/tags` **inside** the sandbox before attempting to `pull` a model.
- Check `ps aux` immediately after starting the server to ensure the process didn't crash.
- Use a long-lived "wrapper" shell script that keeps the process open if `run_async` fails.

**DON'T:**
- Rely on `nohup` within a transient `sb.process.exec()` call; the environment may be cleaned up upon command completion.
- Assume the `daytona` SDK's `run_async=True` persists the process across separate API calls without verification.
- Attempt GPU-based vLLM unless the account limit is explicitly increased.

---

## 📉 Exhaustive List of Failed Attempts

| Attempt | Method | Failure Mode | Root Cause |
| :--- | :--- | :--- | :--- |
| **vLLM GPU** | `daytona.create` (GPU) | `DaytonaValidationError` | Account GPU limit is 0. |
| **Sess. Async** | `execute_session_command` | Health check 502 / Process missing | Process did not persist after the SDK returned. |
| **Nohup Exec** | `sb.process.exec("nohup...")` | Timeout / Process missing | Background processes in `exec` calls are often killed when the shell exits. |
| **Sess. Nohup** | `execute_session_command` + `nohup` | `No such file or directory` | `ollama` binary not in the session's `PATH` (likely `/usr/local/bin` missing). |
| **Fixed Script** | Combined Install + Serve + Pull | User Abort / Timeout | Process took longer than the shell timeout to pull the model. |

---

## 🛠️ Remaining Strategies (Worth Trying)

1. **Custom Docker Image**: 
   - Build an image containing `ollama` and `gemma4:4b` pre-installed.
   - Result: Zero installation/pull time, reduced timeout risk.
2. **Foreground Wrapper**:
   - Run a script that starts the server in the background and then enters a `while true; sleep 1` loop in the foreground.
   - Result: Forces the Daytona sandbox to keep the session alive.
3. **Systemd/Supervisor**:
   - Try to register `ollama` as a system service within the sandbox to ensure auto-restart.
4. **Direct Path Execution**:
   - Call `/usr/local/bin/ollama serve` explicitly instead of relying on the shell's `PATH`.
