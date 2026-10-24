"""
Test setup: the API runs against a temporary copy of resource/database.db, so tests never change real data.
Run from the backend folder:  .venv/Scripts/python -m pytest tests -q
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR / "app"))

_tmp_dir = Path(tempfile.mkdtemp(prefix="agentverse-test-"))
_db_copy = _tmp_dir / "database.db"
shutil.copy(BACKEND_DIR / "resource" / "database.db", _db_copy)
# Environment variables win over backend/.env, so this must happen before the app is imported
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_copy.as_posix()}"


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from main import app

    # Not used as a context manager: the lifespan (handbook embedding warm-up) is not needed here
    yield TestClient(app)


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_tmp_dir, ignore_errors=True)
