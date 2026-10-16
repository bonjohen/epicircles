"""U19 (P5): browser renderer page.

A static HTML page that consumes the FR-9 coeffs.json. pytest checks structure
and that the page reads exactly the exporter's schema (rendering itself is a
manual browser check — the offline suite does not run a browser).
"""
import json
from pathlib import Path

from epicycles.cli import run_svg_pipeline
from epicycles.io.export import to_json

WEB = Path(__file__).resolve().parent.parent / "web" / "index.html"
FIX = Path(__file__).parent / "fixtures"


def test_browser_page_exists_with_canvas_and_slider():
    assert WEB.exists()
    html = WEB.read_text(encoding="utf-8")
    assert "<canvas" in html
    assert 'type="range"' in html  # the M slider
    assert "coeffs.json" in html  # loads the exported coefficients


def test_browser_page_reads_export_fields():
    html = WEB.read_text(encoding="utf-8")
    # The page consumes the FR-9 fields (JS destructures {k, re, im}).
    assert "spec.terms" in html
    assert "{ k, re, im }" in html
    assert "spec.ordering" in html or "ordering" in html
    assert "spec.N" in html


def test_exporter_schema_matches_page_contract():
    res = run_svg_pipeline(str(FIX / "circle.svg"), "auto", 8, "magnitude")
    obj = json.loads(to_json(res.kept, res.n, res.order))
    assert set(obj) == {"N", "ordering", "terms"}
    assert set(obj["terms"][0]) == {"k", "re", "im"}
