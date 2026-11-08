"""Main entrypoint for Digest agent."""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path if running directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from switch_client import SwitchClient
from graph import create_digest_graph

load_dotenv()


async def main():
    print("[digest] Starting Digest agent...")
    server_url = os.getenv("SWITCH_SERVER_URL", "http://localhost:3000")
    room_name = os.getenv("SWITCH_ROOM_NAME", "bug-triage")
    client = SwitchClient(server_url=server_url, room_name=room_name)
    print(f"[digest] Configured for room '{room_name}' at {server_url}")


if __name__ == "__main__":
    asyncio.run(main())
