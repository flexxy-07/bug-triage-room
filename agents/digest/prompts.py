"""Prompts for Digest agent (LangGraph + Gemini)."""

SUMMARISE_PROMPT = """You are the Digest agent in an autonomous bug triage room.
Analyze the bug triage conversation below, including the initial human report, the triager classification, and the repro agent's command and execution output.

Conversation:
{thread_context}

Produce a structured summary adhering strictly to this schema:
- Title: <one concise line>
- Severity: <low | med | high>
- Repro: `<exact terminal command executed>`
- Observed: <what happened> / Expected: <what should happen>
- Likely cause: <concise technical explanation>
"""

PROPOSE_FIX_PROMPT = """You are an expert senior software engineer.
Based on the bug summary, reproduction output, and target codebase context below, draft a minimal unified diff patch to fix the bug.

Bug Summary:
{bug_summary}

Reproduction Output:
{repro_output}

Relevant Source Files from TARGET_REPO ({target_repo}):
{codebase_context}

Rules:
1. Provide a minimal, production-grade unified diff (diff -u or git diff format).
2. Do not invent files. Fix the root cause cleanly.
3. Wrap the diff strictly inside a ```diff code block.
4. Do not include commentary outside the diff.
"""

FORMAT_SUMMARY_MESSAGE = """**Bug summary**
- Title: {title}
- Severity: {severity}
- Repro: `{repro_cmd}`
- Observed: {observed} / Expected: {expected}
- Likely cause: {likely_cause}

**Suggested fix**
```diff
{diff_patch}
```

Reply "approve" or "reject"."""

REVISE_PROMPT = """The human reviewer rejected the proposed patch with this feedback:
"{feedback}"

Original Summary:
{bug_summary}

Source Code Context:
{codebase_context}

Please draft a revised minimal unified diff addressing the reviewer's feedback. Wrap strictly in ```diff.
"""
