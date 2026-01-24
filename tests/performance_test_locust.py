"""
Performance testing for ShowMeGains backend using Locust.

Tests concurrent request handling, database performance, and system stability
under various load conditions (load, stress, spike, duration).

Run with:
    locust -f tests/performance_test_locust.py --host=http://localhost:8000

Or for headless mode with specific load:
    locust -f tests/performance_test_locust.py --host=http://localhost:8000 \\
        --users=50 --spawn-rate=5 --run-time=5m --headless
"""

import random
from locust import HttpUser, task, between
from datetime import date, timedelta


class ShowMeGainsUser(HttpUser):
    """
    Simulated user performing typical ShowMeGains workflows.
    
    Task distribution:
    - Daily plan requests: 20% (lightweight queries)
    - Adaptation requests: 15% (includes LLM calls, slower)
    - Workout logging: 15% (set/rep recording)
    - Deload checks: 10% (recovery assessment)
    - Program creation: 5% (heavier compute)
    - Idle/think time: 35% (user delays)
    """
    
    # Think time between requests (realistic user behavior)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize test data on user startup."""
        # Create a program for this user (simulated with hardcoded default_user_id=1)
        self.program_id = self._create_test_program()
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)
    
    def _create_test_program(self) -> int:
        """Create a test program and return its ID."""
        try:
            response = self.client.post(
                "/api/programs",
                json={
                    "name": f"Performance Test Program {random.randint(1000, 9999)}",
                    "goal_1": "strength",
                    "goal_2": "hypertrophy",
                    "goal_3": "endurance",
                    "goal_weight_1": 50,
                    "goal_weight_2": 40,
                    "goal_weight_3": 10,
                    "split_template": "upper_lower",
                    "progression_style": "linear",
                    "duration_weeks": 8,
                    "deload_every_n_microcycles": 4,
                },
                catch_response=True,
            )
            if response.status_code == 201:
                return response.json()["id"]
            else:
                print(f"Failed to create program: {response.status_code}")
                return 1  # Fallback to program 1
        except Exception as e:
            print(f"Error creating test program: {e}")
            return 1
    
    @task(20)
    def get_daily_plan(self):
        """Get daily plan for today.
        
        Simulates user checking what they need to do today.
        Fast operation - mainly database read.
        """
        with self.client.get(
            f"/api/days/{self.today}/plan?program_id={self.program_id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(15)
    def request_adaptation(self):
        """Request session adaptation with recovery signals.
        
        Simulates user asking for a personalized workout adjustment.
        Slower operation - includes LLM call.
        """
        # Vary recovery signals for realistic scenarios
        recovery = {
            "sleep_quality": random.choice(["poor", "fair", "good", "excellent"]),
            "sleep_hours": random.uniform(5, 10),
            "energy_level": random.randint(1, 10),
            "stress_level": random.randint(1, 10),
        }
        
        # Sometimes include soreness
        soreness = []
        if random.random() > 0.6:
            soreness = [
                {"body_part": "knee", "level": random.randint(1, 5)},
                {"body_part": "shoulder", "level": random.randint(1, 5)},
            ]
        
        with self.client.post(
            f"/api/days/{self.today}/adapt",
            json={
                "program_id": self.program_id,
                "recovery": recovery,
                "soreness": soreness,
                "adherence_vs_optimality": random.choice(["adherence", "optimality", "balanced"]),
                "time_available_minutes": random.choice([30, 45, 60, 90]),
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Adaptation failed: {response.status_code}")
    
    @task(15)
    def log_workout(self):
        """Log a completed workout session.
        
        Simulates user recording their exercise performance.
        Medium operation - database writes + e1RM calculation.
        """
        movements = [
            {"movement_name": "squat", "sets": 5, "reps": 5, "weight_lbs": 300},
            {"movement_name": "bench_press", "sets": 4, "reps": 8, "weight_lbs": 225},
            {"movement_name": "deadlift", "sets": 3, "reps": 3, "weight_lbs": 405},
            {"movement_name": "leg_press", "sets": 3, "reps": 12, "weight_lbs": 500},
            {"movement_name": "pull_ups", "sets": 4, "reps": 8, "weight_lbs": 0},
        ]
        
        with self.client.post(
            "/api/logs/workout",
            json={
                "session_date": str(self.yesterday),
                "session_type": "upper",
                "movements": random.sample(movements, random.randint(2, 4)),
                "duration_minutes": random.randint(30, 90),
                "difficulty_1_5": random.randint(1, 5),
            },
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"Workout log failed: {response.status_code}")
    
    @task(10)
    def check_deload_status(self):
        """Check if deload is recommended.
        
        Simulates user monitoring recovery status.
        Fast operation - aggregate recovery data.
        """
        with self.client.get(
            f"/api/days/{self.today}/plan?program_id={self.program_id}",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # If coach_message mentions deload, that's the signal
                if data.get("coach_message") and "deload" in data["coach_message"].lower():
                    pass  # Deload recommended
            else:
                response.failure(f"Deload check failed: {response.status_code}")
    
    @task(5)
    def get_program_info(self):
        """Retrieve program details.
        
        Simulates user reviewing their program structure.
        Medium operation - database reads with relationships.
        """
        with self.client.get(
            f"/api/programs/{self.program_id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Program retrieval failed: {response.status_code}")


class StressTestUser(ShowMeGainsUser):
    """
    Stress test user with aggressive load.
    
    Higher frequency requests, less think time, focus on heavy endpoints.
    """
    
    wait_time = between(0.5, 1.5)  # Shorter think time
    
    @task(30)  # Increased weight for adaptation (heavier computation)
    def request_adaptation(self):
        """Override parent to increase load on adaptation endpoint."""
        super().request_adaptation()


if __name__ == "__main__":
    # This file is meant to be run with locust CLI:
    # locust -f tests/performance_test_locust.py --host=http://localhost:8000
    print("Run with: locust -f tests/performance_test_locust.py --host=http://localhost:8000")
