"""Export selected Fourier coefficients as deterministic JSON.

Schema (FR-9)::

    {"N": int, "ordering": str, "terms": [{"k": int, "re": float, "im": float}, ...]}

``terms`` are in selection (drawing) order. Object keys are sorted; CPython's
``json`` encoder renders floats with ``float.__repr__`` (shortest round-trip),
so the output is byte-identical across runs on the same environment (NFR-1).
"""
from __future__ import annotations

import json

from epicycles.core.fourier import Spectrum


def to_json(
    spec_selected: Spectrum,
    n: int,
    mode: str,
    segments: list[dict] | None = None,
    background: list[int] | None = None,
) -> str:
    """Serialize a selected spectrum to the FR-9 JSON string.

    When ``segments`` (pen-down spans ``[{t0, t1, colour:[r,g,b]}]``) and/or
    ``background`` (``[r,g,b]``) are given, they are added under the ``segments``
    and ``background`` keys (U20). The ``N``/``ordering``/``terms`` keys are
    unchanged, so consumers that ignore the new keys still work.
    """
    terms = [
        {"k": int(k), "re": float(c.real), "im": float(c.imag)}
        for k, c in zip(spec_selected.k, spec_selected.c)
    ]
    payload: dict = {"N": int(n), "ordering": mode, "terms": terms}
    if segments is not None:
        payload["segments"] = [
            {
                "t0": float(s["t0"]),
                "t1": float(s["t1"]),
                "colour": [int(v) for v in s["colour"]],
            }
            for s in segments
        ]
    if background is not None:
        payload["background"] = [int(v) for v in background]
    return json.dumps(payload, sort_keys=True)
