import os
import tempfile
from pathlib import Path

import pytest


TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="RoutineIA_pytest_"))
os.environ.setdefault("ROUTINE_IA_DATA_DIR", str(TEST_DATA_DIR))
os.environ.setdefault("ROUTINE_IA_OPEN_BROWSER", "0")


@pytest.fixture()
def flask_app():
    from app import create_app

    app = create_app(enable_runtime=False)
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()
