"""LangGraph definition for Digest agent."""
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END


class DigestState(TypedDict):
    room_history: List[dict]
    bug_summary: Optional[str]
    repro_output: Optional[str]
    suggested_patch: Optional[str]
    approval: Optional[str]
    thread_id: Optional[str]


def create_digest_graph():
    """Build the LangGraph workflow for Digest agent."""
    builder = StateGraph(DigestState)
    # Nodes will be implemented in Checkpoint 7
    return builder

