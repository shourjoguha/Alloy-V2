"""Load testing configuration using Locust."""
import random
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from locust import HttpUser, between, events, task
from locust.runners import MasterRunner


class AlloyUser(HttpUser):
    """Simulated user for load testing."""
    
    wait_time = between(1, 5)
    test_program_id = None
    test_circuit_id = 1
    
    def on_start(self):
        """Called when a user starts."""
        self.login()
    
    def on_stop(self):
        """Called when a user stops."""
        self.logout()
    
    @task(3)
    def health_check(self):
        """Health check endpoint."""
        self.client.get("/health", name="Health Check")
    
    @task(5)
    def list_circuits(self):
        """List circuits endpoint."""
        with self.client.get("/circuits", name="List Circuits", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(10)
    def list_movements(self):
        """List movements endpoint (requires auth)."""
        if not self.access_token:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.get(
            "/settings/movements",
            headers=headers,
            name="List Movements",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(7)
    def list_programs(self):
        """List programs endpoint (requires auth)."""
        if not self.access_token:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.get(
            "/programs",
            headers=headers,
            name="List Programs",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
                
                # Extract first program ID for other tasks
                data = response.json()
                if data and "data" in data:
                    programs = data["data"].get("items", [])
                    if programs and programs[0].get("id"):
                        self.test_program_id = programs[0]["id"]
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(3)
    def get_program(self):
        """Get program endpoint (requires auth)."""
        if not self.access_token or not self.test_program_id:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.get(
            f"/programs/{self.test_program_id}",
            headers=headers,
            name="Get Program",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # Program might not exist, not a failure
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(2)
    def get_programs_stats(self):
        """Get program stats endpoint (requires auth)."""
        if not self.access_token:
            return
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.get(
            "/programs/stats",
            headers=headers,
            name="Get Programs Stats",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in (401, 403):
                response.success()  # Auth failure, not an API error
            else:
                response.failure(f"Status code: {response.status_code}")
    
    def login(self):
        """Authenticate user and store access token."""
        email = self.environment.runner.user_email if hasattr(self.environment.runner, "user_email") else "test@example.com"
        password = self.environment.runner.user_password if hasattr(self.environment.runner, "user_password") else "test_password"
        
        response = self.client.post(
            "/auth/login",
            json={"email": email, "password": password},
            name="Login",
            catch_response=True,
        )
        
        if response.status_code == 200:
            response.success()
            data = response.json()
            self.access_token = data.get("data", {}).get("access_token")
        else:
            response.failure(f"Login failed: {response.status_code}")
            self.access_token = None
    
    def logout(self):
        """Clear access token."""
        self.access_token = None


class StressTestUser(AlloyUser):
    """High-intensity user for stress testing."""
    
    wait_time = between(0.1, 1)  # Much faster
    
    @task(10)
    def rapid_health_checks(self):
        """Rapid health checks."""
        self.health_check()
    
    @task(15)
    def rapid_list_circuits(self):
        """Rapid circuit listing."""
        self.list_circuits()


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print(f"\n{'='*60}")
    print(f"Load test starting at {datetime.now().isoformat()}")
    print(f"Target: {environment.host}")
    print(f"{'='*60}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print(f"\n{'='*60}")
    print(f"Load test completed at {datetime.now().isoformat()}")
    print(f"{'='*60}\n")
    
    if isinstance(environment.runner, MasterRunner):
        print("Test run by master. Check worker logs for detailed results.")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Called after each request."""
    if exception:
        print(f"❌ Request failed: {name} - {exception}")
    elif response_time > 5000:
        print(f"⚠️  Slow request: {name} - {response_time:.0f}ms")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║                     Alloy Load Testing Suite                       ║
╚════════════════════════════════════════════════════════════════╝

Run with:
  locust -f tests/load_test/locustfile.py

Options:
  -H, --host            Target host (default: http://localhost:8000)
  -u, --users           Number of users to spawn
  -r, --spawn-rate      Users spawned per second
  -t, --run-time        Stop after the specified time
  --headless             Run without UI
  --csv                  Save stats to CSV files
  --html                 Generate HTML report

Examples:
  # Run with web UI
  locust -f tests/load_test/locustfile.py -H http://localhost:8000

  # Headless mode with 100 users
  locust -f tests/load_test/locustfile.py -H http://localhost:8000 --headless -u 100 -r 10 -t 5m

  # Generate HTML report
  locust -f tests/load_test/locustfile.py -H http://localhost:8000 --headless -u 50 -r 5 -t 3m --html report.html
""")
