# Assumptions and Switch Protocol Notes

This document records assumptions and discoveries about Switch, its Agent Protocol, and open questions encountered during development.

---

## 1. Switch Agent Protocol

- **Protocol Overview**: Agents connect to Switch rooms using SSE (Server-Sent Events) for incoming messages/events and standard HTTP POST requests for outgoing messages.
- **Server Endpoint**: Default Switch server runs locally (via Switch Console Docker stack) or at `SWITCH_SERVER_URL` (typically `http://localhost:3000` or `http://localhost:8000`).
- **SSE Stream**: Room event stream URL is typically `GET /api/rooms/{room_id}/events` or `GET /v1/rooms/{room_id}/sse`.
- **Message Send**: Outgoing messages posted to `POST /api/rooms/{room_id}/messages` or `POST /v1/messages`.
- **Mention Convention**: Switch agents listen to the room log and act when their name is explicitly mentioned (e.g. `@digest`).

---

## 2. Agent Template Schema

- Switch agent templates (`triage-room.template.yaml`) define rooms, participants, providers, and kickoff messages.
- Console manages local containers (Mattermost, Postgres, agent runner) and CLI agents (e.g. OpenCode).

---

## 3. Target Repo: Mem-CLI

- Target repository: `https://github.com/flexxy-07/Mem-CLI`.
- Uses PostgreSQL 17 with `pgvector` (`halfvec(3072)`), running on port 5433 to avoid standard port 5432 clashes.
- Repro agent runs only against throwaway namespace `repro-bot` and scripts are placed in `TARGET_REPO/repro/`.
