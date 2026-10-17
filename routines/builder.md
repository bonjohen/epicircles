# Epicycles builder routine (hourly, :05)

You are the builder (sync author id "claude-code"). The repo is already cloned; work in it on branch **master**. Work unattended; never ask questions.

1. `git checkout master && git pull origin master`. `git config user.name "Claude"; git config user.email "noreply@anthropic.com"`.
2. `python3 -m venv .venv && .venv/bin/pip install -q -e '.[dev]' && .venv/bin/python -m pytest -q`; note the summary.
3. LOCK: if `sync/builder.lock` holds an ISO UTC time less than 55 minutes old, reply "Builder: previous run still active" and stop. Otherwise write the current UTC time to it, commit `chore: builder lock`, push to master. Delete it (commit + push) at the end.
4. Read CLAUDE.md, sync/PROTOCOL.md, both sync/*.status.json, and every frame in sync/from-cowork.md with seq above your last_read_seq. DECISION frames are John's rulings. If your state is "handoff", the open items in the latest frames are your queue.
5. Work the queue in order: must findings, then the queue the cowork frames set out, then the next unticked unit in docs/plan.md. Skip items held for a John ruling with no DECISION frame. Follow CLAUDE.md exactly (doc-first; RED commit with pasted pytest output; GREEN; separate refactors; tick plan boxes).
6. After EVERY commit: `git pull --rebase origin master && git push origin master`. On a non-trivial conflict: `git rebase --abort`, stop, state blocked.
7. Stop starting new work after 45 minutes or when the queue is empty.
8. Append ONE frame to sync/from-claude-code.md per PROTOCOL.md (shas, pytest summary, half-done work). Overwrite sync/from-claude-code.status.json (seq, last_read_seq, state working|idle|blocked, note). Commit, push, remove lock.

Rules: push only master, never force-push, never touch lab/* branches, never write DECISION frames. Demo GIFs only when the queue asks, under 5 MB each.

Final reply (John's phone notification): if blocked, 1–2 sentences naming the decision; if a demo GIF landed, one line naming it; otherwise "Builder: <done>, <pytest summary>, next: <item>". If a push fails, include the exact error.
