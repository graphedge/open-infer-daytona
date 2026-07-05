import os
from daytona import Daytona, DaytonaConfig

def recover_ollama_info():
    daytona = Daytona(DaytonaConfig())
    sandboxes = list(daytona.list())
    
    print(f"Found {len(sandboxes)} sandboxes. Searching for Ollama...")
    
    for sb in sandboxes:
        try:
            # Check if ollama is present and serving
            print(f"Checking sandbox {sb.id}...")
            res = sb.process.exec("ollama --version")
            if "ollama" in res.result.lower():
                print(f"Found Ollama in sandbox {sb.id}!")
                
                # Get preview link for Ollama port
                pv = sb.get_preview_link(11434)
                
                with open("ollama_info.txt", "w") as f:
                    f.write(f"OLLAMA_ENDPOINT={pv.url}\n")
                    f.write(f"OLLAMA_TOKEN={pv.token}\n")
                    f.write(f"SANDBOX_ID={sb.id}\n")
                
                print("\n--- OLLAMA INFO RECOVERED ---")
                print(f"Endpoint: {pv.url}")
                print(f"Token: {pv.token}")
                print(f"Sandbox ID: {sb.id}")
                print("Saved to ollama_info.txt")
                return
        except Exception as e:
            print(f"Could not check sandbox {sb.id}: {e}")

    print("Could not find a sandbox running Ollama.")

if __name__ == "__main__":
    recover_ollama_info()
