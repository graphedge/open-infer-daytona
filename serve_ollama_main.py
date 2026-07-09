import os
import sys
import threading
import time

import requests
from dotenv import load_dotenv
from daytona import (
    CreateSandboxBaseParams,
    Daytona,
    DaytonaConfig,
    Resources,
    SessionExecuteRequest,
)

from deploy_log import (
    discover_binary,
    dump_sandbox_diagnostics,
    log_exec,
    log_http_failure,
    log_poll,
    setup_logging,
)

load_dotenv()

MODEL = os.environ.get(
    "OLLAMA_MODEL",
    "huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF",
)
PORT = int(os.environ.get("OLLAMA_PORT", "11434"))
SESSION = "ollama_manager"
BOOT_TIMEOUT = 900
INSTALL_CMD = r"""bash -c '
set -euo pipefail
OLLAMA_HOME="${HOME}/.ollama-install"
export PATH="${OLLAMA_HOME}/bin:/usr/local/bin:${PATH}"
rm -rf "${OLLAMA_HOME}" /tmp/ollama.tar.zst
mkdir -p "${OLLAMA_HOME}"
df -h /
install_via_script() {
  curl -fsSL --retry 5 --retry-delay 3 --connect-timeout 30 https://ollama.com/install.sh | sh
}
install_via_github() {
  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64) ASSET=ollama-linux-amd64.tar.zst ;;
    aarch64|arm64) ASSET=ollama-linux-arm64.tar.zst ;;
    *) echo "unsupported arch: $ARCH"; return 1 ;;
  esac
  VER=$(curl -fsSL https://api.github.com/repos/ollama/ollama/releases/latest | grep -o "\"tag_name\": \"[^\"]*\"" | cut -d\" -f4)
  URL="https://github.com/ollama/ollama/releases/download/${VER}/${ASSET}"
  EXCLUDES="--exclude=lib/ollama/cuda_v12 --exclude=lib/ollama/cuda_v13 --exclude=lib/ollama/vulkan"
  if tar --help 2>&1 | grep -q -- "--zstd"; then
    curl -fsSL --retry 5 --retry-delay 3 --connect-timeout 120 "$URL" | tar --zstd -xf - -C "$OLLAMA_HOME" $EXCLUDES
  elif command -v zstd >/dev/null 2>&1; then
    curl -fsSL --retry 5 --retry-delay 3 --connect-timeout 120 "$URL" | zstd -d | tar -xf - -C "$OLLAMA_HOME" $EXCLUDES
  else
    echo "zstd decompressor not available"; return 1
  fi
  "${OLLAMA_HOME}/bin/ollama" --version
}
if install_via_script; then exit 0; fi
echo "install.sh failed, trying GitHub binary (CPU-only, streamed)..."
install_via_github
df -h /
'
"""
PULL_PROGRESS_INTERVAL = 60


def is_ollama_healthy(resp: requests.Response) -> bool:
    if resp.status_code != 200:
        return False
    text = resp.text
    if "auth0" in text.lower() or "<!doctype html" in text.lower():
        return False
    if "Ollama is running" in text:
        return True
    try:
        return "models" in resp.json()
    except ValueError:
        return False


def tail_pull_log(sb, logger):
    try:
        resp = sb.process.exec("tail -n 5 /tmp/ollama_pull.log 2>/dev/null || true")
        output = (getattr(resp, "result", "") or "").strip()
        if output:
            logger.info("[pull] progress:\n%s", output)
    except Exception as exc:
        logger.debug("[pull] could not tail pull log: %s", exc)


