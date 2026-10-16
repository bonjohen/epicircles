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


def to_json(spec_selected: Spectrum, n: int, mode: str) -> str:
    """Serialize a selected spectrum to the FR-9 JSON string."""
    terms = [
        {"k": int(k), "re": float(c.real), "im": float(c.imag)}
        for k, c in zip(spec_selected.k, spec_selected.c)
    ]
    payload = {"N": int(n), "ordering": mode, "terms": terms}
    return json.dumps(payload, sort_keys=True)
