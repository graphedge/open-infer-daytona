# Redeploy OpenCode — procedure

Purpose
- Re-run deploy_opencode.py to produce a fresh OPENCODE_ENDPOINT and OPENCODE_TOKEN so validation can proceed.

Quick steps (run in repo root)

1) Prepare a virtualenv and install deps

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install requests python-dotenv daytona
```

2) Verify Ollama is healthy (ollama_info.txt must exist)

```bash
cat ollama_info.txt
.venv/bin/python query_ollama.py
```

3) Run deploy_opencode.py and capture logs

```bash
mkdir -p logs
.venv/bin/python deploy_opencode.py 2>&1 | tee logs/deploy_opencode-$(date +%Y%m%d-%H%M%S).log
```

4) Monitor progress
- In another terminal: tail -f logs/deploy_opencode-*.log
- To inspect runtime logs inside the sandbox (Daytona SDK or via remote shell): tail -f /tmp/opencode.log

5) On success
- `opencode_info.txt` will be written to the repo root with:
  OPENCODE_ENDPOINT=...
  OPENCODE_TOKEN=...
  SANDBOX_ID=...
  OPENCODE_PORT=...

6) Validate (non-streaming)

```bash
python3 scripts/validate_opencode.py   # reads opencode_info.txt by default
# Or explicitly:
python3 scripts/validate_opencode.py --endpoint "https://..." --token "<TOKEN>" --timeout 120
```

Troubleshooting
- If `/global/health` returns HTML/Auth0 page: the preview token may be invalid/expired or the preview proxy returned an auth error. Re-run deploy to obtain a fresh preview token.
- If deploy stalls or process exits: inspect logs (`tail -n 200 logs/deploy_opencode-*.log`) and sandbox diagnostics (see deploy_log.dump_sandbox_diagnostics output appended to the logs on failures).
- If account CPU limits are hit: run `cleanup_sandboxes.py` to remove stale sandboxes.

Security notes
- Do NOT commit `opencode_info.txt` or preview tokens. These are sensitive. If you paste a token into chat temporarily, rotate it afterwards.
- To share minimally: paste only the two lines: `OPENCODE_ENDPOINT=...` and `OPENCODE_TOKEN=...`.

If you want, paste those two lines here and I'll run the validation and finalize the feature matrix.
