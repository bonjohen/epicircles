"""U6: fetch with caching (network is always monkeypatched).

Contract in docs/design.md#io/fetch.py:
  fetch(src, cache_dir) -> Path; local path passthrough; URL ->
  cache_dir/sha256(url)[:16]+ext downloaded once via urllib with a User-Agent;
  ext from URL path, else Content-Type (svg/png/jpeg); unknown type raises.
"""
import hashlib
import urllib.request
from email.message import Message
from pathlib import Path

import pytest

from epicycles.io.fetch import fetch


class _Resp:
    def __init__(self, data: bytes, ctype: str):
        self._data = data
        h = Message()
        h["Content-Type"] = ctype
        self.headers = h

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake(data=b"<svg/>", ctype="image/svg+xml", calls=None, captured=None):
    def _urlopen(req, *a, **k):
        if calls is not None:
            calls.append(1)
        if captured is not None:
            captured.append(req)
        return _Resp(data, ctype)

    return _urlopen


def test_local_path_passthrough(tmp_path):
    f = tmp_path / "a.svg"
    f.write_text("<svg/>")
    assert fetch(str(f), tmp_path / "cache") == Path(str(f))


def test_url_downloads_once_and_caches(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(urllib.request, "urlopen", _fake(calls=calls))
    url = "http://example.com/drawing.svg"
    cache = tmp_path / "c"
    p1 = fetch(url, cache)
    assert p1.read_bytes() == b"<svg/>"
    assert len(calls) == 1
    p2 = fetch(url, cache)
    assert p2 == p1
    assert len(calls) == 1  # second call hits the cache, no network


def test_cache_name_is_sha256_prefix_plus_ext(tmp_path, monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _fake())
    url = "http://example.com/a.svg"
    p = fetch(url, tmp_path)
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    assert p.name == digest + ".svg"


def test_extension_from_content_type_when_url_has_none(tmp_path, monkeypatch):
    monkeypatch.setattr(
        urllib.request, "urlopen", _fake(data=b"\x89PNG", ctype="image/png")
    )
    p = fetch("http://example.com/image", tmp_path)
    assert p.suffix == ".png"


def test_unknown_content_type_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        _fake(data=b"zzz", ctype="application/octet-stream"),
    )
    with pytest.raises(ValueError):
        fetch("http://example.com/thing", tmp_path)


def test_user_agent_sent(tmp_path, monkeypatch):
    captured = []
    monkeypatch.setattr(urllib.request, "urlopen", _fake(captured=captured))
    fetch("http://example.com/a.svg", tmp_path)
    assert captured[0].get_header("User-agent")
