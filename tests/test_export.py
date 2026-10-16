"""U5: coefficient export to JSON.

Contracts in docs/design.md#io/export.py and FR-9:
  to_json(spec_selected, n, mode) -> str; schema {N, ordering, terms:[{k,re,im}]};
  keys sorted; terms in selection order; byte-identical across runs (NFR-1);
  round-trips to the same evaluate() output.
"""
import json

import numpy as np

from epicycles.core.fourier import Spectrum, evaluate, select, spectrum
from epicycles.io.export import to_json


def _selected(n: int = 16, m: int = 5) -> Spectrum:
    j = np.arange(n)
    z = (
        (1 - 1j)
        + 2.0 * np.exp(2j * np.pi * j / n)
        + 0.7 * np.exp(-4j * np.pi * j / n)
    )
    return select(spectrum(z), m, "magnitude")


def test_schema_keys():
    spec = _selected()
    obj = json.loads(to_json(spec, 16, "magnitude"))
    assert set(obj) == {"N", "ordering", "terms"}
    assert obj["N"] == 16
    assert obj["ordering"] == "magnitude"
    assert len(obj["terms"]) == len(spec.k)
    for term in obj["terms"]:
        assert set(term) == {"k", "re", "im"}


def test_deterministic_bytes():
    spec = _selected()
    assert to_json(spec, 16, "magnitude") == to_json(spec, 16, "magnitude")


def test_terms_in_selection_order():
    spec = _selected()
    obj = json.loads(to_json(spec, 16, "magnitude"))
    assert [t["k"] for t in obj["terms"]] == [int(x) for x in spec.k]


def test_roundtrip_reconstructs_evaluate():
    spec = _selected()
    obj = json.loads(to_json(spec, 16, "magnitude"))
    k = np.array([t["k"] for t in obj["terms"]], dtype=np.int64)
    c = np.array(
        [t["re"] + 1j * t["im"] for t in obj["terms"]], dtype=np.complex128
    )
    t = np.linspace(0, 1, 50, endpoint=False)
    assert np.allclose(evaluate(Spectrum(k, c), t), evaluate(spec, t), atol=1e-12)
