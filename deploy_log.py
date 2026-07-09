import logging
import os
import time
from datetime import datetime
from typing import Callable, Optional, TypeVar

T = TypeVar("T")

LOG_DIR = "logs"
MAX_OUTPUT_CHARS = 8000
PROGRESS_INTERVAL = 30


def setup_logging(script_name: str) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(LOG_DIR, f"{script_name}-{timestamp}.log")

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)

    logger.info("Logging to %s", log_path)
    return logger


def truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated {len(text) - limit} chars]"


def log_exec(sb, logger: logging.Logger, label: str, command: str, *, required: bool = True):
    logger.info("[%s] exec: %s", label, truncate(command.replace("\n", " "), 200))
    response = sb.process.exec(command)
    exit_code = getattr(response, "exit_code", None)
    result = getattr(response, "result", "") or ""
    if exit_code not in (0, None):
        logger.error("[%s] exit_code=%s\n%s", label, exit_code, truncate(result))
        if required:
            raise RuntimeError(f"{label} failed with exit_code={exit_code}")
    else:
        if result.strip():
            logger.debug("[%s] output:\n%s", label, truncate(result))
        else:
            logger.debug("[%s] completed (no output)", label)
    return response


def log_poll(
    logger: logging.Logger,
    label: str,
    check_fn: Callable[[], Optional[T]],
    timeout: float,
    interval: float = 5.0,
    progress_interval: float = PROGRESS_INTERVAL,
) -> T:
    deadline = time.time() + timeout
    attempt = 0
    last_status = "no attempts yet"
    last_progress = time.time()

    while time.time() < deadline:
        attempt += 1
        try:
            result = check_fn()
            if result is not None:
                logger.info("[%s] ready after %d attempt(s)", label, attempt)
                return result
            last_status = "check returned not-ready"
        except Exception as exc:
            last_status = str(exc)
            logger.debug("[%s] attempt %d error: %s", label, attempt, exc)

        now = time.time()
        if now - last_progress >= progress_interval:
            logger.info(
                "[%s] still waiting (attempt %d, %.0fs elapsed): %s",
                label,
                attempt,
                now - (deadline - timeout),
                last_status,
            )
            last_progress = now

        time.sleep(interval)

    raise TimeoutError(f"{label} not ready after {timeout}s; last status: {last_status}")


def dump_sandbox_diagnostics(sb, logger: logging.Logger, service: str, port: Optional[int] = None):
    logger.error("=== sandbox diagnostics (%s) ===", service)
    commands = {
        "disk": "df -h",
        "processes": f"ps aux | grep -E '{service}|PID' | grep -v grep || true",
        "service_log": f"tail -n 200 /tmp/{service}.log 2>/dev/null || echo '(no log)'",
        "pull_log": "tail -n 100 /tmp/ollama_pull.log 2>/dev/null || echo '(no pull log)'",
        "pid_file": f"cat /tmp/{service}.pid 2>/dev/null || echo '(no pid file)'",
        "pid_alive": (
            f"PID=$(cat /tmp/{service}.pid 2>/dev/null); "
            "if [ -n \"$PID\" ] && [ -d /proc/$PID ]; then echo alive; else echo dead; fi"
        ),
    }
    if port is not None:
        commands["local_health"] = (
            f"curl -sS -w '\\nHTTP %{{http_code}}' http://localhost:{port}/api/tags 2>&1 || true"
        )

    for name, cmd in commands.items():
        try:
            resp = sb.process.exec(cmd)
            output = getattr(resp, "result", "") or ""
            logger.error("[%s]\n%s", name, truncate(output))
        except Exception as exc:
            logger.error("[%s] failed to fetch: %s", name, exc)

    logger.error("=== end diagnostics ===")


def discover_binary(sb, logger: logging.Logger, name: str) -> str:
    resp = log_exec(
        sb,
        logger,
        f"find_{name}",
        f"export PATH=$HOME/.ollama-install/bin:/usr/local/bin:/usr/bin; command -v {name}",
        required=False,
    )
    path = (getattr(resp, "result", "") or "").strip()
    if not path or getattr(resp, "exit_code", 1) != 0:
        raise RuntimeError(f"{name} binary not found after install")
    logger.info("Discovered %s at %s", name, path)
    return path


def classify_http_body(text: str) -> str:
    lower = text.lower()
    if "auth0" in lower or "<!doctype html" in lower:
        return "auth0_html_dead_sandbox"
    if "ollama is running" in lower:
        return "ollama_root"
    return "other"


def log_http_failure(logger: logging.Logger, label: str, status: int, body: str):
    kind = classify_http_body(body)
    logger.error(
        "[%s] HTTP %s (%s): %s",
        label,
        status,
        kind,
        truncate(body, 200),
    )
