import base64

from fastapi.testclient import TestClient
from starlette.testclient import TestClient


def test_protected_endpoint_success(test_app: TestClient, basic_auth_credentials):
    username, password = basic_auth_credentials
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    headers = {"Authorization": f"Basic {encoded_credentials}"}
    response = test_app.get("/health", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health(test_app, basic_auth_header):
    response = test_app.get("/health", headers=basic_auth_header)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
