# Digest Agent

Custom autonomous agent for the Bug Triage Room, built with **LangGraph** and **Gemini**, connecting via the **Switch Agent Protocol**.

## Architecture & State Machine

The agent joins the Switch room via SSE (Server-Sent Events) and HTTP POST. When mentioned (`@digest`), it triggers a LangGraph state machine:

1. `collect`: Gather thread messages (original report, triager classification, repro command & output).
2. `summarise`: Gemini generates a structured summary (Title, Severity, Observed vs Expected, Likely cause).
3. `propose_fix`: Gemini inspects target repo source code and drafts a minimal unified diff patch.
4. `ask_approval`: Posts the summary and diff to the room, requesting `Reply "approve" or "reject".`
5. `await_human`: Checkpointed wait for human response.
6. `finalize`: Upon "approve", posts patch ready to apply. Upon "reject", requests feedback.

## Running the Agent

```bash
cd agents/digest
pip install -r requirements.txt
python main.py
```
