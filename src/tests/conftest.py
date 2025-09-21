import base64
import os

import pytest
from starlette.testclient import TestClient

from app.server import app


@pytest.fixture(scope="module")
def test_app():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def basic_auth_credentials():
    """Loads basic authentication credentials from the .env file."""
    username = os.getenv("BASIC_AUTH_USERNAME")
    password = os.getenv("BASIC_AUTH_PASSWORD")
    if not username or not password:
        raise ValueError("BASIC_AUTH_USERNAME or BASIC_AUTH_PASSWORD not found in .env file.")
    return username, password


@pytest.fixture(scope="module")
def basic_auth_header(basic_auth_credentials):
    """Creates a basic authentication header"""
    username, password = basic_auth_credentials
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    headers = {"Authorization": f"Basic {encoded_credentials}"}
    return headers
