"""
Tests for authentication endpoints.
"""

from fastapi.testclient import TestClient

from src.config import app_config


class TestAuth:
    """Test authentication endpoints."""

    def test_register_user(self, client: TestClient) -> None:
        """Test user registration returns user with ID."""
        # Given
        user_data: dict[str, str] = {
            "firstname": "John",
            "lastname": "Doe",
            "username": "johndoe",
            "email": "john.doe@example.com",
            "password": "password123",
        }
        auth_prefix = app_config.api_config.auth_prefix

        # When
        response = client.post(f"{auth_prefix}/register", json=user_data)

        # Then
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["id"] is not None
        assert data["id"] == 1
        assert data["username"] == "johndoe"
        assert "hashedPassword" not in data
