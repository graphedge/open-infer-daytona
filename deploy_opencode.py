import json
import os
import sys
import shlex

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
    dump_sandbox_diagnostics,
    log_exec,
    log_http_failure,
    log_poll,
    setup_logging,
)

load_dotenv()

PORT = int(os.environ.get("OPENCODE_PORT", "3000"))
SESSION = "opencode_session"
BOOT_TIMEOUT = 600
MODEL = os.environ.get(
    "OLLAMA_MODEL",
    "huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF",
)


def read_info(path):
    info = {}
    with open(path, "r") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                info[k] = v
    return info


def build_opencode_config(ollama_endpoint, ollama_token):
    return {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Ollama (Daytona)",
                "options": {
                    "baseURL": f"{ollama_endpoint.rstrip('/')}/v1",
                    "apiKey": "ollama",
                    "headers": {
                        "x-daytona-preview-token": ollama_token,
                    },
                },
                "models": {
                    MODEL: {"name": MODEL},
                },
            }
        },
        "model": f"ollama/{MODEL}",
    }


def redact_config(config):
    redacted = json.loads(json.dumps(config))
    headers = redacted.get("provider", {}).get("ollama", {}).get("options", {}).get("headers", {})
    if "x-daytona-preview-token" in headers:
        headers["x-daytona-preview-token"] = "***"
    return redacted


def supports_port_flag(sb, logger, opencode_bin, launch_mode):
    probe_cmd = f"""bash -c '
set -euo pipefail
BIN={shlex.quote(opencode_bin)}
if "$BIN" {launch_mode} --help 2>&1 | grep -q -- "--port"; then
  echo yes
else
  echo no
fi
'"""
    resp = log_exec(sb, logger, "detect_port_flag", probe_cmd, required=False)
    value = (getattr(resp, "result", "") or "").strip().splitlines()
    return bool(value and value[-1].strip() == "yes")


def discover_opencode_binary(sb, logger):
    probe_cmd = """bash -c '
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/.opencode/bin:$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:$PATH"
if command -v opencode >/dev/null 2>&1; then
  command -v opencode
  exit 0
fi
for p in "$HOME/.local/bin/opencode" "$HOME/.opencode/bin/opencode" "/usr/local/bin/opencode"; do
  if [ -x "$p" ]; then
    echo "$p"
    exit 0
  fi
done
echo "missing"
exit 1
'"""
    resp = log_exec(sb, logger, "find_opencode", probe_cmd, required=False)
    path = (getattr(resp, "result", "") or "").strip().splitlines()
    candidate = path[-1].strip() if path else ""
    if getattr(resp, "exit_code", 1) != 0 or not candidate or candidate == "missing":
        raise RuntimeError("opencode binary not found after install")
    logger.info("Discovered opencode at %s", candidate)
    return candidate


