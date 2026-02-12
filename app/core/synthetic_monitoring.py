"""Synthetic monitoring for critical user journeys."""
import asyncio
from datetime import datetime
from typing import Any

import httpx

from app.config.settings import get_settings

settings = get_settings()


class SyntheticTransaction(BaseModel):
    """Configuration for a synthetic transaction."""

    name: str
    description: str
    enabled: bool = True
    check_interval_seconds: int = Field(default=60, ge=10, le=3600)
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    max_retries: int = Field(default=3, ge=1, le=10)


class TransactionResult(BaseModel):
    """Result of a synthetic transaction."""

    name: str
    status: str
    duration_ms: float
    error: str | None = None
    checked_at: datetime
    success: bool = Field(alias="is_success")


class SyntheticMonitor:
    """Manages synthetic monitoring checks."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=30.0)
        self._monitor_tasks: dict[str, asyncio.Task] = {}
        self._results: dict[str, list[TransactionResult]] = []

    async def start(self) -> None:
        """Start all enabled monitors."""
        transactions = self._get_transactions()

        for transaction in transactions:
            if transaction.enabled:
                task = asyncio.create_task(self._monitor_transaction(transaction))
                self._monitor_tasks[transaction.name] = task

    async def stop(self) -> None:
        """Stop all monitors."""
        for task in self._monitor_tasks.values():
            task.cancel()
        self._monitor_tasks.clear()

    async def _monitor_transaction(self, transaction: SyntheticTransaction) -> None:
        """Monitor a single transaction."""
        while True:
            try:
                result = await self._run_transaction(transaction)
                self._store_result(transaction.name, result)

                if not result.success:
                    await self._on_transaction_failure(transaction, result)
            except Exception as e:
                error_result = TransactionResult(
                    name=transaction.name,
                    status="error",
                    duration_ms=0,
                    error=str(e),
                    checked_at=datetime.utcnow(),
                    is_success=False,
                )
                self._store_result(transaction.name, error_result)
                await self._on_transaction_failure(transaction, error_result)

            await asyncio.sleep(transaction.check_interval_seconds)

    async def _run_transaction(self, transaction: SyntheticTransaction) -> TransactionResult:
        """Execute a synthetic transaction."""
        start_time = datetime.utcnow()

        try:
            if transaction.name == "health_check":
                return await self._check_health()
            elif transaction.name == "user_login":
                return await self._check_login()
            elif transaction.name == "create_program":
                return await self._check_create_program()
            elif transaction.name == "list_movements":
                return await self._check_list_movements()
            elif transaction.name == "get_program":
                return await self._check_get_program()
            else:
                return TransactionResult(
                    name=transaction.name,
                    status="unknown",
                    duration_ms=0,
                    error="Unknown transaction type",
                    checked_at=start_time,
                    is_success=False,
                )
        except httpx.TimeoutException:
            return TransactionResult(
                name=transaction.name,
                status="timeout",
                duration_ms=transaction.timeout_seconds * 1000,
                error="Request timeout",
                checked_at=start_time,
                is_success=False,
            )
        except httpx.HTTPStatusError as e:
            return TransactionResult(
                name=transaction.name,
                status="http_error",
                duration_ms=0,
                error=f"HTTP {e.response.status_code}",
                checked_at=start_time,
                is_success=False,
            )
        except Exception as e:
            return TransactionResult(
                name=transaction.name,
                status="error",
                duration_ms=0,
                error=str(e),
                checked_at=start_time,
                is_success=False,
            )

    async def _check_health(self) -> TransactionResult:
        """Check health endpoint."""
        start = datetime.utcnow()
        response = await self._client.get(f"{self.base_url}/health")
        duration = (datetime.utcnow() - start).total_seconds() * 1000

        return TransactionResult(
            name="health_check",
            status="success" if response.status_code == 200 else "failed",
            duration_ms=duration,
            error=None if response.status_code == 200 else f"Status: {response.status_code}",
            checked_at=start,
            is_success=response.status_code == 200,
        )

    async def _check_login(self) -> TransactionResult:
        """Check login transaction."""
        start = datetime.utcnow()
        response = await self._client.post(
            f"{self.base_url}/auth/login",
            json={"email": settings.synthetic_monitor_user, "password": settings.synthetic_monitor_password},
        )
        duration = (datetime.utcnow() - start).total_seconds() * 1000

        success = response.status_code == 200 and "access_token" in response.json().get("data", {})

        return TransactionResult(
            name="user_login",
            status="success" if success else "failed",
            duration_ms=duration,
            error=None if success else "Login failed or token missing",
            checked_at=start,
            is_success=success,
        )

    async def _check_create_program(self) -> TransactionResult:
        """Check create program transaction."""
        start = datetime.utcnow()
        response = await self._client.post(
            f"{self.base_url}/programs",
            json={
                "name": "Synthetic Test Program",
                "duration_weeks": 8,
                "goals": [{"goal_type": "strength", "weight": 5}],
                "split_template": "push_pull_legs",
                "progression_style": "linear",
                "max_session_duration": 60,
                "persona": {"age_range": "25-34", "experience_level": "intermediate"},
            },
            headers=self._get_auth_header(),
        )
        duration = (datetime.utcnow() - start).total_seconds() * 1000

        success = response.status_code == 201

        return TransactionResult(
            name="create_program",
            status="success" if success else "failed",
            duration_ms=duration,
            error=None if success else f"Status: {response.status_code}",
            checked_at=start,
            is_success=success,
        )

    async def _check_list_movements(self) -> TransactionResult:
        """Check list movements transaction."""
        start = datetime.utcnow()
        response = await self._client.get(
            f"{self.base_url}/settings/movements",
            headers=self._get_auth_header(),
        )
        duration = (datetime.utcnow() - start).total_seconds() * 1000

        success = response.status_code == 200

        return TransactionResult(
            name="list_movements",
            status="success" if success else "failed",
            duration_ms=duration,
            error=None if success else f"Status: {response.status_code}",
            checked_at=start,
            is_success=success,
        )

    async def _check_get_program(self) -> TransactionResult:
        """Check get program transaction."""
        start = datetime.utcnow()
        response = await self._client.get(
            f"{self.base_url}/programs/1",
            headers=self._get_auth_header(),
        )
        duration = (datetime.utcnow() - start).total_seconds() * 1000

        success = response.status_code == 200 or response.status_code == 404

        return TransactionResult(
            name="get_program",
            status="success" if success else "failed",
            duration_ms=duration,
            error=None if success else f"Status: {response.status_code}",
            checked_at=start,
            is_success=success,
        )

    def _get_auth_header(self) -> dict[str, str]:
        """Get authentication header."""
        return {"Authorization": f"Bearer {settings.synthetic_monitor_token}"}

    def _store_result(self, name: str, result: TransactionResult) -> None:
        """Store transaction result."""
        if name not in self._results:
            self._results[name] = []
        self._results[name].append(result)

        if len(self._results[name]) > 1000:
            self._results[name] = self._results[name][-1000:]

    async def _on_transaction_failure(self, transaction: SyntheticTransaction, result: TransactionResult) -> None:
        """Handle transaction failure."""
        print(f"⚠️ Synthetic transaction failed: {transaction.name}")
        print(f"   Error: {result.error}")
        print(f"   Duration: {result.duration_ms:.0f}ms")

    def get_results(self) -> dict[str, list[TransactionResult]]:
        """Get all transaction results."""
        return self._results

    def get_summary(self) -> dict[str, Any]:
        """Get monitoring summary."""
        summary = {
            "transactions": [],
            "overall_health": "unknown",
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
        }

        for name, results in self._results.items():
            if not results:
                continue

            recent_results = results[-10:] if len(results) > 10 else results
            success_rate = sum(1 for r in recent_results if r.success) / len(recent_results)
            avg_duration = sum(r.duration_ms for r in recent_results) / len(recent_results)

            summary["transactions"].append(
                {
                    "name": name,
                    "success_rate": f"{success_rate * 100:.1f}%",
                    "avg_duration_ms": round(avg_duration, 2),
                    "last_status": recent_results[-1].status,
                    "last_checked": recent_results[-1].checked_at.isoformat(),
                }
            )

            summary["total_checks"] += len(recent_results)
            summary["successful_checks"] += sum(1 for r in recent_results if r.success)
            summary["failed_checks"] += sum(1 for r in recent_results if not r.success)

        if summary["total_checks"] > 0:
            overall_rate = summary["successful_checks"] / summary["total_checks"]
            if overall_rate >= 0.95:
                summary["overall_health"] = "healthy"
            elif overall_rate >= 0.8:
                summary["overall_health"] = "degraded"
            else:
                summary["overall_health"] = "unhealthy"

        return summary

    def _get_transactions(self) -> list[SyntheticTransaction]:
        """Get configured transactions."""
        return [
            SyntheticTransaction(
                name="health_check",
                description="Health check endpoint",
                enabled=True,
                check_interval_seconds=30,
            ),
            SyntheticTransaction(
                name="user_login",
                description="User login flow",
                enabled=settings.synthetic_monitor_token is not None,
                check_interval_seconds=60,
            ),
            SyntheticTransaction(
                name="create_program",
                description="Create training program",
                enabled=settings.synthetic_monitor_token is not None,
                check_interval_seconds=120,
            ),
            SyntheticTransaction(
                name="list_movements",
                description="List movements",
                enabled=settings.synthetic_monitor_token is not None,
                check_interval_seconds=60,
            ),
            SyntheticTransaction(
                name="get_program",
                description="Get program details",
                enabled=settings.synthetic_monitor_token is not None,
                check_interval_seconds=60,
            ),
        ]


_global_monitor: SyntheticMonitor | None = None


def get_monitor() -> SyntheticMonitor:
    """Get global synthetic monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SyntheticMonitor(base_url=settings.api_base_url or "http://localhost:8000")
    return _global_monitor


async def start_synthetic_monitoring() -> None:
    """Start synthetic monitoring."""
    monitor = get_monitor()
    await monitor.start()


async def stop_synthetic_monitoring() -> None:
    """Stop synthetic monitoring."""
    monitor = get_monitor()
    await monitor.stop()


def get_synthetic_status() -> dict[str, Any]:
    """Get synthetic monitoring status."""
    monitor = get_monitor()
    return monitor.get_summary()
