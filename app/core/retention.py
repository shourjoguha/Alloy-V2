"""Log retention and archival policies."""
import asyncio
import gzip
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.config.settings import get_settings

settings = get_settings()


class LogType(BaseModel):
    """Log type configuration."""

    name: str
    path: str
    retention_days: int = Field(default=30, ge=1, le=365, description="Retention period in days")
    archive_after_days: int = Field(default=7, ge=1, le=180, description="Archive after N days")
    max_size_mb: int = Field(default=500, ge=10, le=10000, description="Max size before rotation in MB")
    compress_archives: bool = Field(default=True, description="Compress archived logs")


class RetentionConfig(BaseModel):
    """Complete retention configuration."""

    logs: list[LogType] = Field(default_factory=list)
    archive_directory: str = Field(default="./logs/archive")
    cleanup_schedule: str = Field(default="0 2 * * *", description="Cron expression for cleanup")
    enabled: bool = Field(default=True)


class LogRotator:
    """Handles log rotation and cleanup."""

    def __init__(self, config: RetentionConfig):
        self.config = config
        self._rotation_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start scheduled cleanup tasks."""
        if self._rotation_task is None:
            self._rotation_task = asyncio.create_task(self._rotation_loop())

    async def stop(self) -> None:
        """Stop scheduled cleanup tasks."""
        if self._rotation_task:
            self._rotation_task.cancel()
            self._rotation_task = None

    async def _rotation_loop(self) -> None:
        """Continuous rotation loop."""
        while True:
            try:
                await self._perform_cleanup()
            except Exception as e:
                print(f"Log cleanup error: {e}")
            await asyncio.sleep(3600)

    async def _perform_cleanup(self) -> None:
        """Perform cleanup for all configured logs."""
        for log_type in self.config.logs:
            await self._rotate_log(log_type)
            await self._archive_old_logs(log_type)
            await self._delete_expired_logs(log_type)

    async def _rotate_log(self, log_type: LogType) -> None:
        """Rotate log file if it exceeds max size."""
        log_path = Path(log_type.path)

        if not log_path.exists():
            return

        file_size_mb = log_path.stat().st_size / (1024 * 1024)

        if file_size_mb >= log_type.max_size_mb:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_name = f"{log_path.stem}_{timestamp}{log_path.suffix}"
            rotated_path = log_path.parent / rotated_name

            log_path.rename(rotated_path)
            print(f"Rotated log: {log_path.name} -> {rotated_name}")

    async def _archive_old_logs(self, log_type: LogType) -> None:
        """Archive old log files."""
        log_dir = Path(log_type.path).parent
        archive_dir = Path(self.config.archive_directory) / log_type.name
        archive_dir.mkdir(parents=True, exist_ok=True)

        cutoff_date = datetime.now() - timedelta(days=log_type.archive_after_days)

        for log_file in log_dir.glob(f"{log_path.name}.*"):
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    archive_path = archive_dir / log_file.name

                    if log_type.compress_archives and not archive_path.suffix == ".gz":
                        with open(log_file, "rb") as f_in:
                            with gzip.open(archive_path.with_suffix(".gz"), "wb") as f_out:
                                f_out.writelines(f_in)
                        log_file.unlink()
                    else:
                        log_file.rename(archive_path)

                    print(f"Archived: {log_file.name}")
            except Exception as e:
                print(f"Failed to archive {log_file.name}: {e}")

    async def _delete_expired_logs(self, log_type: LogType) -> None:
        """Delete expired log files."""
        archive_dir = Path(self.config.archive_directory) / log_type.name

        if not archive_dir.exists():
            return

        cutoff_date = datetime.now() - timedelta(days=log_type.retention_days)

        for log_file in archive_dir.glob("*"):
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    log_file.unlink()
                    print(f"Deleted expired log: {log_file.name}")
            except Exception as e:
                print(f"Failed to delete {log_file.name}: {e}")

    def get_retention_status(self) -> dict[str, Any]:
        """Get current retention status."""
        status = {
            "last_cleanup": self._last_cleanup_time.isoformat() if hasattr(self, "_last_cleanup_time") else "never",
            "logs": [],
        }

        for log_type in self.config.logs:
            log_path = Path(log_type.path)
            archive_dir = Path(self.config.archive_directory) / log_type.name

            log_info = {
                "name": log_type.name,
                "path": str(log_path),
                "exists": log_path.exists(),
                "size_mb": log_path.stat().st_size / (1024 * 1024) if log_path.exists() else 0,
                "retention_days": log_type.retention_days,
                "archive_count": len(list(archive_dir.glob("*"))) if archive_dir.exists() else 0,
            }

            status["logs"].append(log_info)

        return status


_global_rotator: LogRotator | None = None


def get_rotator() -> LogRotator:
    """Get global log rotator instance."""
    global _global_rotator
    if _global_rotator is None:
        config = RetentionConfig(
            logs=[
                LogType(
                    name="application",
                    path="logs/app.log",
                    retention_days=30,
                    archive_after_days=7,
                    max_size_mb=500,
                    compress_archives=True,
                ),
                LogType(
                    name="audit",
                    path="logs/audit.log",
                    retention_days=90,
                    archive_after_days=30,
                    max_size_mb=1000,
                    compress_archives=True,
                ),
                LogType(
                    name="error",
                    path="logs/error.log",
                    retention_days=180,
                    archive_after_days=14,
                    max_size_mb=250,
                    compress_archives=True,
                ),
            ],
            archive_directory="logs/archive",
            cleanup_schedule="0 2 * * *",
            enabled=settings.log_retention_enabled,
        )
        _global_rotator = LogRotator(config)
    return _global_rotator


async def start_retention() -> None:
    """Start log retention system."""
    rotator = get_rotator()
    await rotator.start()


async def stop_retention() -> None:
    """Stop log retention system."""
    rotator = get_rotator()
    await rotator.stop()


def get_retention_status() -> dict[str, Any]:
    """Get current retention status."""
    rotator = get_rotator()
    return rotator.get_retention_status()
