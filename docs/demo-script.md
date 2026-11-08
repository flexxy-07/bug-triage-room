# Demo Video Script (2 minutes max)

This script follows Section 12 of `BUILD_SPEC.md` for the Flip the Switch Hackathon demo.

---

### Step 1 (0:00 - 0:10): The Problem
- **Voiceover / Text:** "Bug reports pile up in team chat and nobody reproduces them before developers spend hours debugging. Today, we show the Bug Triage Room powered by Switch."
- **Visual:** Show empty or busy chat channel `#bug-triage` in Mattermost.

---

### Step 2 (0:10 - 0:20): The Switch Room & Agents
- **Voiceover / Text:** "We have a Switch room `#bug-triage` connected to Mattermost with three agents: `@triager`, `@repro`, and `@digest`."
- **Visual:** Show the member list in Mattermost with human and the 3 agents.

---

### Step 3 (0:20 - 0:40): Bug Report 01 (Classify & Route)
- **Action:** Paste `01-bug.md` into the room mentioning `@triager`.
- **Expected:** `@triager` replies within seconds:
  1. Restates the bug in one line.
  2. Classifies as `bug`.
  3. Mentions `@repro` with details.

---

### Step 4 (0:40 - 1:00): Repro Execution
- **Expected:** `@repro` generates a minimal reproduction script in `TARGET_REPO/repro/`, executes it against the isolated `repro-bot` namespace, outputs the actual command output, and mentions `@digest`.
- **Visual:** Highlight the exact terminal output posted right in the chat thread.

---

### Step 5 (1:00 - 1:20): Digest Summary & Suggested Fix
- **Expected:** `@digest` (custom LangGraph agent via Switch Agent Protocol) synthesizes the thread history, provides structured summary (Title, Severity, Observed vs Expected, Likely cause), drafts a unified diff patch, and asks:
  `Reply "approve" or "reject".`

---

### Step 6 (1:20 - 1:35): Human in the Loop (Approval)
- **Action:** Human replies `approve`.
- **Expected:** `@digest` acknowledges and outputs: `Approved. Patch ready to apply.`

---

### Step 7 (1:35 - 1:45): Question Classification Path
- **Action:** Paste `03-question.md` mentioning `@triager`.
- **Expected:** `@triager` answers directly and does *not* route to `@repro`.

---

### Step 8 (1:45 - 2:00): Closing & Switch Architecture
- **Voiceover / Text:** "Switch provides the shared room and protocol that makes autonomous multi-agent handoff and human-in-the-loop triage seamless."
- **Visual:** Display `docs/architecture.png`.