def serve_ollama():
    logger = setup_logging("serve_ollama")
    sb = None

    try:
        daytona = Daytona(DaytonaConfig())

        logger.info("Creating CPU Sandbox (4vCPU, 8GB RAM, 30GB disk)...")
        sb = daytona.create(
            CreateSandboxBaseParams(
                resources=Resources(cpu=4, memory=8, disk=30),
                auto_stop_interval=0,
                ephemeral=True,
            ),
            timeout=600,
        )
        logger.info("Sandbox created: %s", sb.id)

        for attempt in range(1, 4):
            try:
                log_exec(sb, logger, f"install_attempt_{attempt}", INSTALL_CMD)
                break
            except RuntimeError:
                if attempt == 3:
                    raise
                logger.warning("Install attempt %d failed, retrying in 10s...", attempt)
                time.sleep(10)

        ollama_bin = discover_binary(sb, logger, "ollama")

        wrapper_script = f"""#!/bin/bash
set -euo pipefail
export PATH=$PATH:/usr/local/bin
{ollama_bin} serve > /tmp/ollama.log 2>&1 &
echo $! > /tmp/ollama.pid
while true; do sleep 60; done
"""
        log_exec(
            sb,
            logger,
            "write_wrapper",
            f"cat > /tmp/ollama_wrapper.sh << 'WRAPPER_EOF'\n{wrapper_script}\nWRAPPER_EOF\nchmod +x /tmp/ollama_wrapper.sh",
        )

        try:
            sb.process.create_session(SESSION)
            logger.debug("Session %s created", SESSION)
        except Exception as exc:
            logger.debug("Session create note: %s", exc)

        logger.info("Starting Ollama in long-lived session...")
        sb.process.execute_session_command(
            SESSION,
            SessionExecuteRequest(
                command="bash /tmp/ollama_wrapper.sh",
                run_async=True,
            ),
        )

        def local_health_ready():
            resp = sb.process.exec(
                f"curl -sS -o /dev/null -w '%{{http_code}}' http://localhost:{PORT}/api/tags 2>/dev/null || echo fail"
            )
            code = (getattr(resp, "result", "") or "").strip()
            if code == "200":
                return True
            return None

        log_poll(logger, "local_health", local_health_ready, timeout=120, interval=2)

        logger.info("Pulling model %s (may take several minutes)...", MODEL)
        pull_cmd = (
            f"bash -c 'set -o pipefail; export PATH=$HOME/.ollama-install/bin:/usr/local/bin:$PATH; "
            f"{ollama_bin} pull {MODEL} 2>&1 | tee -a /tmp/ollama_pull.log'"
        )
        pull_done = threading.Event()

        def tail_loop():
            while not pull_done.wait(PULL_PROGRESS_INTERVAL):
                tail_pull_log(sb, logger)

        tail_thread = threading.Thread(target=tail_loop, daemon=True)
        tail_thread.start()
        try:
            log_exec(sb, logger, "pull", pull_cmd)
        finally:
            pull_done.set()
            tail_pull_log(sb, logger)

        pull_check = sb.process.exec("grep -i '^Error:' /tmp/ollama_pull.log && exit 1 || exit 0")
        if getattr(pull_check, "exit_code", 0) != 0:
            raise RuntimeError(f"Model pull failed for {MODEL}; see /tmp/ollama_pull.log")

        pv = sb.get_preview_link(PORT)
        hdr = {"x-daytona-preview-token": pv.token}
        logger.info("Polling preview URL %s", pv.url)

        def preview_ready():
            try:
                resp = requests.get(f"{pv.url}/api/tags", headers=hdr, timeout=10)
                if is_ollama_healthy(resp):
                    return True
                log_http_failure(logger, "preview_health", resp.status_code, resp.text)
            except requests.RequestException as exc:
                logger.debug("preview poll error: %s", exc)
            return None

        log_poll(logger, "preview_health", preview_ready, timeout=BOOT_TIMEOUT, interval=5)

        logger.info("--- OLLAMA SERVER READY ---")
        logger.info("OLLAMA_ENDPOINT=%s", pv.url)
        logger.info("OLLAMA_TOKEN=%s", pv.token)
        logger.info("SANDBOX_ID=%s", sb.id)

        with open("ollama_info.txt", "w") as f:
            f.write(f"OLLAMA_ENDPOINT={pv.url}\n")
            f.write(f"OLLAMA_TOKEN={pv.token}\n")
            f.write(f"SANDBOX_ID={sb.id}\n")

        logger.info("Information saved to ollama_info.txt.")

    except Exception as exc:
        logger.error("Deploy failed: %s", exc)
        if sb is not None:
            dump_sandbox_diagnostics(sb, logger, "ollama", port=PORT)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    try:
        serve_ollama()
    except KeyboardInterrupt:
        print("Interrupted by user.")
        sys.exit(0)
