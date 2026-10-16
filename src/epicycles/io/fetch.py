"""Fetch a source file, caching remote downloads by URL hash.

A local path is returned unchanged. A URL is downloaded once (no retries) with
a User-Agent header — Wikimedia rejects requests without one — and cached at
``cache_dir/sha256(url)[:16] + ext``. The extension comes from the URL path, or
from the response Content-Type when the path has none.
"""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

_USER_AGENT = "epicycles/0.1 (https://github.com/epicycles; line-drawing tool)"
_CONTENT_TYPE_EXT = {
    "image/svg+xml": ".svg",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}


def _is_url(src: str) -> bool:
    return urlsplit(src).scheme in ("http", "https")


def fetch(src: str, cache_dir: Path) -> Path:
    """Return a local path for ``src``, downloading and caching if it is a URL."""
    if not _is_url(src):
        return Path(src)

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(src.encode()).hexdigest()[:16]

    # Second call: a cached file digest.* already exists -> no network.
    cached = sorted(cache_dir.glob(digest + ".*"))
    if cached:
        return cached[0]

    url_ext = Path(urlsplit(src).path).suffix
    request = urllib.request.Request(src, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request) as response:
        data = response.read()
        if url_ext:
            ext = url_ext
        else:
            ctype = response.headers.get_content_type()
            ext = _CONTENT_TYPE_EXT.get(ctype)
            if ext is None:
                raise ValueError(f"cannot determine extension for Content-Type {ctype!r}")

    dest = cache_dir / (digest + ext)
    dest.write_bytes(data)
    return dest
