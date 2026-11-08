# Bug Triage Room (Flip the Switch Hackathon)

> **A bug report goes into chat. Three agents triage it, reproduce it, and propose a fix. A human approves. All in one Switch room.**

[Demo Video Link / GIF will be added here]

---

## Why Switch is Central

In traditional software workflows, bug triage is fragmented: issue trackers, terminal repros, PR discussions, and chat notifications live in completely separate silos. Developers manually reproduce bugs and coordinate fixes across disjointed tools.

Without Switch:
- There is **no shared room** where humans and autonomous AI agents collaborate in real-time.
- There is **no agent-to-agent handoff** (e.g. `@triager` identifying a bug and calling `@repro`, which in turn hands execution traces to `@digest`).
- There is **no shared event log** giving all agents synchronized context without complex ad-hoc plumbing.
- There is **no native human-in-the-loop approval** in the same conversation thread where agents work.

Switch provides the multi-agent chat infrastructure, standard protocol, and room lifecycle that make this autonomous pipeline possible.

---

## Architecture & Flow

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

1. **Human** posts a bug report in `#bug-triage` mentioning `@triager`.
2. **`@triager`** restates the report, classifies it (`bug` / `question` / `request`), and if it is a bug, mentions `@repro`.
3. **`@repro`** writes a minimal repro script in `TARGET_REPO/repro/`, executes it against an isolated namespace, and replies with exact terminal output.
4. **`@repro`** mentions `@digest`.
5. **`@digest`** (custom LangGraph agent via Switch Agent Protocol) synthesizes the thread, generates a structured summary + unified diff patch, and asks the human to approve or reject.
6. **Human** replies `approve` (or `reject`). `@digest` finalizes and provides the patch ready for merge.

---

## Agents

| Agent | Runs as | Role |
|---|---|---|
| `triager` | OpenCode + Gemini (via Switch Console) | Restates report in 1 line, classifies bug/question/request, routes bugs to `@repro` |
| `repro` | OpenCode + Gemini (via Switch Console) | Reads target repo, writes minimal repro script to `repro/`, runs it, posts output, calls `@digest` |
| `digest` | Custom LangGraph + Gemini agent (Switch Agent Protocol) | Analyzes thread, generates structured summary + unified diff fix, waits for human approval |

---

## Prerequisites

1. **Docker Desktop** (running on Windows)
2. **Switch Console** (or Switch server container)
3. **Python 3.11+** (Python 3.12 verified)
4. **Google AI Studio Gemini API Key** (`GOOGLE_API_KEY`)
5. **Mem-CLI** (Target repo, cloned locally with its PostgreSQL + pgvector container running on port 5433)

---

## Quick Setup (< 10 Steps)

1. Clone this repository:
   ```bash
   git clone https://github.com/flexxy-07/bug-triage-room.git
   cd bug-triage-room
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
3. Copy environment configuration and set keys:
   ```bash
   cp .env.example .env
   # Edit .env with your GOOGLE_API_KEY and absolute TARGET_REPO path
   ```
4. Install digest agent dependencies:
   ```bash
   pip install -r agents/digest/requirements.txt
   ```
5. Clone and set up the target repo [Mem-CLI](https://github.com/flexxy-07/Mem-CLI):
   ```bash
   # In a separate directory
   git clone https://github.com/flexxy-07/Mem-CLI.git
   cd Mem-CLI
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -e .
   docker compose up -d
   memcli list
   ```
6. Launch Switch Console and import `switch/triage-room.template.yaml`.
7. Start the custom digest agent:
   ```bash
   python agents/digest/main.py
   ```
8. Open Mattermost (`#bug-triage`) and start posting!

---

## Running the Demo

Test scenarios are located in `switch/bug-reports/`:
- `01-bug.md`: Real issue in Mem-CLI -> full 3-agent triage, repro, and fix flow.
- `02-bug.md`: Second real issue in Mem-CLI -> full flow.
- `03-question.md`: Question -> `@triager` answers directly without triggering `@repro`.

---

## Limitations & Next Steps

- **Automatic Patch Application:** Currently, `@digest` generates unified diffs for human review. Automatic branch creation and git commit application is a natural next step.
- **Cross-Platform Rooms:** Switch supports bridging rooms to Slack, Discord, and Mattermost simultaneously.
- **Enhanced Verification:** Running automated pytest regression suites before marking patches as approved.

---

## Credits & License

- Built for the **Flip the Switch Hackathon** (WeMakeDevs x DevTools Academy x Switch).
- Target system: [Mem-CLI](https://github.com/flexxy-07/Mem-CLI) by flexxy-07.
- License: MIT.
- Tag: `#HowISwitch`

