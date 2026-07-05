import os
import sys
import time
import requests
from dotenv import load_dotenv
from daytona import (
    CreateSandboxFromImageParams,
    Daytona,
    DaytonaConfig,
    GpuType,
    Image,
    Resources,
    SessionExecuteRequest,
)

load_dotenv()

# --- Configuration ---
MODEL = "google/gemma-4-31b" # Adjusted to the user's requested model
SERVED_AS = "gemma-4-31b"
VLLM_IMAGE = "vllm/vllm-openai:v0.22.1"
PORT = 8000
TARGET = "us-east-1"  # current region for GPU sandboxes
SESSION = "vllm"
BOOT_TIMEOUT = 900

def dump_log(cmd_id):
    # Simple implementation to save logs if boot fails
    pass

def serve_vllm():
    daytona = Daytona(DaytonaConfig())
    
    env_vars = {}
    if os.environ.get("HF_TOKEN"):
        env_vars["HF_TOKEN"] = os.environ["HF_TOKEN"]

    print(f"Creating GPU sandbox with image {VLLM_IMAGE}...")
    sb = daytona.create(
        CreateSandboxFromImageParams(
            image=Image.base(VLLM_IMAGE),
            resources=Resources(
                gpu=1,
                gpu_type=[GpuType.H100, GpuType.RTX_PRO_6000],
            ),
            auto_stop_interval=0,
            ephemeral=True,
            env_vars=env_vars,
        ),
        timeout=600,
    )
    
    print(f"Sandbox created: {sb.id}")

    print(f"Starting vLLM server for {MODEL}...")
    cmd = sb.process.execute_session_command(
        SESSION,
        SessionExecuteRequest(
            command=(
                f"vllm serve {MODEL} --port {PORT} "
                f"--served-model-name {SERVED_AS} "
                "--enable-auto-tool-choice --tool-call-parser gemma4 "
                "--reasoning-parser gemma4 "
                "--enable-prefix-caching"
            ),
            run_async=True,
        ),
    )
    cmd_id = cmd.cmd_id

    pv = sb.get_preview_link(PORT)
    hdr = {"x-daytona-preview-token": pv.token}
    
    deadline = time.time() + BOOT_TIMEOUT
    ready = False
    printed = 0
    
    print(f"Waiting for server at {pv.url}...")

    while time.time() < deadline:
        # Logs
        out = sb.process.get_session_command_logs(SESSION, cmd_id).output or ""
        if len(out) > printed:
            sys.stdout.write(out[printed:])
            sys.stdout.flush()
            printed = len(out)
            
        # Check exit code
        exit_info = sb.process.get_session_command(SESSION, cmd_id)
        if exit_info.exit_code is not None:
            print(f"!! vllm exited with code {exit_info.exit_code}")
            sys.exit(1)
            
        # Health check
        try:
            resp = requests.get(f"{pv.url}/health", headers=hdr, timeout=10)
            if resp.status_code == 200:
                ready = True
                break
        except requests.RequestException:
            pass
            
        time.sleep(10)

    if not ready:
        print("Timeout waiting for server to become healthy.")
        sys.exit(1)

    print("\n--- SERVER READY ---")
    print(f"export VLLM_ENDPOINT={pv.url}")
    print(f"export VLLM_TOKEN={pv.token}")
    print(f"sandbox_id: {sb.id}")
    print("--------------------")
    
    # In a real scenario, we might want the script to stay alive to keep the session 
    # or pass control back. For this task, we keep the subprocess running.
    # However, in this Python script, the cmd is in the background. 
    # To prevent the script from immediately exiting and potentially the session 
    # being cleaned up (though ephemeral=True and auto_stop=0 should prevent this),
    # we'll wait.
    
    print("Server is running. Press Ctrl+C to exit the management script (the sandbox will remain UP).")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    try:
        serve_vllm()
    except KeyboardInterrupt:
        print("\nManagement script stopped.")
