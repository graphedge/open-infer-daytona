#!/usr/bin/env python3
"""
Validate OpenCode endpoints locally using OPENCODE_ENDPOINT and OPENCODE_TOKEN.
Usage:
  ./scripts/validate_opencode.py [--info opencode_info.txt] [--endpoint URL] [--token TOKEN]

The script performs:
  - GET /global/health
  - POST /session {}
  - POST /session/{id}/message with a small text part (non-streaming)
  - GET /session/{id}/message to list messages

No external Python packages required.
"""

import argparse
import json
import os
import sys
import time
from urllib import request, error


DEFAULT_MODEL = os.environ.get(
    "OLLAMA_MODEL", "huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF"
)


def load_info(path):
    info = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    info[k] = v
    return info


def http_request(method, url, token=None, data=None, timeout=30):
    headers = {"User-Agent": "open-infer-validate/1"}
    if token:
        headers["x-daytona-preview-token"] = token
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        body = None
    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            return status, body
    except error.HTTPError as e:
        try:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception:
            return e.code, str(e)
    except Exception as e:
        return None, str(e)


def pretty_print_json(prefix, text):
    try:
        j = json.loads(text)
        print(prefix + json.dumps(j, indent=2)[:4000])
    except Exception:
        print(prefix + text[:4000])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--info", default="opencode_info.txt", help="Path to opencode_info.txt")
    parser.add_argument("--endpoint", help="OPENCODE_ENDPOINT override")
    parser.add_argument("--token", help="OPENCODE_TOKEN override")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--message", default="Say hello in five words or fewer.")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    info = load_info(args.info) if os.path.exists(args.info) else {}
    endpoint = args.endpoint or info.get("OPENCODE_ENDPOINT")
    token = args.token or info.get("OPENCODE_TOKEN")
    sandbox_id = info.get("SANDBOX_ID")

    if not endpoint:
        print("OPENCODE_ENDPOINT not provided and not found in {}".format(args.info))
        print("Create opencode_info.txt via deploy_opencode.py or pass --endpoint and --token")
        sys.exit(2)

    endpoint = endpoint.rstrip("/")
    print("Using endpoint:", endpoint)
    if token:
        print("Using preview token: ****(hidden)****")

    # 1) GET /global/health
    print("\nGET /global/health")
    st, body = http_request("GET", f"{endpoint}/global/health", token=token, timeout=10)
    if st is None:
        print("Health check failed:", body)
        sys.exit(1)
    print("HTTP", st)
    pretty_print_json("BODY: ", body)

    # 2) POST /session
    print("\nPOST /session (create session)")
    st, body = http_request("POST", f"{endpoint}/session", token=token, data={}, timeout=10)
    if st is None:
        print("Session creation failed:", body)
        sys.exit(1)
    print("HTTP", st)
    pretty_print_json("RESPONSE: ", body)
    try:
        sid = json.loads(body).get("id")
    except Exception:
        sid = None
    if not sid:
        print("Could not parse session id from response. Stopping.")
        sys.exit(1)
    print("Session id:", sid)

    # 3) POST /session/{id}/message with non-streaming payload
    payload = {
        "model": {"providerID": "ollama", "modelID": args.model},
        "parts": [{"type": "text", "text": args.message}],
        "stream": False,
    }
    print("\nPOST /session/{sid}/message (non-streaming attempt)".replace("{sid}", sid))

    # Provide a brief delay to allow logs to be observed if the user wants to tail them
    print("You can tail opencode logs now (e.g., tail -f /tmp/opencode.log in sandbox) if you want to capture provider flow.")

    st, body = http_request("POST", f"{endpoint}/session/{sid}/message", token=token, data=payload, timeout=args.timeout)
    if st is None:
        print("Message POST error:", body)
        sys.exit(1)
    print("HTTP", st)
    pretty_print_json("RESPONSE: ", body)

    # 4) GET /session/{id}/message to list messages
    print("\nGET /session/{sid}/message (list messages)".replace("{sid}", sid))
    st, body = http_request("GET", f"{endpoint}/session/{sid}/message", token=token, timeout=10)
    if st is None:
        print("List messages error:", body)
        sys.exit(1)
    print("HTTP", st)
    pretty_print_json("RESPONSE: ", body)

    print("\nValidation script complete. Check opencode logs if results are missing or the POST hung.")
    if sandbox_id:
        print(f"Sandbox id: {sandbox_id} — you can tail logs via the Daytona SDK/CLI or by re-entering the sandbox and tailing /tmp/opencode.log")

    return 0


if __name__ == "__main__":
    sys.exit(main())
