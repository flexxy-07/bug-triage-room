"""Switch Agent Protocol Client.

Handles Server-Sent Events (SSE) streaming and HTTP message posting
for communicating with Switch rooms and agents.
"""
import asyncio
import json
import logging
from typing import AsyncIterator, Optional, Dict, Any
import httpx
from httpx_sse import aconnect_sse

logger = logging.getLogger("switch_client")


class SwitchEvent:
    """Represents a message or event from a Switch room."""

    def __init__(
        self,
        event_type: str,
        content: str,
        author: str,
        thread_id: Optional[str] = None,
        raw: Optional[Dict[str, Any]] = None,
    ):
        self.event_type = event_type
        self.content = content
        self.author = author
        self.thread_id = thread_id
        self.raw = raw or {}

    def is_mention(self, agent_name: str) -> bool:
        """Check if message explicitly addresses this agent."""
        target = f"@{agent_name.lower()}"
        return target in self.content.lower()

    def __repr__(self) -> str:
        return f"<SwitchEvent author={self.author} type={self.event_type} thread={self.thread_id}>"


class SwitchClient:
    """Client for Switch Agent Protocol (SSE in, HTTP POST out)."""

    def __init__(
        self,
        server_url: str = "http://localhost:3000",
        room_name: str = "bug-triage",
        agent_name: str = "digest",
        agent_token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.server_url = server_url.rstrip("/")
        self.room_name = room_name
        self.agent_name = agent_name
        self.agent_token = agent_token
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.agent_token:
            self.headers["Authorization"] = f"Bearer {self.agent_token}"

    def _get_stream_urls(self) -> list[str]:
        """Candidate SSE streaming endpoints supported across Switch versions."""
        return [
            f"{self.server_url}/gateway/rooms/{self.room_name}/events",
            f"{self.server_url}/api/rooms/{self.room_name}/events",
            f"{self.server_url}/rooms/{self.room_name}/events",
            f"{self.server_url}/room/events?room={self.room_name}",
        ]

    def _get_post_urls(self) -> list[str]:
        """Candidate POST message endpoints supported across Switch versions."""
        return [
            f"{self.server_url}/gateway/rooms/{self.room_name}/messages",
            f"{self.server_url}/api/rooms/{self.room_name}/messages",
            f"{self.server_url}/rooms/{self.room_name}/messages",
            f"{self.server_url}/messages",
        ]

    async def listen(self) -> AsyncIterator[SwitchEvent]:
        """Listen to room events over Server-Sent Events (SSE) with reconnect backoff."""
        stream_urls = self._get_stream_urls()
        backoff = 2.0
        max_backoff = 30.0

        while True:
            connected = False
            for url in stream_urls:
                try:
                    logger.info(f"Connecting to Switch SSE stream at {url}...")
                    async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, read=None)) as client:
                        async with aconnect_sse(client, "GET", url, headers=self.headers) as event_source:
                            logger.info(f"Successfully connected to Switch SSE stream at {url}")
                            connected = True
                            backoff = 2.0  # Reset backoff on successful connection

                            async for sse in event_source.aiter_sse():
                                event = self._parse_sse(sse)
                                if event:
                                    # Ignore the agent's own messages to prevent loops
                                    if event.author.lower() == self.agent_name.lower():
                                        continue
                                    yield event

                except (httpx.ConnectError, httpx.HTTPStatusError, httpx.ReadTimeout) as err:
                    logger.debug(f"Could not connect to {url}: {err}")
                    continue
                except Exception as ex:
                    logger.warning(f"SSE stream error on {url}: {ex}")
                    break

            if not connected:
                logger.info(f"Switch server not reachable. Retrying in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, max_backoff)

    def _parse_sse(self, sse) -> Optional[SwitchEvent]:
        """Parse raw SSE frame into a SwitchEvent."""
        try:
            data = json.loads(sse.data) if sse.data else {}
        except Exception:
            data = {"content": sse.data}

        event_type = sse.event or data.get("type", "message")
        content = data.get("content") or data.get("message") or data.get("text", "")
        author = data.get("author") or data.get("sender") or data.get("user", "")
        thread_id = data.get("thread_id") or data.get("threadId") or data.get("id")

        if not content and not data:
            return None

        return SwitchEvent(
            event_type=event_type,
            content=str(content),
            author=str(author),
            thread_id=str(thread_id) if thread_id else None,
            raw=data,
        )

    async def send(self, text: str, thread_id: Optional[str] = None) -> bool:
        """Send message to the Switch room or thread."""
        payload = {
            "content": text,
            "sender": self.agent_name,
            "room": self.room_name,
        }
        if thread_id:
            payload["thread_id"] = thread_id

        post_urls = self._get_post_urls()
        for url in post_urls:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload, headers=self.headers)
                    if resp.is_success:
                        logger.info(f"Message sent to {url} (thread={thread_id})")
                        return True
            except Exception as e:
                logger.debug(f"Failed sending message to {url}: {e}")
                continue

        logger.error("Failed to post message to any Switch endpoint.")
        return False
