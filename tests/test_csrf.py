from fastapi.testclient import TestClient

from app.main import app


def test_mutating_requests_require_session_csrf_token():
    client = TestClient(app)
    page = client.get("/")

    assert page.status_code == 200
    token = client.get("/auth/csrf").json()["csrf_token"]

    rejected = client.post("/auth/logout")
    accepted = client.post(
        "/auth/logout",
        headers={"X-CSRF-Token": token}
    )

    assert rejected.status_code == 403
    assert accepted.status_code == 200
