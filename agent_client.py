import os
import sys

import requests

from deploy_log import log_http_failure, setup_logging
from query_ollama import read_info

DEFAULT_MODEL = os.environ.get(
    "OLLAMA_MODEL",
    "huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF",
)


def opencode_headers(token):
    return {"x-daytona-preview-token": token} if token else {}


def check_health(endpoint, token, logger):
    hdr = opencode_headers(token)
    logger.info("Checking OpenCode at %s", endpoint)
    try:
        resp = requests.get(f"{endpoint.rstrip('/')}/v1/models", headers=hdr, timeout=10)
    except requests.RequestException as exc:
        logger.error("Connection error: %s", exc)
        return False

    logger.info("Status: %s", resp.status_code)
    body = resp.text.lower()
    if resp.status_code == 200 and "auth0" not in body and "<!doctype html" not in body:
        logger.info("OpenCode is reachable.")
        return True

    log_http_failure(logger, "health", resp.status_code, resp.text)
    return False


def send_prompt(endpoint, token, prompt, logger, model=None):
    hdr = {
        **opencode_headers(token),
        "Content-Type": "application/json",
    }
    model = model or DEFAULT_MODEL

    for path, payload in [
        (
            "/api/chat",
            {
                "model": f"ollama/{model}",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        ),
        (
            "/v1/chat/completions",
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        ),
    ]:
        url = f"{endpoint.rstrip('/')}{path}"
        try:
            resp = requests.post(url, json=payload, headers=hdr, timeout=120)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    log_http_failure(logger, path, resp.status_code, resp.text)
                    continue
                if "choices" in data:
                    return data["choices"][0]["message"]["content"]
                if "message" in data:
                    return data["message"].get("content", str(data))
                return str(data)
            log_http_failure(logger, path, resp.status_code, resp.text)
        except requests.RequestException as exc:
            logger.error("%s failed: %s", path, exc)

    return None


def main():
    logger = setup_logging("agent_client")

    if not os.path.exists("opencode_info.txt"):
        logger.error("opencode_info.txt not found. Run deploy_opencode.py first.")
        return 1

    info = read_info("opencode_info.txt")
    endpoint = info.get("OPENCODE_ENDPOINT")
    token = info.get("OPENCODE_TOKEN")
    if not endpoint:
        logger.error("OPENCODE_ENDPOINT missing in opencode_info.txt")
        return 1

    if not check_health(endpoint, token, logger):
        return 1

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        reply = send_prompt(endpoint, token, prompt, logger)
        if reply:
            print(f"\nAgent: {reply}")
            return 0
        return 1

    print("Enter prompts (empty line or Ctrl+C to quit).")
    try:
        while True:
            try:
                prompt = input("\nYou: ").strip()
            except EOFError:
                break
            if not prompt:
                break
            reply = send_prompt(endpoint, token, prompt, logger)
            if reply:
                print(f"Agent: {reply}")
            else:
                print("Agent: (no response)")
    except KeyboardInterrupt:
        print("\nBye.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
