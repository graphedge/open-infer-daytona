import os
import sys

from dotenv import load_dotenv
from daytona import Daytona, DaytonaConfig

from deploy_log import setup_logging

load_dotenv()


def recover_ollama_info():
    logger = setup_logging("recover_ollama")
    daytona = Daytona(DaytonaConfig())
    sandboxes = list(daytona.list())

    logger.info("Found %d sandboxes. Searching for Ollama...", len(sandboxes))

    for sb in sandboxes:
        try:
            logger.info("Checking sandbox %s...", sb.id)
            res = sb.process.exec("/usr/local/bin/ollama --version 2>/dev/null || ollama --version")
            out = (getattr(res, "result", "") or "").lower()
            if getattr(res, "exit_code", 1) != 0 or "version" not in out:
                logger.debug("Sandbox %s: ollama not running (%s)", sb.id, out.strip()[:80])
                continue

            logger.info("Found Ollama in sandbox %s", sb.id)
            pv = sb.get_preview_link(11434)

            with open("ollama_info.txt", "w") as f:
                f.write(f"OLLAMA_ENDPOINT={pv.url}\n")
                f.write(f"OLLAMA_TOKEN={pv.token}\n")
                f.write(f"SANDBOX_ID={sb.id}\n")

            logger.info("--- OLLAMA INFO RECOVERED ---")
            logger.info("Endpoint: %s", pv.url)
            logger.info("Token: %s", pv.token)
            logger.info("Sandbox ID: %s", sb.id)
            logger.info("Saved to ollama_info.txt")
            return
        except Exception as exc:
            logger.warning("Could not check sandbox %s: %s", sb.id, exc)

    logger.error("Could not find a sandbox running Ollama.")


if __name__ == "__main__":
    recover_ollama_info()
    if not os.path.exists("ollama_info.txt"):
        sys.exit(1)
