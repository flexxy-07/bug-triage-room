# BUILD_SPEC.md: Bug Triage Room (Flip the Switch Hackathon)

> You are the coding agent building this project. Read this whole file first, then build in the order given in section 9. Do not skip the checkpoints.

---

## 0. Hard rules for the agent

1. **Do not invent Switch APIs.** Before writing any code that talks to Switch (agent protocol, endpoints, auth, event formats), read the real docs: https://docs.switchagents.ai and the repo https://github.com/sandbox-quantum/switch (see `examples/agent-templates/`). The docs are also served over MCP at `https://docs.switchagents.ai/mcp`. If something is unclear, write down the assumption in `docs/ASSUMPTIONS.md` and keep going.
2. **Smallest working thing first.** Every checkpoint in section 9 must work before starting the next.
3. **Never commit secrets.** Keys live in `.env`; only `.env.example` is committed.
4. **Keep it reproducible.** A stranger must be able to clone the repo, follow the README, and see the demo work.
5. **Time budget is about 8 hours total.** If a step eats more than its budget, apply the fallback listed in section 10.
6. Write short, plain code. No over-engineering, no unnecessary abstractions.

---

## 1. Context

- **Event:** Flip the Switch Hackathon (WeMakeDevs x DevTools Academy x Switch), submissions close Nov 7, 11:59 PM IST.
- **Track:** Track 01, Best Business Workflow. Side tracks to also enter: Best Blog (optional), Code with Wispr (only if used).
- **Switch** is open-source infra that puts AI agents into team chat. Each channel is a "room", and agents join it like teammates. Agents speak the Switch Agent Protocol (HTTP out, SSE in). **Switch Console** (desktop app) runs CLI agents and a local Docker server, and bundles Mattermost for chat.
- **Judging weights:** Use of Switch (Switch must be central), Technical execution (reproducible), Creativity and impact, Presentation (README + demo video).
- **Environment:** Windows, native. Switch Console has a Windows build (early access). Docker Desktop is required. **Do not use WSL for development unless the native path is clearly broken** (see section 10).
- **LLM:** Gemini free tier (Google AI Studio API key). No Claude or Codex available.

---

## 2. Project summary

**Bug Triage Room**: a Mattermost channel where a human posts a bug report and three agents resolve it together:

| Agent | Runs as | Job |
|---|---|---|
| `triager` | OpenCode + Gemini (via Switch Console) | Restates the report in one line, classifies it as bug / question / request, routes bugs to `repro` by name |
| `repro` | OpenCode + Gemini (via Switch Console) | Writes the smallest script that reproduces the bug in the **target repo**, runs it, posts exact output in the thread |
| `digest` | **Custom** LangGraph + Gemini agent, joins via the Switch Agent Protocol | Reads the room, posts a structured summary and a suggested fix, then waits for human approval |

The human stays in the loop: the human files the bug and gives the final approve/reject on the fix. Without Switch, the three agents would not share a room, a history, or a way to hand work to each other.

**One-line pitch:** "A bug report goes into chat. Three agents triage it, reproduce it, and propose a fix. A human approves. All in one Switch room."

---

## 3. Architecture

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
                        TARGET_REPO (a real project)
```

Flow:
1. Human posts a bug in the room, mentioning `@triager`.
2. `triager` restates, classifies, and if it's a bug, mentions `@repro` with the details.
3. `repro` writes `repro/repro_<id>.py` inside the target repo, runs it, and replies in the thread with the exact output.
4. `repro` mentions `@digest`.
5. `digest` reads the room history, produces the summary + suggested patch (as a diff in a code block), and asks the human: `Reply "approve" or "reject".`
6. Human replies. `digest` acknowledges and, on approve, posts the final patch ready to apply. (Applying the patch automatically is a stretch goal. See section 11.)

---

## 4. Repo structure

```
bug-triage-room/
├── README.md                  # see section 8
├── BUILD_SPEC.md              # this file
├── .env.example
├── .gitignore
├── docs/
│   ├── ASSUMPTIONS.md         # any guesses made about Switch
│   ├── architecture.png       # exported from the diagram
│   └── demo-script.md         # section 12
├── switch/
│   ├── triage-room.template.yaml   # Switch agent template (triager + repro)
│   └── bug-reports/                # 3 sample reports to paste in (written against TARGET_REPO)
│       ├── 01-bug.md
│       ├── 02-bug.md
│       └── 03-question.md          # non-bug, tests classification
└── agents/
    └── digest/
        ├── main.py            # entrypoint, connects to the room
        ├── switch_client.py   # thin client for the Switch Agent Protocol
        ├── graph.py           # LangGraph definition
        ├── prompts.py
        ├── requirements.txt
        └── README.md
