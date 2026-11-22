import os
import time
from pathlib import Path

from config import UserStore


def test_reload_and_invalid(tmp_path: Path):
    f = tmp_path / "u.yaml"
    f.write_text("users:\n  - id: a\n    name: A\n")
    s = UserStore(str(f))
    assert [u.id for u in s.all()] == ["a"]
    f.write_text("users:\n  - id: a\n  - id: b\n    name: Bea\n")
    os.utime(f, (time.time() + 5, time.time() + 5))
    assert [(u.id, u.name) for u in s.all()] == [("a", "a"), ("b", "Bea")]
    f.write_text("users:\n  - id: 'Bad Id'\n")
    os.utime(f, (time.time() + 10, time.time() + 10))
    assert [u.id for u in s.all()] == ["a", "b"]  # letzter gültiger Stand


def test_missing_file(tmp_path: Path):
    assert UserStore(str(tmp_path / "nope.yaml")).all() == []
