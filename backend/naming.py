"""Titel-Säuberung und Dateinamen (ADR 0008)."""
from __future__ import annotations

import re
from datetime import datetime

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_FORBIDDEN = re.compile(r'[/\\:*?"<>|]')
_EXT = re.compile(r"^[a-z0-9]{1,5}$")


def clean_title(title: str) -> str:
    t = _CONTROL.sub("", re.sub(r"\s", " ", title))
    t = re.sub(r" +", " ", _FORBIDDEN.sub(" ", t)).strip()[:100]
    return t.rstrip(". ").strip()


def file_name(ts: datetime, index: int, original: str | None) -> str:
    ext = "jpg"
    if original and "." in original:
        cand = original.rsplit(".", 1)[1].lower()
        if _EXT.match(cand):
            ext = "jpg" if cand == "jpeg" else cand
    return f"{ts:%Y%m%d-%H%M%S}_{index:02d}.{ext}"


def join(base: str, *parts: str) -> str:
    """Pfad im Cloudspeicher, immer mit führendem / und ohne doppelte /."""
    segs = [s for p in (base, *parts) for s in p.split("/") if s]
    return "/" + "/".join(segs)