```

---

## 5. Target repo: Mem-CLI

Target: https://github.com/flexxy-07/Mem-CLI (the user's own project). Do **not** build a demo app. Clone it locally and set `TARGET_REPO` in `.env` to its absolute path.

**What it is:** a Python CLI (`memcli`) that gives LLM agents persistent memory. LangGraph short-term memory plus PostgreSQL 17 + pgvector long-term memory (HNSW on `halfvec(3072)`), Gemini embeddings, semantic deduplication (cosine >= 0.95 refreshes the existing row), LLM-arbiter conflict resolution (0.75 <= sim < 0.95 may supersede an old memory), and GDPR-style `forget` / `export` / `clear`. Code is in `src/memcli/` (`agent.py`, `arbiter.py`, `cli.py`, `database.py`, `embeddings.py`, `memory.py`).

**Why it's a good target:** it is a real project with real edge cases, it already uses Gemini (so no extra provider), and the agents can exercise it entirely through CLI commands.

**Setup for the target (do this once, follow its README):**
1. `python -m venv .venv`, activate, `pip install -e .`
2. Copy `.env.example` to `.env`, fill in `GOOGLE_API_KEY`. Host Postgres port is `5433`.
3. `docker compose up -d` (this is Mem-CLI's own Postgres, separate from Switch's Docker stack, so check for port clashes).
4. `memcli list` must work. Record `TARGET_RUN_CMD=memcli` in this project's `.env`.

**Rules for the repro agent on this target:**
- Always use a throwaway namespace: `memcli -u repro-bot ...`. Never touch other users' data. Run `memcli clear -u repro-bot --confirm` at the end of each repro.
- Write repro scripts to `$TARGET_REPO/repro/` (add `repro/` to Mem-CLI's `.gitignore`). Scripts are shell or Python that call `memcli` commands and print outputs.
- Never edit files under `src/`. Read only.
- Keep API calls minimal. Gemini free tier is rate limited and Mem-CLI spends quota on both LLM and embedding calls on every write. Prefer `memcli remember` / `list` / `search` / `export` (cheap) over `chat`.

**Bug reports (`switch/bug-reports/`):**
- Reports 01 and 02 must describe **real** problems in Mem-CLI. First ask the user whether they know of any bugs or rough edges. If not, probe by hand in the `repro-bot` namespace and find them. Good areas to probe: dedup behaviour near the 0.95 and 0.75 thresholds, whether near-duplicate phrasings create extra rows, conflict resolution on changed preferences (does the old row become inactive with `superseded_by` set?), `forget` by semantic query matching too much or too little, `export --active-only` and CSV escaping of commas/quotes/newlines in memory text, behaviour with empty or very long input, and behaviour when the database is down or `GOOGLE_API_KEY` is missing (error clarity).
- Write them like a real user: short, vague, no stack traces, e.g. "I told it I switched from Java to Rust but `memcli list` still shows both."
- Report 03 is a plain question, e.g. "Does Mem-CLI support multiple users, and how do I keep their memories separate?" (tests the non-bug path).
- Record the real underlying problems in `docs/ASSUMPTIONS.md`, never in the report files.
- If probing finds no clear bug, report a genuine missing behaviour or unclear error message instead. Do not fabricate bugs or modify Mem-CLI to create them.

**Demo narrative:** "Mem-CLI is my own project. I built a Switch room where agents triage, reproduce, and propose fixes for bugs in it." Dogfooding makes the story credible.

---

## 6. Switch setup (triager + repro)

Create `switch/triage-room.template.yaml` based on Switch's official `triage-pair.template.yaml` (https://github.com/sandbox-quantum/switch/blob/main/examples/agent-templates/triage-pair.template.yaml). **Read it first and match its exact schema.** Use these instructions as a starting point.

**triager**
```
You are the triager of a small engineering team. For each report posted in this room:
1. Restate it in one line.
2. Classify it as exactly one of: bug, question, request.
3. If bug: mention @repro by name with the one-line restatement and any details from the report. Do not guess the cause.
4. If question or request: answer briefly yourself or say who should handle it. Do not mention @repro.
Keep every message under 6 lines. Never write code.
```

**repro**
```
You reproduce bugs in the project located at the path in TARGET_REPO.
When @triager routes a bug to you:
1. Read the relevant source files in the target repo. Do not modify them.
2. Write the smallest script in the target repo's repro/ folder that demonstrates the bug.
3. Run it and post the exact command and exact output in this thread.
4. State in one line what is wrong, based on the output only.
5. Mention @digest so it can summarise and propose a fix.
If you cannot reproduce it, say so and list what you tried.
```

Both agents use `provider: opencode` (verify the exact provider name from the template/docs) with the Gemini model configured in OpenCode. Use a Flash-class Gemini model for rate limits. Verify the current model ID in Google AI Studio.

OpenCode + Gemini config: set `GEMINI_API_KEY` (or the env var OpenCode expects for Google, so check OpenCode docs) before launching Console.

The room: `name: bug-triage`, bridge: Mattermost (bundled local server). Add the human user as creator.

**Kickoff message** in the template:
`@triager and @repro: this is the bug triage room. @digest will join to summarise and propose fixes.`

---

## 7. Custom agent: `digest` (LangGraph + Gemini)

This is the differentiator. It must join the room through the **Switch Agent Protocol**, not through Console.

### 7.1 `switch_client.py`
- After reading the protocol docs, implement a minimal client:
  - Open the SSE stream for the room and parse incoming events.
  - Send messages via the HTTP endpoint.
  - Handle auth/registration exactly as documented.
  - Reconnect with simple backoff on drop.
- Expose: `async def listen() -> AsyncIterator[Event]` and `async def send(text: str, thread_id: str | None = None)`.
- Ignore the agent's own messages. Respond only when mentioned by exact name (`@digest`), because Switch agents ignore un-mentioned messages by convention.

### 7.2 `graph.py` (LangGraph)
State: `{room_history, bug_summary, repro_output, suggested_patch, approval}`.

Nodes:
1. `collect`: gather the relevant thread messages (original report, triager classification, repro command and output).
2. `summarise`: Gemini produces a structured summary: **Title / Severity (low-med-high) / Steps to reproduce / Observed vs expected / Likely root cause.**
3. `propose_fix`: Gemini reads the relevant files from `TARGET_REPO` (read-only) and drafts a minimal unified diff.
4. `ask_approval`: post the summary and the diff, then ask: `Reply "approve" or "reject".`
5. `await_human`: wait for the next human message in the thread. Interrupt/resume with LangGraph checkpointing (`MemorySaver` is fine).
6. `finalize`: on `approve`, post "Approved. Patch ready to apply" plus the diff again. On `reject`, ask for one line of feedback and loop to `propose_fix` once.

Use `langchain-google-genai` with model from `GEMINI_MODEL` env var. Temperature 0.2. Keep prompts in `prompts.py`.

**Output format for the summary message** (keep it short, Mattermost-friendly markdown):

```
**Bug summary**
- Title: ...
- Severity: ...
- Repro: `command`
- Observed: ... / Expected: ...
- Likely cause: ...

