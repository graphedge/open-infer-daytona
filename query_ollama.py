import os
import sys

import requests

from deploy_log import log_http_failure, setup_logging

DEFAULT_MODEL = os.environ.get(
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


def test_ollama():
    logger = setup_logging("query_ollama")

    if not os.path.exists("ollama_info.txt"):
        logger.error("ollama_info.txt not found. Run serve_ollama_main.py first.")
        return False

    info = read_info("ollama_info.txt")
    endpoint = info.get("OLLAMA_ENDPOINT")
    token = info.get("OLLAMA_TOKEN")
    if not endpoint:
        logger.error("OLLAMA_ENDPOINT missing in ollama_info.txt")
        return False

    hdr = {"x-daytona-preview-token": token} if token else {}
    logger.info("Testing Ollama at %s", endpoint)

    try:
        resp = requests.get(f"{endpoint.rstrip('/')}/api/tags", headers=hdr, timeout=10)
    except requests.RequestException as exc:
        logger.error("Connection error: %s", exc)
        return False

    if not is_ollama_healthy(resp):
        log_http_failure(logger, "health", resp.status_code, resp.text)
        logger.error("Sandbox may be stopped or token expired.")
        return False

    logger.info("Ollama is responding.")

    chat_url = f"{endpoint.rstrip('/')}/api/chat"
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [{"role": "user", "content": "Say hello in five words or fewer."}],
        "stream": False,
    }
    try:
        resp = requests.post(chat_url, json=payload, headers=hdr, timeout=120)
    except requests.RequestException as exc:
        logger.error("Chat connection error: %s", exc)
        return False

    if resp.status_code == 200:
        logger.info("Model response: %s", resp.json()["message"]["content"])
        return True

    if resp.status_code == 404:
        logger.error("Model not found (404). Is %s pulled?", DEFAULT_MODEL)
    log_http_failure(logger, "chat", resp.status_code, resp.text)
    return False


if __name__ == "__main__":
    ok = test_ollama()
    sys.exit(0 if ok else 1)
