"""LangGraph Workflow for Digest Agent with Telemetry and Revision Loop."""
import os
import re
import time
from typing import TypedDict, List, Optional, Dict, Any, Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from prompts import SUMMARISE_PROMPT, PROPOSE_FIX_PROMPT, REVISE_PROMPT

load_dotenv()


class DigestState(TypedDict):
    room_history: List[Dict[str, Any]]
    thread_id: Optional[str]
    target_repo: str
    bug_summary: Optional[str]
    repro_output: Optional[str]
    suggested_patch: Optional[str]
    summary_message: Optional[str]
    human_response: Optional[str]
    approval_status: Optional[str]
    feedback: Optional[str]
    final_message: Optional[str]
    revision_count: int
    total_tokens: int
    elapsed_time: float


def _extract_text(content: Any) -> str:
    """Normalize response content whether returned as str, list of parts, or dict."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict):
                parts.append(p.get("text", ""))
            else:
                parts.append(str(p))
        return "".join(parts).strip()
    return str(content).strip()


def _get_llm():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
    )


def _load_codebase_context(target_repo: str) -> str:
    """Read key source files from target repo (read-only) for context."""
    context_parts = []
    src_dir = os.path.join(target_repo, "src", "memcli")
    if not os.path.exists(src_dir):
        return "(Target repo src directory not found)"

    for fname in ["cli.py", "memory.py", "database.py"]:
        fpath = os.path.join(src_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    context_parts.append(f"--- File: src/memcli/{fname} ---\n{content[:6000]}")
            except Exception as e:
                context_parts.append(f"Error reading {fname}: {e}")
    return "\n\n".join(context_parts)


def _format_telemetry(tokens: int, elapsed: float) -> str:
    """Format token count, latency, and estimated cost line."""
    # Gemini 3.5 Flash / Flash-Lite approximate cost: ~$0.10 per 1M tokens
    cost = (tokens / 1_000_000) * 0.10
    return f"_📊 Telemetry: {tokens:,} tokens • {elapsed:.1f}s latency • ~${cost:.5f} est. cost_"


def collect_node(state: DigestState) -> Dict[str, Any]:
    """Collect messages from room history into structured thread context."""
    history = state.get("room_history", [])
    repro_text = ""

    for msg in history:
        content = msg.get("content", "")
        author = msg.get("author", "")
        if "repro" in author.lower() or "reproduced" in content.lower():
            repro_text += f"\n{content}"

    if not repro_text and history:
        repro_text = history[-1].get("content", "")

    return {
        "repro_output": repro_text,
        "total_tokens": state.get("total_tokens", 0),
        "revision_count": state.get("revision_count", 0),
    }


def summarise_node(state: DigestState) -> Dict[str, Any]:
    """Synthesize bug summary from collected thread context."""
    t0 = time.time()
    llm = _get_llm()
    history = state.get("room_history", [])
    thread_text = "\n".join(f"[{m.get('author', 'user')}]: {m.get('content', '')}" for m in history)

    prompt = SUMMARISE_PROMPT.format(thread_context=thread_text)
    res = llm.invoke([HumanMessage(content=prompt)])
    bug_summary = _extract_text(res.content)
    elapsed = time.time() - t0

    # Extract tokens from usage metadata if available
    tokens = getattr(res, "usage_metadata", {}).get("total_tokens", len(prompt.split()) + len(bug_summary.split()))
    current_tokens = state.get("total_tokens", 0) + tokens
    current_elapsed = state.get("elapsed_time", 0.0) + elapsed

    return {
        "bug_summary": bug_summary,
        "total_tokens": current_tokens,
        "elapsed_time": current_elapsed,
    }


def propose_fix_node(state: DigestState) -> Dict[str, Any]:
    """Read target repo context and generate unified diff."""
    t0 = time.time()
    llm = _get_llm()
    target_repo = state.get("target_repo") or os.getenv("TARGET_REPO", "E:/GenAI/Projects/Mem-CLI")
    codebase_context = _load_codebase_context(target_repo)

    prompt = PROPOSE_FIX_PROMPT.format(
        bug_summary=state.get("bug_summary", ""),
        repro_output=state.get("repro_output", ""),
        target_repo=target_repo,
        codebase_context=codebase_context,
    )
    res = llm.invoke([HumanMessage(content=prompt)])
    raw_patch = _extract_text(res.content)
    elapsed = time.time() - t0

    diff_match = re.search(r"```diff\s*(.*?)\s*```", raw_patch, re.DOTALL)
    diff_content = diff_match.group(1).strip() if diff_match else raw_patch.strip("`")

    tokens = getattr(res, "usage_metadata", {}).get("total_tokens", len(prompt.split()) + len(raw_patch.split()))
    current_tokens = state.get("total_tokens", 0) + tokens
    current_elapsed = state.get("elapsed_time", 0.0) + elapsed

    return {
        "suggested_patch": diff_content,
        "total_tokens": current_tokens,
        "elapsed_time": current_elapsed,
    }


def ask_approval_node(state: DigestState) -> Dict[str, Any]:
    """Format and assemble the structured summary, patch, and telemetry."""
    summary = state.get("bug_summary", "")
    diff = state.get("suggested_patch", "")
    tokens = state.get("total_tokens", 0)
    elapsed = state.get("elapsed_time", 0.0)
    telemetry = _format_telemetry(tokens, elapsed)

    rev_tag = f" _(Revision {state.get('revision_count')})_" if state.get("revision_count", 0) > 0 else ""
    formatted_msg = (
        f"**Bug summary**{rev_tag}\n"
        f"{summary}\n\n"
        f"**Suggested fix**\n"
        f"```diff\n{diff}\n```\n\n"
        f"{telemetry}\n\n"
        f"Reply \"approve\" or \"reject\"."
    )
    return {"summary_message": formatted_msg}


def revise_node(state: DigestState) -> Dict[str, Any]:
    """Incorporate human feedback to revise the patch."""
    t0 = time.time()
    llm = _get_llm()
    target_repo = state.get("target_repo") or os.getenv("TARGET_REPO", "E:/GenAI/Projects/Mem-CLI")
    codebase_context = _load_codebase_context(target_repo)
    feedback = state.get("feedback") or state.get("human_response") or "Fix requires adjustment"

    prompt = REVISE_PROMPT.format(
        feedback=feedback,
        bug_summary=state.get("bug_summary", ""),
        codebase_context=codebase_context,
    )
    res = llm.invoke([HumanMessage(content=prompt)])
    raw_patch = _extract_text(res.content)
    elapsed = time.time() - t0

    diff_match = re.search(r"```diff\s*(.*?)\s*```", raw_patch, re.DOTALL)
    diff_content = diff_match.group(1).strip() if diff_match else raw_patch.strip("`")

    tokens = getattr(res, "usage_metadata", {}).get("total_tokens", len(prompt.split()) + len(raw_patch.split()))
    rev_count = state.get("revision_count", 0) + 1

    return {
        "suggested_patch": diff_content,
        "revision_count": rev_count,
        "total_tokens": state.get("total_tokens", 0) + tokens,
        "elapsed_time": state.get("elapsed_time", 0.0) + elapsed,
    }


def finalize_node(state: DigestState) -> Dict[str, Any]:
    """Handle final approval or rejection outcome."""
    resp = (state.get("human_response") or "").strip().lower()
    diff = state.get("suggested_patch", "")
    tokens = state.get("total_tokens", 0)
    elapsed = state.get("elapsed_time", 0.0)
    telemetry = _format_telemetry(tokens, elapsed)

    if "approve" in resp:
        final_msg = f"Approved. Patch ready to apply.\n\n```diff\n{diff}\n```\n\n{telemetry}"
        status = "approved"
    elif "reject" in resp:
        # Extract feedback if present after colon
        fb = resp.split("reject", 1)[-1].strip(":").strip() or "Reviewer requested changes"
        final_msg = f"Proposal rejected with feedback: '{fb}'. Generating revised patch..."
        status = "rejected"
        return {
            "final_message": final_msg,
            "approval_status": status,
            "feedback": fb,
        }
    else:
        final_msg = f"Received response: '{resp}'. Please reply with \"approve\" or \"reject\"."
        status = "pending"

    return {
        "final_message": final_msg,
        "approval_status": status,
    }


def approval_router(state: DigestState) -> Literal["revise", "__end__"]:
    """Route based on human approval status."""
    if state.get("approval_status") == "rejected" and state.get("revision_count", 0) < 2:
        return "revise"
    return "__end__"


def create_digest_graph():
    """Build and compile the LangGraph workflow with MemorySaver checkpointing."""
    workflow = StateGraph(DigestState)

    workflow.add_node("collect", collect_node)
    workflow.add_node("summarise", summarise_node)
    workflow.add_node("propose_fix", propose_fix_node)
    workflow.add_node("ask_approval", ask_approval_node)
    workflow.add_node("finalize", finalize_node)
    workflow.add_node("revise", revise_node)

    workflow.set_entry_point("collect")
    workflow.add_edge("collect", "summarise")
    workflow.add_edge("summarise", "propose_fix")
    workflow.add_edge("propose_fix", "ask_approval")
    workflow.add_edge("ask_approval", "finalize")

    workflow.add_conditional_edges(
        "finalize",
        approval_router,
        {
            "revise": "revise",
            "__end__": END,
        },
    )
    workflow.add_edge("revise", "ask_approval")

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)
