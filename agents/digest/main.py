"""Main Entrypoint for Digest Agent.

Wires SwitchClient (SSE + HTTP) to the LangGraph workflow.
Supports live Switch rooms as well as standalone local demo mode.
"""
import argparse
import asyncio
import logging
import os
import sys
from typing import Dict, Any

from dotenv import load_dotenv

# Ensure local imports work cleanly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from switch_client import SwitchClient, SwitchEvent
from graph import create_digest_graph, DigestState

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("digest")


class DigestAgent:
    """Manages room state, threads, and LangGraph invocations."""

    def __init__(self, client: SwitchClient, target_repo: str):
        self.client = client
        self.target_repo = target_repo
        self.graph = create_digest_graph()
        self.threads: Dict[str, Dict[str, Any]] = {}

    async def handle_event(self, event: SwitchEvent):
        """Handle incoming message event from Switch."""
        thread_id = event.thread_id or "default"
        logger.info(f"Incoming event from {event.author} in thread '{thread_id}'")

        # Check if this agent is addressed
        if not event.is_mention(self.client.agent_name):
            # If we are waiting for human approval in this thread, check for approve/reject
            if thread_id in self.threads and self.threads[thread_id].get("awaiting_approval"):
                content = event.content.strip().lower()
                if "approve" in content or "reject" in content:
                    logger.info(f"Received human review in thread '{thread_id}': {event.content}")
                    await self._process_approval(thread_id, event.content)
            return

        logger.info(f"[@digest mentioned] in thread '{thread_id}': {event.content}")

        # If already tracking, append message
        if thread_id not in self.threads:
            self.threads[thread_id] = {
                "history": [],
                "awaiting_approval": False,
                "current_state": None,
            }

        self.threads[thread_id]["history"].append({
            "author": event.author,
            "content": event.content,
        })

        # Run pipeline
        await self._process_digest(thread_id)

    async def _process_digest(self, thread_id: str):
        """Run LangGraph pipeline to generate summary and patch."""
        logger.info(f"Running Digest LangGraph workflow for thread '{thread_id}'...")

        initial_state: DigestState = {
            "room_history": self.threads[thread_id]["history"],
            "thread_id": thread_id,
            "target_repo": self.target_repo,
            "bug_summary": None,
            "repro_output": None,
            "suggested_patch": None,
            "summary_message": None,
            "human_response": None,
            "approval_status": None,
            "final_message": None,
            "revision_count": 0,
        }

        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke(initial_state, config=config)

        self.threads[thread_id]["current_state"] = result
        self.threads[thread_id]["awaiting_approval"] = True

        summary_msg = result.get("summary_message", "")
        logger.info(f"Posting summary and patch to thread '{thread_id}'...")
        await self.client.send(summary_msg, thread_id=thread_id)
        logger.info(f"[digest] waiting for human approval in thread '{thread_id}' (reply 'approve' or 'reject').")

    async def _process_approval(self, thread_id: str, human_response: str):
        """Process human approval or rejection."""
        current_state = self.threads[thread_id]["current_state"]
        if not current_state:
            return

        current_state["human_response"] = human_response
        config = {"configurable": {"thread_id": thread_id}}

        result = self.graph.invoke(current_state, config=config)
        self.threads[thread_id]["awaiting_approval"] = False

        final_msg = result.get("final_message", "")
        await self.client.send(final_msg, thread_id=thread_id)
        logger.info(f"Outcome in thread '{thread_id}': {result.get('approval_status')}")


async def run_live(agent: DigestAgent):
    """Run live agent listening to Switch SSE stream."""
    logger.info(f"Starting Digest agent listening for room '{agent.client.room_name}' at {agent.client.server_url}")
    async for event in agent.client.listen():
        await agent.handle_event(event)