**Suggested fix**
```diff
...
```
Reply "approve" or "reject".
```

### 7.3 `main.py`
Wire client -> graph. Print clear logs (`[digest] mentioned in thread X`, `[digest] waiting for approval`). Run with `python main.py`.

---

## 8. README requirements (judges read this)

README.md must include, in this order:
1. Title, one-line pitch, demo GIF or video link at the top.
2. **Why Switch is central:** a short paragraph plus a bullet list ("without Switch there is no shared room, no handoff between agents, no human approval in chat").
3. Architecture diagram (`docs/architecture.png`) and the flow from section 3.
4. **Prerequisites:** Docker Desktop, Switch Console (Windows early-access build), Python 3.11+, a Gemini API key, a local clone of Mem-CLI (with its own Postgres container running).
5. **Setup in under 10 steps:** copy-paste commands, from clone to a working room, including setting `TARGET_REPO`.
6. **Run the demo:** which bug reports to paste, and what to expect from each agent.
7. Agent descriptions (table from section 2).
8. Honest limitations and what is next.
9. `#HowISwitch` link, license, credits.

---

## 9. Build order and checkpoints

| # | Task | Checkpoint (must pass) | Budget |
|---|---|---|---|
| 1 | Repo scaffold, `.gitignore`, `.env.example` | Repo exists, structure matches section 4 | 15 min |
| 2 | Clone and set up Mem-CLI (section 5), confirm `memcli list` works, find 2 real issues, write 3 bug reports | `memcli` runs against Docker Postgres, 2 real issues reproducible by hand | 45 min |
| 3 | Read Switch docs, write `docs/ASSUMPTIONS.md` | Protocol and template schema summarised | 20 min |
| 4 | Template YAML (triager + repro) | Room created in Console, `@triager` replies in Mattermost | 60 min |
| 5 | Full flow with 2 agents | Bug report 01 gets classified, routed, reproduced with real output | 45 min |
| 6 | `switch_client.py` | Client connects, receives a mention, posts a reply in the room | 60 min |
| 7 | LangGraph `digest` agent | End-to-end: repro output leads to summary + diff + approval | 75 min |
| 8 | Run all 3 sample reports | Report 03 is not routed to repro, 01 and 02 complete | 20 min |
| 9 | README, diagram, demo video, polish | Section 8 satisfied, video recorded | 90 min |
| 10 | Submit | Submission confirmed | 15 min |

