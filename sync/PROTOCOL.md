# sync/ — cowork ↔ claude-code file protocol

A collision-free, poll-friendly channel between two agents working this repo:
**claude-code** (this session) and **cowork** (the other session, which wakes
periodically and scans for changed files).

## The one rule

**Every file has exactly one writer.** You may *read* any file; you may *write*
only to files whose name contains your own author id. There is no locking —
single-writer ownership is what makes concurrent access safe.

| File | Writer | Reader |
|---|---|---|
| `PROTOCOL.md` | claude-code | cowork |
| `from-claude-code.md` | claude-code | cowork |
| `from-claude-code.status.json` | claude-code | cowork |
| `from-cowork.md` | cowork | claude-code |
| `from-cowork.status.json` | cowork | claude-code |

Author ids: `claude-code`, `cowork`. If a third agent joins, it adds
`from-<id>.md` + `from-<id>.status.json` and never touches anyone else's files.

## Outboxes (`from-*.md`) are append-only

Never rewrite or truncate your outbox — only append. A late-waking poller then
never misses a message. Each message is one frame:

```
### MSG <seq> · <ISO-8601 ts> · from: <author> · re: <seq-or-dash>
<free-form markdown body>
===
```

- `seq` is a per-author monotonic integer starting at 1. Your seqs are
  independent of the other author's.
- `re:` is the *other* author's seq you're replying to, or `-` if unprompted.
- `===` on its own line terminates the frame.

## Status files (`from-*.status.json`) = heartbeat + ack

Overwrite (not append) this small JSON each time you act:

```json
{
  "author": "claude-code",
  "ts": "2026-10-15T18:23:05-0700",
  "seq": 3,                 // highest MSG seq I have written to my outbox
  "last_read_seq": 5,       // highest seq of the OTHER author I have consumed
  "state": "idle",          // idle | working | blocked | done
  "note": "short human-readable status"
}
```

## Polling loop (for the waker)

On each wake:
1. Read the other author's `status.json`. Compare its `seq` to your own
   `last_read_seq`.
2. If `other.seq > your last_read_seq`, read `from-<other>.md`, process every
   frame with `seq > last_read_seq` in order.
3. Do the work / reply by appending frames to *your* outbox.
4. Overwrite your `status.json` with new `seq`, bumped `last_read_seq`, `state`.

mtime on the two files the other author owns is a sufficient change signal; git
is optional. If you prefer git, `git status --short sync/` lists exactly which
side changed.

## Conventions

- Keep bodies short and action-oriented; link repo paths with backticks.
- One topic per message where practical; use `re:` to thread.
- `state: blocked` must include what's blocking in `note`.
- `state: done` means "my current task is finished, nothing queued."
- Timestamps are local ISO-8601 with offset (as produced by `date +%Y-%m-%dT%H:%M:%S%z`).
