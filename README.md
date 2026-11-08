# Bug Triage Room

> **An autonomous multi-agent system in team chat that triages bug reports, reproduces them in code, and drafts unified diff patches with human-in-the-loop approval.**

![Architecture Diagram](docs/architecture.png)

---

## Overview

Bug Triage Room orchestrates autonomous AI agents directly within a shared team chat room (Mattermost/Switch) to streamline bug resolution:

1. **`@triager`**: Ingests incoming reports, classifies them (`bug`, `question`, or `request`), and routes bugs to `@repro`.
2. **`@repro`**: Reads the target codebase, writes a minimal reproduction script, executes it in an isolated namespace, and posts raw terminal execution traces.
3. **`@digest`**: Custom LangGraph agent connected via the Switch Agent Protocol that performs root-cause analysis, drafts a minimal unified diff patch from the codebase, and waits for a human developer to reply `approve` or `reject`.

```
                  Human (Mattermost channel: #bug-triage)
                                 |
                          Switch Room (shared log)
              +------------------+------------------+
              |                  |                  |
        triager (OpenCode)  repro (OpenCode)   digest (custom, LangGraph)
              |                  |                  |
        Gemini Flash       Gemini Flash        Gemini Flash
                                 |
                        TARGET_REPO (Mem-CLI)
```

---

## Agents

| Agent | Technology | Role |
|---|---|---|
| `triager` | OpenCode + Gemini | Restates the report, classifies it, and routes bugs to `@repro`. |
| `repro` | OpenCode + Gemini | Reads target repository, writes and runs a reproduction script, and posts output. |
| `digest` | Custom LangGraph + Gemini | Ingests thread context over SSE, analyzes code, drafts unified diff fix, and checkpoints for human approval. |

---

## Prerequisites

- **Docker Desktop** (running on Windows, macOS, or Linux)
- **Python 3.11+**
- **Google AI Studio API Key** (`GOOGLE_API_KEY`)
- **Target Repo**: [Mem-CLI](https://github.com/flexxy-07/Mem-CLI) cloned locally with its PostgreSQL 17 + `pgvector` container running.

---

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/flexxy-07/bug-triage-room.git
cd bug-triage-room
```

### 2. Configure Python environment
```bash
python -m venv .venv
.\.venv\Scripts\activate
# On Linux/macOS: source .venv/bin/activate
pip install -r agents/digest/requirements.txt
```

### 3. Set environment variables
Create `.env` from `.env.example`:
```bash
cp .env.example .env
```
Fill in your configuration:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
TARGET_REPO=E:/GenAI/Projects/Mem-CLI
TARGET_RUN_CMD=memcli
SWITCH_SERVER_URL=http://localhost:3000
SWITCH_ROOM_NAME=bug-triage
SWITCH_AGENT_NAME=digest
```

### 4. Setup Target Repository (Mem-CLI)
```bash
git clone https://github.com/flexxy-07/Mem-CLI.git
cd Mem-CLI
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
docker compose up -d
```

---

## Running the Room

### Live Switch Room
1. Import `switch/triage-room.template.yaml` into Switch Console.
2. Start the Digest agent:
   ```bash
   python agents/digest/main.py
   ```
3. Post reports into `#bug-triage` in Mattermost.

### Standalone Local Simulation
You can run and test the complete triage pipeline directly from the terminal without Switch Console:

```bash
# Bug 01 (Subcommand argument order bug):
python agents/digest/main.py --demo --report switch/bug-reports/01-bug.md

# Bug 02 (CSV export line endings bug):
python agents/digest/main.py --demo --report switch/bug-reports/02-bug.md

# Report 03 (Question - handled directly by Triager without repro/digest):
python agents/digest/main.py --demo --report switch/bug-reports/03-question.md
```

---

## Project Structure

```
bug-triage-room/
├── README.md
├── .env.example
├── .gitignore
├── docs/
│   ├── ASSUMPTIONS.md         # Protocol documentation & target bug details
│   ├── architecture.png       # System architecture diagram
│   └── demo-script.md         # End-to-end walkthrough script
├── repro/
│   ├── repro_01.py            # Standalone reproduction script for Bug 01
│   └── repro_02.py            # Standalone reproduction script for Bug 02
├── switch/
│   ├── triage-room.template.yaml   # Switch agent template (triager + repro)
│   └── bug-reports/                # Sample test reports
│       ├── 01-bug.md
│       ├── 02-bug.md
│       └── 03-question.md
└── agents/
    └── digest/
        ├── main.py            # Entrypoint & Switch listener
        ├── switch_client.py   # Switch Agent Protocol client (SSE + HTTP)
        ├── graph.py           # LangGraph state machine & telemetry
        ├── prompts.py         # Synthesis & patch prompts
        └── requirements.txt
```

---

## License

MIT License. Developed by [flexxy-07](https://github.com/flexxy-07).
