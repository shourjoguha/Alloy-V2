#!/usr/bin/env python3
"""API Client Generator - Generate Python client from OpenAPI spec."""
import json
from pathlib import Path
from typing import Any


def generate_client() -> None:
    """Generate Python API client from OpenAPI specification."""
    
    client_code = '''"""
Alloy API Python Client

Generated API client for Alloy backend.
"""

import dataclasses
from typing import Any
from datetime import datetime
from enum import Enum

import httpx
from pydantic import BaseModel, Field


class ClientError(Exception):
    """Base exception for API client errors."""
    pass


class AuthenticationError(ClientError):
    """Authentication failed."""
    pass


class APIError(ClientError):
    """API returned an error."""
    def __init__(self, message: str, code: str | None = None, details: dict | None = None):
        self.code = code
        self.details = details
        super().__init__(message)


class APIResponse(BaseModel):
    """Standard API response wrapper."""
    data: Any | None = None
    meta: dict | None = None
    errors: list[dict] = Field(default_factory=list)


@dataclasses.dataclass
class AlloyClient:
    """Alloy API client."""
    
    base_url: str
    access_token: str | None = None
    refresh_token: str | None = None
    timeout: float = 30.0
    
    def __post_init__(self):
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
        )
    
    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    def _handle_response(self, response: httpx.Response) -> APIResponse:
        """Handle API response and raise errors if needed."""
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = response.text
        
        if response.status_code >= 400:
            error_data = data if isinstance(data, dict) else {}
            errors = error_data.get("errors", [])
            if errors:
                error = errors[0]
                raise APIError(
                    message=error.get("message", "API error"),
                    code=error.get("code"),
                    details=error.get("details")
                )
            raise APIError(message=response.reason_phrase)
        
        return APIResponse(**data)
    
    def _refresh_access_token(self) -> None:
        """Refresh access token using refresh token."""
        if not self.refresh_token:
            raise AuthenticationError("No refresh token available")
        
        response = self._client.post(
            "/auth/refresh",
            json={"refresh_token": self.refresh_token},
        )
        
        if response.status_code != 200:
            raise AuthenticationError("Failed to refresh token")
        
        data = response.json()
        self.access_token = data["data"]["access_token"]
    
    def login(self, email: str, password: str) -> None:
        """
        Authenticate and store tokens.
        
        Args:
            email: User email
            password: User password
        """
        response = self._client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        
        if response.status_code != 200:
            raise AuthenticationError("Login failed")
        
        data = response.json()["data"]
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
    
    def logout(self) -> None:
        """Clear stored tokens."""
        self.access_token = None
        self.refresh_token = None
    
    # Programs
    
    def create_program(self, program_data: dict) -> dict:
        """
        Create a new program.
        
        Args:
            program_data: Program creation data
            
        Returns:
            Created program data
        """
        response = self._client.post(
            "/programs",
            json=program_data,
            headers=self._get_headers(),
        )
        return self._handle_response(response).data
    
    def list_programs(
        self,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """
        List programs for current user.
        
        Args:
            is_active: Filter by active status
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of programs
        """
        params = {"limit": limit, "offset": offset}
        if is_active is not None:
            params["is_active"] = is_active
        
        response = self._client.get(
            "/programs",
            params=params,
            headers=self._get_headers(),
        )
        return self._handle_response(response).data
    
    def get_program(self, program_id: int) -> dict:
        """
        Get a specific program.
        
        Args:
            program_id: Program ID
            
        Returns:
            Program data
        """
        response = self._client.get(
            f"/programs/{program_id}",
            headers=self._get_headers(),
        )
        return self._handle_response(response).data
    
    def update_program(self, program_id: int, program_data: dict) -> dict:
        """
        Update a program.
        
        Args:
            program_id: Program ID
            program_data: Update data
            
        Returns:
            Updated program data
        """
        response = self._client.patch(
            f"/programs/{program_id}",
            json=program_data,
            headers=self._get_headers(),
        )
        return self._handle_response(response).data
    
    def delete_program(self, program_id: int) -> None:
        """
        Delete a program.
        
        Args:
            program_id: Program ID
        """
        response = self._client.delete(
            f"/programs/{program_id}",
            headers=self._get_headers(),
        )
        if response.status_code != 204:
            self._handle_response(response)
    
    # Settings
    
    def get_user_settings(self) -> dict:
        """Get current user settings."""
        response = self._client.get(
            "/settings/user",
            headers=self._get_headers(),
        )
        return self._handle_response(response).data
    
    def update_user_settings(self, settings_data: dict) -> dict:
        """
        Update user settings.
        
        Args:
            settings_data: Settings update data
            
        Returns:
            Updated settings
        """
        response = self._client.patch(
            "/settings/user",
            json=settings_data,
            headers=self._get_headers(),
        )
        return self._handle_response(response).data
    
    def list_movements(
        self,
        pattern: str | None = None,
        discipline: str | None = None,
        equipment: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """
        List movements with optional filtering.
        
        Args:
            pattern: Filter by movement pattern
            discipline: Filter by discipline
            equipment: Filter by equipment type
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of movements
        """
        params = {"limit": limit, "offset": offset}
        if pattern:
            params["pattern"] = pattern
        if discipline:
            params["discipline"] = discipline
        if equipment:
            params["equipment"] = equipment
        
        response = self._client.get(
            "/settings/movements",
            params=params,
            headers=self._get_headers(),
        )
        return self._handle_response(response).data
    
    def query_movements(self, query: dict) -> dict:
        """
        Advanced movement query.
        
        Args:
            query: Query object with filters, sort, pagination
            
        Returns:
            Query results
        """
        response = self._client.post(
            "/settings/movements/query",
            json=query,
            headers=self._get_headers(),
        )
        return self._handle_response(response).data
    
    # Circuits
    
    def list_circuits(
        self,
        circuit_type: str | None = None,
    ) -> list[dict]:
        """
        List circuit templates.
        
        Args:
            circuit_type: Filter by circuit type
            
        Returns:
            List of circuits
        """
        params = {}
        if circuit_type:
            params["circuit_type"] = circuit_type
        
        response = self._client.get(
            "/circuits",
            params=params,
        )
        return self._handle_response(response).data
    
    def get_circuit(self, circuit_id: int) -> dict:
        """
        Get a circuit template.
        
        Args:
            circuit_id: Circuit ID
            
        Returns:
            Circuit data
        """
        response = self._client.get(
            f"/circuits/{circuit_id}",
        )
        return self._handle_response(response).data
    
    # Health
    
    def health_check(self) -> dict:
        """
        Get system health status.
        
        Returns:
            Health status data
        """
        response = self._client.get("/health")
        return self._handle_response(response).data
    
    def database_health(self) -> dict:
        """
        Get database health status.
        
        Returns:
            Database health data
        """
        response = self._client.get("/health/database")
        return self._handle_response(response).data
    
    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Example usage
if __name__ == "__main__":
    # Create client
    client = AlloyClient(base_url="http://localhost:8000")
    
    # Login
    try:
        client.login(email="user@example.com", password="password")
        print("✓ Logged in successfully")
        
        # List programs
        programs = client.list_programs()
        print(f"✓ Found {len(programs.get('items', []))} programs")
        
        # Create a program
        program = client.create_program({
            "name": "Strength Program",
            "duration_weeks": 8,
            "goals": [
                {"goal_type": "strength", "weight": 5},
                {"goal_type": "muscle_gain", "weight": 3},
            ],
            "split_template": "push_pull_legs",
            "progression_style": "linear",
            "max_session_duration": 60,
            "persona": {
                "age_range": "25-34",
                "experience_level": "intermediate"
            }
        })
        print(f"✓ Created program: {program['name']} (ID: {program['id']})")
        
        # Get program
        program_detail = client.get_program(program["id"])
        print(f"✓ Retrieved program: {program_detail['name']}")
        
        # List movements
        movements = client.list_movements(pattern="squat")
        print(f"✓ Found {len(movements.get('items', []))} squat movements")
        
        # Health check
        health = client.health_check()
        print(f"✓ System status: {health['status']}")
        
    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e}")
    except APIError as e:
        print(f"✗ API error: {e.message} (code: {e.code})")
    finally:
        client.close()
'''
    
    output_path = Path(__file__).parent.parent / "client" / "alloy_api_client.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(client_code)
    print(f"✓ Generated API client at: {output_path}")


if __name__ == "__main__":
    generate_client()
