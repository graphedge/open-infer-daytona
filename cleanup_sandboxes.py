import argparse
import os
import sys

from dotenv import load_dotenv
from daytona import Daytona, DaytonaConfig

from deploy_log import setup_logging

load_dotenv()


def read_sandbox_ids_from_info_files():
    ids = set()
    for path in ("ollama_info.txt", "opencode_info.txt"):
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                if line.startswith("SANDBOX_ID="):
                    ids.add(line.strip().split("=", 1)[1])
    return ids


def cleanup(keep_ids=None, dry_run=False, keep_from_info=True):
    logger = setup_logging("cleanup_sandboxes")
    keep_ids = set(keep_ids or [])
    if keep_from_info:
        keep_ids |= read_sandbox_ids_from_info_files()

    daytona = Daytona(DaytonaConfig())
    sandboxes = list(daytona.list())
    logger.info("Found %d sandboxes; keeping %s", len(sandboxes), keep_ids or "none")

    deleted = 0
    for sb in sandboxes:
        if sb.id in keep_ids:
            logger.info("Keeping %s (%s)", sb.id, sb.state)
            continue
        if dry_run:
            logger.info("Would delete %s (%s)", sb.id, sb.state)
            continue
        try:
            logger.info("Deleting %s (%s)...", sb.id, sb.state)
            sb.delete()
            deleted += 1
        except Exception as exc:
            logger.error("Failed to delete %s: %s", sb.id, exc)

    logger.info("Done. Deleted %d sandbox(es).", deleted)


def main():
    parser = argparse.ArgumentParser(description="Delete Daytona sandboxes")
    parser.add_argument("--keep", action="append", default=[], help="Sandbox ID to keep")
    parser.add_argument("--dry-run", action="store_true", help="List only, do not delete")
    parser.add_argument("--all", action="store_true", help="Delete all including info-file sandboxes")
    args = parser.parse_args()

    keep = [] if args.all else args.keep
    cleanup(keep_ids=keep, dry_run=args.dry_run, keep_from_info=not args.all)


if __name__ == "__main__":
    main()
    sys.exit(0)
