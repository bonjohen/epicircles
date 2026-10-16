# CLAUDE.md — epicycles

Fourier-epicycle line drawing: input (SVG / line-art raster / photo) → single closed path → DFT → animated chain of rotating vectors.

## Read first
- `docs/requirements.md` — what and acceptance criteria (normative: MUST/SHOULD)
- `docs/design.md` — module contracts, math, data types
- `docs/plan.md` — phased work units; do units in order

## Workflow (non-negotiable)
For every work unit in `docs/plan.md`:
1. **Doc first.** If the unit changes a contract, update `docs/design.md` (and requirements if scope changes) before any code. Commit: `docs(<unit>): ...`.
2. **RED.** Write the tests listed for the unit. Run `pytest -q`. They must fail for the right reason: a failed assertion, or an `ImportError`/`AttributeError` for the symbol under test (pytest may report this as a collection error; that is valid RED). Syntax errors or broken imports of anything else are not RED. Paste the failing summary into the commit body. Commit: `test(<unit>): RED ...`.
3. **GREEN.** Minimal implementation to pass. No speculative features. Commit: `feat(<unit>): GREEN ...`.
4. **Refactor** only with tests green. Commit separately.
5. Tick the unit's checkbox in `docs/plan.md`.

Do not modify a test to make it pass unless the doc changed first and the commit says why.

## Rules
- Python 3.11+. Runtime deps: `numpy`, `pillow`, `scikit-image`, `svgpathtools`, `matplotlib`. Dev: `pytest`, `hypothesis`. Add nothing else without updating `docs/design.md#dependencies`.
- Deterministic: no unseeded randomness; ties broken by index; same input + same environment → byte-identical coefficient file. Hypothesis runs under a `derandomize=True` profile registered in `tests/conftest.py`.
- Tests never hit the network. Web fetch is tested with monkeypatched `urllib`.
- Test geometry and data, not pixels. Renderer tests assert on chain positions / frame counts, never PNG bytes.
- Pure functions in `core/`, I/O only in `io/` and `cli.py`.
- Type hints everywhere; complex paths are `np.ndarray[complex128]` shape `(N,)`.
- Recursion: no recursive graph/pixel traversal; use explicit stacks (real skeletons exceed Python's recursion limit).
- Commands: `pytest -q`, `python -m epicycles --help`.
- Coordination: a reviewer posts notes in `docs/handoff.md`. Read it at session start; when you finish a phase, append a dated status entry there.

## Commit Message Format (relaxed — overrides global)

commit-format: relaxed

This is a personal project. It **overrides** the global `~/.claude/CLAUDE.md`
"Commit Message Format" rule: the structured `What changed:` / `Why:` /
`What we learned:` body is **optional**, not required, including for `feat:`
commits. The `commit-format: relaxed` token above is read by the global
`check-commit-msg.py` hook, which then skips its structured-section nag for
commits made in this repo.

Convention for this repo:
- Single-line conventional-commit subjects with the TDD unit prefix are the
  norm: `docs(<unit>): ...`, `test(<unit>): RED ...`, `feat(<unit>): GREEN ...`,
  `refactor(<unit>): ...`.
- Add a short body only when the change isn't self-explanatory (e.g. paste the
  failing `pytest` summary into a `test(...): RED` commit, as the workflow
  above requires).
- Keep the global trailer: `Co-Authored-By: Claude 5.5 <noreply@anthropic.com>`.
