import pytest
from fastapi.testclient import TestClient

from app.models import User
from app.services import auth_service

def test_2fa_pre_auth_token_cannot_access_protected_endpoints(client: TestClient):
    """
    Verifies that a temporary 'pre_auth_token' issued for 2FA verification
    cannot be used to access other protected API endpoints.
    """
    # 1. Register a new user
    user_data = {"username": "testuser_2fa", "password": "testpassword"}
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201, "Failed to register user"

    # 2. Log in normally to get a standard access token to enable 2FA
    login_data = {"username": user_data["username"], "password": user_data["password"]}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200, "Failed to log in"
    login_json = response.json()
    assert "access_token" in login_json, "Initial login should provide a standard access token"
    access_token = login_json["access_token"]

    # 3. Enable 2FA for the user
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/auth/2fa/setup", headers=headers)
    assert response.status_code == 200, "Failed to enable 2FA"

    # 4. Log in again. This time, because 2FA is enabled, we should get a pre_auth_token
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    login_2fa_json = response.json()
    assert "pre_auth_token" in login_2fa_json, "Login with 2FA enabled should return a pre_auth_token"
    assert login_2fa_json.get("2fa_required") is True, "2FA should be marked as required"
    pre_auth_token = login_2fa_json["pre_auth_token"]

    # 5. Attempt to use the pre_auth_token to access a protected endpoint
    # This is the core of the test. This request should be denied.
    pre_auth_headers = {"Authorization": f"Bearer {pre_auth_token}"}
    response = client.post("/auth/2fa/setup", headers=pre_auth_headers)

    # 6. Assert that the request was unauthorized
    # Before the fix, this would have returned 200 OK. After the fix, it must be 401.
    assert response.status_code == 401, \
        "A pre_auth_token should not be valid for accessing protected endpoints."

    assert response.json()["detail"] == "Could not validate credentials"