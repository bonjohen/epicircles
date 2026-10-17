"""U20b / FR-14: SVG stroke colour, group inheritance, fallback to default ink."""
from __future__ import annotations

from epicycles.io.svg import load_svg, load_svg_coloured

HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
INK = (0, 0, 0)


def _svg(tmp_path, body):
    p = tmp_path / "t.svg"
    p.write_text(HEAD + body + "</svg>")
    return p


def test_stroke_attribute_hex(tmp_path):
    p = _svg(tmp_path, '<path d="M10 10 L90 10" stroke="#00f"/>')
    strokes, colours = load_svg_coloured(p, 64)
    assert len(strokes) == 1 and colours == [(0, 0, 255)]


def test_style_wins_over_attribute_and_forms(tmp_path):
    p = _svg(
        tmp_path,
        '<path d="M10 10 L90 10" stroke="#00f" style="fill:none;stroke:#ff8000"/>'
        '<path d="M10 30 L90 30" stroke="rgb(10, 20, 30)"/>'
        '<path d="M10 50 L90 50" stroke="red"/>'
        '<path d="M10 70 L90 70" stroke="#123456"/>',
    )
    _, colours = load_svg_coloured(p, 64)
    assert colours == [(255, 128, 0), (10, 20, 30), (255, 0, 0), (0x12, 0x34, 0x56)]


def test_group_inheritance_nearest_wins(tmp_path):
    p = _svg(
        tmp_path,
        '<g stroke="green"><g><path d="M10 10 L90 10"/></g>'
        '<path d="M10 30 L90 30" stroke="#f00"/></g>',
    )
    _, colours = load_svg_coloured(p, 64)
    assert sorted(colours) == sorted([(0, 128, 0), (255, 0, 0)])


def test_none_missing_and_unparseable_fall_back_to_ink(tmp_path):
    p = _svg(
        tmp_path,
        '<path d="M10 10 L90 10"/>'
        '<path d="M10 30 L90 30" stroke="none"/>'
        '<path d="M10 50 L90 50" stroke="url(#g)"/>'
        '<path d="M10 70 L90 70" stroke="currentColor"/>',
    )
    _, colours = load_svg_coloured(p, 64)
    assert colours == [INK] * 4


def test_subpaths_inherit_and_load_svg_unchanged(tmp_path):
    p = _svg(tmp_path, '<path d="M10 10 L90 10 M10 50 L90 50" stroke="#0f0"/>')
    strokes, colours = load_svg_coloured(p, 64)
    assert len(strokes) == 2 and colours == [(0, 255, 0)] * 2
    plain = load_svg(p, 64)
    assert len(plain) == 2 and all((a == b).all() for a, b in zip(plain, strokes))
