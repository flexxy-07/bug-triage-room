# Assumptions and Technical Discoveries

This document records technical details, verified Switch schemas, and target repo analyses as required by the Build Specification.

---

## 1. Verified Target Issues in Mem-CLI (Target Repo)

### Bug 01: Subcommand Argument Parsing Rejects Postfixed `-u` / `--user`
- **Location:** `src/memcli/cli.py` (`main()`)
- **Underlying Cause:**
  `parser.add_argument("-u", "--user", ...)` is defined on the root `ArgumentParser` before `parser.add_subparsers(...)`. In Python's `argparse`, options on the parent parser are not automatically accepted after subcommands unless defined on a shared parent parser passed to each subparser (`parents=[parent_parser]`) or declared explicitly per subparser.
- **Observed Behavior:**
  Running `memcli list -u repro-bot` or `memcli clear -u repro-bot --confirm` causes `argparse` to error out:
  `memcli: error: unrecognized arguments: -u repro-bot`
  Currently, users are forced to write `memcli -u repro-bot list`.
- **Expected Behavior:**
  Users should be able to pass `-u` either before or after subcommands (`memcli list -u repro-bot` or `memcli -u repro-bot list`).

### Bug 02: Windows CSV Export Double Carriage Return (`\r\r\n`)
- **Location:** `src/memcli/cli.py` (export handler, lines 298-301)
- **Underlying Cause:**
  When generating CSV output, `csv.DictWriter(io.StringIO(), ...)` generates CRLF (`\r\n`) line terminators. When writing to a file using `with open(args.output, "w", encoding="utf-8") as f: f.write(output_content)`, Python on Windows translates `\n` to `\r\n` by default, turning `\r\n` into `\r\r\n` (byte sequence `0x0D 0x0D 0x0A`).
- **Observed Behavior:**
  Files created with `memcli -u repro-bot export --format csv -o memories.csv` have double line breaks and empty rows when opened in Excel or CSV readers.
- **Expected Behavior:**
  Opening the output file with `newline=""` or specifying `lineterminator="\n"` in `DictWriter` prevents duplicate carriage return translation.

### Report 03: Non-Bug User Query
- Tests the non-bug classification path. `@triager` answers directly that Mem-CLI isolates users via the `-u <user_id>` parameter and `user_id` index in PostgreSQL, without invoking `@repro`.

---

## 2. Switch Agent Protocol Discoveries & Schema

- **Template Schema:**
  Verified against `sandbox-quantum/switch` (`examples/agent-templates/triage-pair.template.yaml`):
  - Root fields: `version: 1`, `params:`, `agents:`, `room:`, `kickoff:`.
  - Agents specify `name`, `description`, `addressing`, `provider`, `location`, `directory`, `instructions`.
  - Rooms specify `name`, `bridge`, `agents`, `users: ["{$creator}"]`.
- **Switch Agent Protocol Wire Endpoints:**
  - SSE real-time stream: `GET /gateway/rooms/{room_id}/events` or `GET /api/rooms/{room_id}/events` (with `Accept: text/event-stream`).
  - Outgoing message dispatch: `POST /gateway/rooms/{room_id}/messages` or `POST /api/rooms/{room_id}/messages` (with JSON body `{"content": text, "thread_id": thread_id}`).
  - Mention semantics: Agents act on `@agent_name` mentions in the room or thread.
- **Provider & Model:**
  - OpenCode / Gemini models: `gemini-3.5-flash-lite` or current active Flash models in Google AI Studio.
