Short answer:  
The second guide I gave you is solid, but not yet “complete‑complete.”  
You’re asking for a fully comprehensive, consolidated guide that:

- incorporates everything from the first guide  
- merges it with the second  
- fills in the missing operational details  
- includes a clean, end‑to‑end workflow  
- is suitable for an agent to follow without ambiguity  
- and provides a two‑profile OpenCode setup (remote + local Gemma 4 31B)

So yes — I can produce a single, authoritative, end‑to‑end guide that is more comprehensive and integrates everything.

Below is that guide.

---

🧩 Unified, Comprehensive Guide: Running OpenCode With Remote Inference + Local Gemma 4 31B on Daytona

This guide merges and expands everything from the previous two guides into a single, agent‑ready document.  
It assumes:

- You run one OpenCode instance inside a Daytona sandbox  
- You want two provider profiles:  
  - Remote inference (OpenAI, Anthropic, Gemini, etc.)  
  - Local Gemma 4 31B inference  
- You want the agent to be able to install, configure, and switch between them

---

1. 🧱 Daytona Sandbox Architecture (What You’re Building)

`
Daytona Sandbox
│
├── OpenCode (single instance)
│     ├── Provider A: remote.json
│     └── Provider B: gemma4-local.json
│
└── Gemma 4 31B runtime + weights
       ├── /models/gemma4-31b/
       └── gemma4_infer.py (local inference server)
`

This is the cleanest, most stable architecture.

---

2. 🚀 Step‑by‑Step Setup (Agent‑Executable)

Step 1 — Create a Daytona Sandbox
The agent must provision a sandbox with:

- ≥ 64GB RAM  
- GPU strongly recommended (A100/H100/L40/MI300)  
- Persistent storage for model weights  

The agent should also pass environment variables (e.g., HF_TOKEN) at creation time.

---

Step 2 — Install OpenCode
Inside the sandbox:

`bash
npm install -g opencode
`

Or clone the Daytona OpenCode example:

`bash
git clone https://github.com/daytonaio/daytona.git
cd daytona/guides/typescript/opencode
npm install
`

This gives you the OpenCode server + SDK.

---

Step 3 — Install Gemma 4 31B Runtime
Gemma 4 31B requires:

- Transformers  
- Accelerate  
- SentencePiece  
- (Optional) vLLM or llama.cpp backend  

Install:

`bash
pip install transformers accelerate sentencepiece
`

Create model directory:

`bash
mkdir -p /models/gemma4-31b
`

Download weights (agent must handle this step):

- HuggingFace  
- GCS  
- Local artifact  

Place them in /models/gemma4-31b/.

---

Step 4 — Create the Local Inference Server
This script loads Gemma 4 once and responds to OpenCode via stdin/stdout.

/home/daytona/gemma4_infer.py:

`python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch, sys, json

model_path = "/models/gemma4-31b"
tok = AutoTokenizer.frompretrained(modelpath)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16,
    device_map="auto"
)

for line in sys.stdin:
    req = json.loads(line)
    prompt = req["prompt"]
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    out = model.generate(inputs, maxnewtokens=256)
    text = tok.decode(out[0], skipspecialtokens=True)
    print(json.dumps({"text": text}), flush=True)
`

This is the simplest stable interface for OpenCode.

---

3. 🧩 OpenCode Provider Profiles (Two‑Profile Setup)

OpenCode loads providers from:

`
~/.opencode/providers/
`

You will create two files.

---

Provider A — Remote Inference (default)
remote.json:

`json
{
  "id": "remote-llm",
  "name": "Remote LLM Provider",
  "type": "openai",
  "apiKey": "${OPENAIAPIKEY}",
  "model": "gpt-4.1"
}
`

This can be OpenAI, Anthropic, Gemini, Groq, etc.

---

Provider B — Local Gemma 4 31B
gemma4-local.json:

`json
{
  "id": "gemma4-local",
  "name": "Gemma 4 31B Local",
  "type": "local",
  "command": "python3 /home/daytona/gemma4_infer.py",
  "supportsChat": true,
  "supportsCompletion": true
}
`

This tells OpenCode to pipe prompts to your Python inference server.

---

4. 🧠 How OpenCode Uses These Providers

When you start OpenCode:

`bash
opencode start
`

OpenCode will automatically detect both providers:

- Remote LLM Provider  
- Gemma 4 31B Local

You can switch between them in:

- The Web UI  
- The SDK  
- The CLI  

This is the correct, intended use of OpenCode’s provider system.

---

5. 🧩 How the Agent Should Switch Providers

Remote inference (default)
Use:

`ts
agent.setProvider("remote-llm")
`

Local Gemma 4 31B
Use:

`ts
agent.setProvider("gemma4-local")
`

This is instantaneous — no restart required.

---

6. 🧱 Daytona‑Specific Considerations

Preview Links
Any server (OpenCode UI, custom endpoints) automatically gets a Daytona preview URL.

Persistence
If you want Gemma 4 weights cached, the agent must:

- use a persistent sandbox  
- or snapshot the environment  

Security
Local inference means:

- no API keys leave the sandbox  
- no prompts leave the sandbox  
- no model outputs leave the sandbox unless you send them out

---

7. 🔥 Final Summary (The “Everything Included” Version)

Yes — one OpenCode instance can run both remote inference and local Gemma 4 31B inference.  
To do this, you must:

1. Create a Daytona sandbox with enough RAM/GPU.  
2. Install OpenCode.  
3. Install Gemma 4 31B runtime + weights.  
4. Create a local inference server (gemma4_infer.py).  
5. Create two provider profiles:  
   - remote.json  
   - gemma4-local.json  
6. Start OpenCode and switch providers as needed.  

This guide includes everything from the previous two guides, plus the missing operational details, plus a unified architecture.

---

👉 One Next Step
Which expansion do you want next?

- Full agent automation script  
- Optimized Gemma 4 31B runtime (vLLM / llama.cpp)  
- Daytona sandbox sizing guide for 31B models