After each checkpoint, commit with a clear message.

---

## 10. Fallbacks (apply without asking)

- **Console won't run natively on Windows within 90 minutes:** only then fall back to WSL2 + Docker Desktop and the Linux build. Otherwise stay native.
- **Gemini rate limited:** Mem-CLI, OpenCode agents, and `digest` all share the free tier. Use a separate API key (ideally a separate Google project) for the Switch agents vs. Mem-CLI, use a Flash-Lite or smaller variant, add retry with backoff, shorten prompts, and pre-record or pace the demo to avoid bursts.
- **Agent protocol client takes more than 2 hours:** ship with two agents (triager + repro) and make `digest` a "stretch goal" in the README. Do not leave half-working code in `main`.
- **OpenCode will not use Gemini:** run `triager` and `repro` as custom protocol agents using the same `switch_client.py` and a simple LangChain loop.
- **Repro agent can't run code:** have it post the script and the expected output, then run it via a small `run_repro.sh` helper.

---

## 11. Stretch goals (only if everything above works)

- `digest` applies the approved patch to the target repo and runs its tests, posting the result.
- Cost/latency line at the end of each digest message.
- A fourth bug report that triggers the "reject" loop.
- Connect a second chat platform (Discord) to show the same room across platforms.

---

## 12. Demo video script (2 minutes max)

1. (0:00) One sentence: the problem. "Bug reports pile up in chat and nobody reproduces them."
2. (0:10) Show the Mattermost room and the three agents in the member list.
3. (0:20) Paste bug report 01. Show triager classify and route.
4. (0:40) Show repro write and run the script, with real output.
5. (1:00) Show digest post the summary and diff.
6. (1:20) Human replies `approve`. Show the final message.
7. (1:35) Paste bug report 03 (a question) to show the classification path.
8. (1:45) Close on the architecture diagram: "Switch is the room that makes the handoffs possible."

---

## 13. Submission checklist

- [ ] Public GitHub repo, README complete
- [ ] `.env.example` present, no secrets committed
- [ ] Demo video linked in README and submission form
- [ ] Architecture diagram in `docs/`
- [ ] Works from a clean clone (test it)
- [ ] Track 01 selected; Best Blog / Code with Wispr entered only if applicable
- [ ] `#HowISwitch` post published
- [ ] Submit on wemakedevs.org/hackathons/switch before 11:59 PM IST

---

## 14. Definition of done

A stranger clones the repo, follows the README, pastes `01-bug.md` into the room, and within a couple of minutes sees: triager classify and route, repro show real output, digest propose a diff, and the human approve it. All through Switch.