def deploy_opencode():
    logger = setup_logging("deploy_opencode")
    sb = None

    try:
        if os.path.exists("opencode_info.txt"):
            os.remove("opencode_info.txt")

        if not os.path.exists("ollama_info.txt"):
            logger.error("ollama_info.txt not found. Run serve_ollama_main.py first.")
            raise SystemExit(1)

        ollama = read_info("ollama_info.txt")
        ollama_endpoint = ollama.get("OLLAMA_ENDPOINT")
        ollama_token = ollama.get("OLLAMA_TOKEN")
        if not ollama_endpoint or not ollama_token:
            logger.error("OLLAMA_ENDPOINT or OLLAMA_TOKEN missing in ollama_info.txt")
            raise SystemExit(1)

        config = build_opencode_config(ollama_endpoint, ollama_token)
        config_json = json.dumps(config)
        logger.info("OpenCode config: %s", json.dumps(redact_config(config)))

        daytona = Daytona(DaytonaConfig())
        logger.info("Creating CPU Sandbox for OpenCode (2vCPU, 4GB RAM)...")
        sb = daytona.create(
            CreateSandboxBaseParams(
                resources=Resources(cpu=2, memory=4),
                auto_stop_interval=0,
                ephemeral=True,
            ),
            timeout=600,
        )
        logger.info("Sandbox created: %s", sb.id)

        setup_cmd = """
set -euo pipefail
export PATH=$HOME/.local/bin:$HOME/.opencode/bin:$HOME/.npm-global/bin:/usr/local/bin:$PATH
if ! command -v opencode >/dev/null 2>&1; then
  if curl -fsSL --retry 3 https://opencode.ai/install | bash; then
    true
  else
    npm install -g opencode-ai
  fi
fi
opencode --version
"""
        logger.info("Installing Node/opencode inside sandbox...")
        log_exec(sb, logger, "install_opencode", setup_cmd)
        opencode_bin = discover_opencode_binary(sb, logger)
        launch_mode = "serve"
        has_port_flag = supports_port_flag(sb, logger, opencode_bin, launch_mode)
        launch_args = f"{launch_mode} --port {PORT}" if has_port_flag else launch_mode
        logger.info("Launch args: %s", launch_args)

        log_exec(
            sb,
            logger,
            "write_config",
            f"cat > /tmp/opencode.json << 'CONFIG_EOF'\n{config_json}\nCONFIG_EOF",
        )

        wrapper_script = """#!/bin/bash
set -euo pipefail
export OPENCODE_PORT="{port}"
export PORT="{port}"
export OPENCODE_CONFIG=/tmp/opencode.json
export PATH="$HOME/.local/bin:$HOME/.opencode/bin:$HOME/.npm-global/bin:/usr/local/bin:$PATH"
"{opencode_bin}" {launch_args} > /tmp/opencode.log 2>&1 &
echo $! > /tmp/opencode.pid
while true; do sleep 60; done
""".format(port=PORT, opencode_bin=opencode_bin, launch_args=launch_args)
        log_exec(
            sb,
            logger,
            "write_wrapper",
            f"cat > /tmp/opencode_wrapper.sh << 'WRAPPER_EOF'\n{wrapper_script}\nWRAPPER_EOF\nchmod +x /tmp/opencode_wrapper.sh",
        )

        try:
            sb.process.create_session(SESSION)
            logger.debug("Session %s created", SESSION)
        except Exception as exc:
            logger.debug("Session create note: %s", exc)

        logger.info("Starting OpenCode in long-lived session...")
        sb.process.execute_session_command(
            SESSION,
            SessionExecuteRequest(
                command="bash /tmp/opencode_wrapper.sh",
                run_async=True,
            ),
        )

        def local_health_ready():
            cmd = (
                f"bash -c 'PID=$(cat /tmp/opencode.pid 2>/dev/null || true); "
                "if [ -z \"$PID\" ] || [ ! -d /proc/$PID ]; then echo dead; exit 0; fi; "
                "listen=$(grep -oE \"127.0.0.1:[0-9]+\" /tmp/opencode.log 2>/dev/null | tail -n1 | cut -d: -f2); "
                f"if [ -z \"$listen\" ]; then listen=\"{PORT}\"; fi; "
                "body=$(curl -sS \"http://localhost:${listen}/global/health\" 2>/dev/null || true); "
                "if echo \"$body\" | grep -qi '\\"healthy\\"[[:space:]]*:[[:space:]]*true'; then "
                "echo ready:${listen}; "
                "else "
                "echo not_ready:${listen}; "
                "fi'"
            )
            resp = sb.process.exec(cmd)
            state = (getattr(resp, "result", "") or "").strip()
            if state.startswith("ready:"):
                return state.split(":", 1)[1]
            if state == "dead":
                raise RuntimeError("OpenCode process exited before becoming healthy")
            return None

        effective_port = int(log_poll(logger, "local_health", local_health_ready, timeout=180, interval=3))
        logger.info("OpenCode appears healthy on localhost:%s", effective_port)

        pv = sb.get_preview_link(effective_port)
        hdr = {"x-daytona-preview-token": pv.token}
        logger.info("Waiting for OpenCode at %s", pv.url)

        def preview_ready():
            try:
                resp = requests.get(f"{pv.url.rstrip('/')}/global/health", headers=hdr, timeout=5)
                if resp.status_code == 200:
                    try:
                        js = resp.json()
                        if js.get("healthy") is True:
                            return True
                    except ValueError:
                        body = resp.text.lower()
                        if '"healthy":true' in body:
                            return True
                log_http_failure(logger, "preview_health", resp.status_code, resp.text)
            except requests.RequestException as exc:
                logger.debug("preview poll error: %s", exc)
            return None

        log_poll(logger, "preview_health", preview_ready, timeout=BOOT_TIMEOUT, interval=5)

        logger.info("--- OPENCODE READY ---")
        logger.info("OPENCODE_ENDPOINT=%s", pv.url)
        logger.info("OPENCODE_TOKEN=%s", pv.token)
        logger.info("SANDBOX_ID=%s", sb.id)
        logger.info("OPENCODE_PORT=%s", effective_port)

        with open("opencode_info.txt", "w") as f:
            f.write(f"OPENCODE_ENDPOINT={pv.url}\n")
            f.write(f"OPENCODE_TOKEN={pv.token}\n")
            f.write(f"SANDBOX_ID={sb.id}\n")
            f.write(f"OPENCODE_PORT={effective_port}\n")

        logger.info("Information saved to opencode_info.txt.")

    except SystemExit:
        raise
    except Exception as exc:
        logger.error("Deploy failed: %s", exc)
        if sb is not None:
            dump_sandbox_diagnostics(sb, logger, "opencode", port=PORT)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    try:
        deploy_opencode()
    except KeyboardInterrupt:
        print("Interrupted by user.")
        sys.exit(0)
