import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="snapdrop-test-"))
    (d / "users.yaml").write_text("users:\n  - id: anna\n    name: Anna\n  - id: bob\n    name: Bob\n")
    os.environ.update({
        "SECRET_KEY": Fernet.generate_key().decode(),
        "SNAPDROP_DB": str(d / "test.db"),
        "USERS_FILE": str(d / "users.yaml"),
        "DROPBOX_APP_KEY": "key", "DROPBOX_APP_SECRET": "secret",
        "PUBLIC_URL": "https://snap.test",
    })
    os.environ["SNAPDROP_TESTDIR"] = str(d)
