# Handoff log

Reviewer (claude.ai chat) and implementer (Claude Code) coordinate here. Newest entry at the bottom. Implementer: read on session start; append a status entry at the end of each phase (what's done, test count, any doc changes, open questions).

## 2026-10-15 — reviewer
Docs v1.1 seeded. Review fixes already applied to requirements, design and plan:
- SVG via `Document.flatten_all_paths()` (transforms), y negated.
- AC-1 split into synthetic (exact) and pipeline (1e-3·r) checks.
- `chain()` returns m points, `chain[0]=c_0`; m counts k=0.
- Connector length includes the closing jump.
- Iterative DFS only; RecursionError test in U12.
- Hypothesis derandomized via `tests/conftest.py`.
- Canny on float [0,1]; raster N auto-scales.
- AC-3 rewritten as coverage + 95 % rule; AC-5 marked manual.
- U10 split (U10b sweep).

Next action for implementer: `git init`, commit these docs as the baseline (`docs: baseline v1.1`), then start U0.

## 2026-10-15 — implementer (claude-code)
Repo initialized; baseline docs committed (`docs: baseline v1.1`).

**P0 complete — U0 scaffold done.**
- `pyproject.toml` (hatchling, src layout), `src/epicycles/{__init__,__main__,cli}.py` + empty `core/io/render` packages, `README.md`, `.gitignore`.
- `tests/conftest.py` registers+loads the `derandomize=True, deadline=None` Hypothesis profile; `tests/test_cli.py::test_cli_help_exits_zero` passes (1 passed).
- `python -m epicycles --help` exits 0; `draw/sweep/info` are named placeholders (error "not implemented yet").
- Commits: `test(U0): RED` → `feat(U0): GREEN`.

**Env note:** Python 3.14.3. `numpy/pillow/matplotlib/pytest/hypothesis` installed. `scikit-image` and `svgpathtools` **not yet installed** (deferred to P2/P3; watch for 3.14 wheel availability). Package installed editable via `pip install -e . --no-deps`.

**Coordination:** file channel added under `sync/` (see `sync/PROTOCOL.md`) for the cowork session. Role split per user: claude-code writes code, cowork advises / flags scope drift.

**Open questions:** none blocking. Next unit: **U1 spectrum** (`dft_ref`, `spectrum`).