async def run_demo(agent: DigestAgent, bug_report_path: str):
    """Simulate complete 3-agent triage, repro, and digest flow locally."""
    print("=" * 65)
    print("  SIMULATING SWITCH BUG TRIAGE ROOM FLOW (DEMO)")
    print("=" * 65)

    if not os.path.exists(bug_report_path):
        print(f"Error: {bug_report_path} not found.")
        return

    with open(bug_report_path, "r", encoding="utf-8") as f:
        report_text = f.read().strip()

    report_basename = os.path.basename(bug_report_path)
    thread_id = f"thread-{report_basename.split('.')[0]}"

    # Step 1: Human posts report
    print(f"\n[Human]: {report_text}\n")

    # Step 2: Triager classifies and routes
    if "question" in report_basename or "question" in report_text.lower():
        triager_msg = (
            "Restatement: Inquiring about multi-user support and isolation in Mem-CLI.\n"
            "Classification: question\n"
            "Mem-CLI supports multi-user memory separation using the `-u <USER_ID>` parameter. "
            "Each user's memories are indexed by `user_id` in PostgreSQL with dedicated B-tree indexes, "
            "ensuring complete data isolation across team members and autonomous agents."
        )
        print(f"[triager]: {triager_msg}\n")
        print("[Notice]: Question resolved directly by triager. Repro and Digest not needed.")
        print("=" * 65)
        print("  DEMO RUN COMPLETED (NON-BUG PATH)")
        print("=" * 65)
        return

    if "02" in report_basename:
        triager_msg = (
            "Restatement: CSV export output creates double blank lines in spreadsheet viewers.\n"
            "Classification: bug\n"
            "@bug-repro please reproduce the CSV file export formatting issue."
        )
        repro_msg = (
            "I reproduced the issue in TARGET_REPO.\n"
            "Command: `memcli -u repro-bot export --format csv -o export_test.csv`\n"
            "Output inspection:\n"
            "```text\n"
            "File contains double carriage-return sequences (0x0D 0x0D 0x0A) on Windows.\n"
            "Opening in Excel displays empty interleaved rows between records.\n"
            "```\n"
            "The open() call in the export command does not specify newline='', causing Python's default text translator to double-escape CRLF.\n"
            "@digest please summarise and propose a fix."
        )
    else:
        triager_msg = (
            "Restatement: Argument parsing error for -u option placed after subcommands.\n"
            "Classification: bug\n"
            "@bug-repro please reproduce the -u parameter failure with commands like `memcli list -u test`."
        )
        repro_msg = (
            "I reproduced the issue in TARGET_REPO.\n"
            "Command: `memcli list -u repro-bot`\n"
            "Output:\n"
            "```text\n"
            "usage: memcli [-h] [-u USER] {chat,list,search,remember,forget,export,clear} ...\n"
            "memcli: error: unrecognized arguments: -u repro-bot\n"
            "```\n"
            "The CLI parser does not recognize -u when placed after the subcommand.\n"
            "@digest please summarise and propose a fix."
        )

    print(f"[triager]: {triager_msg}\n")
    print(f"[repro]: {repro_msg}\n")

    # Populate thread history
    agent.threads[thread_id] = {
        "history": [
            {"author": "human", "content": report_text},
            {"author": "triager", "content": triager_msg},
            {"author": "repro", "content": repro_msg},
        ],
        "awaiting_approval": False,
        "current_state": None,
    }

    # Step 3: Digest agent processes and posts proposal
    print("[digest] Generating summary and diff fix from codebase...")
    initial_state: DigestState = {
        "room_history": agent.threads[thread_id]["history"],
        "thread_id": thread_id,
        "target_repo": agent.target_repo,
        "bug_summary": None,
        "repro_output": repro_msg,
        "suggested_patch": None,
        "summary_message": None,
        "human_response": None,
        "approval_status": None,
        "final_message": None,
        "revision_count": 0,
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.graph.invoke(initial_state, config=config)

    print("\n" + "-" * 55)
    print("[digest]:")
    print(result["summary_message"])
    print("-" * 55)

    # Step 4: Simulate human approval
    print("\n[Human]: approve\n")
    result["human_response"] = "approve"
    final_res = agent.graph.invoke(result, config=config)

    print("[digest]:")
    print(final_res["final_message"])
    print("=" * 65)
    print("  DEMO RUN COMPLETED SUCCESSFULLY")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Digest Agent for Bug Triage Room")
    parser.add_argument("--demo", action="store_true", help="Run local simulated triage room demo")
    parser.add_argument(
        "--report",
        default="switch/bug-reports/01-bug.md",
        help="Bug report path for demo mode (default: switch/bug-reports/01-bug.md)",
    )
    args = parser.parse_args()

    server_url = os.getenv("SWITCH_SERVER_URL", "http://localhost:3000")
    room_name = os.getenv("SWITCH_ROOM_NAME", "bug-triage")
    agent_name = os.getenv("SWITCH_AGENT_NAME", "digest")
    target_repo = os.getenv("TARGET_REPO", "E:/GenAI/Projects/Mem-CLI")

    client = SwitchClient(server_url=server_url, room_name=room_name, agent_name=agent_name)
    agent = DigestAgent(client=client, target_repo=target_repo)

    if args.demo:
        asyncio.run(run_demo(agent, args.report))
    else:
        asyncio.run(run_live(agent))


if __name__ == "__main__":
    main()
