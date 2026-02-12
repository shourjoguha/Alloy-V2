"""Alerting system for error rates and performance metrics."""
import asyncio
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

import httpx
from pydantic import BaseModel, Field, HttpUrl

from app.config.settings import get_settings
from app.core.metrics import (
    error_requests_total,
    http_requests_total,
    db_queries_total,
)

settings = get_settings()


class AlertThreshold(BaseModel):
    """Configuration for alert thresholds."""

    error_rate_warning: float = Field(default=1.0, ge=0, le=100, description="Error rate % for warning")
    error_rate_critical: float = Field(default=5.0, ge=0, le=100, description="Error rate % for critical")
    latency_p95_warning: float = Field(default=500.0, ge=0, description="P95 latency ms for warning")
    latency_p95_critical: float = Field(default=2000.0, ge=0, description="P95 latency ms for critical")
    check_interval_seconds: int = Field(default=60, ge=10, le=3600, description="Check interval in seconds")


class AlertConfig(BaseModel):
    """Complete alerting configuration."""

    enabled: bool = Field(default=True)
    thresholds: AlertThreshold = Field(default_factory=AlertThreshold)
    notification_channels: list[str] = Field(default_factory=lambda: ["email"])
    cooldown_minutes: int = Field(default=15, ge=1, description="Cooldown between alerts")


class NotificationConfig(BaseModel):
    """Configuration for notification channels."""

    email_enabled: bool = Field(default=True)
    smtp_server: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_username: str | None = Field(default=None)
    smtp_password: str | None = Field(default=None)
    email_from: str | None = Field(default=None)
    email_to: list[str] = Field(default_factory=list)

    slack_enabled: bool = Field(default=False)
    slack_webhook_url: HttpUrl | None = Field(default=None)

    webhook_enabled: bool = Field(default=False)
    webhook_url: HttpUrl | None = Field(default=None)


class Alert(BaseModel):
    """Alert data model."""

    id: str
    severity: str
    title: str
    message: str
    metric_name: str
    current_value: float
    threshold: float
    triggered_at: datetime
    resolved_at: datetime | None = None


class AlertManager:
    """Manages alert checking and notifications."""

    def __init__(self, config: AlertConfig):
        self.config = config
        self.notification_config = NotificationConfig()
        self._active_alerts: dict[str, Alert] = {}
        self._last_check_time: datetime | None = None
        self._check_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start alert monitoring task."""
        if self._check_task is None:
            self._check_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop alert monitoring task."""
        if self._check_task:
            self._check_task.cancel()
            self._check_task = None

    async def _monitor_loop(self) -> None:
        """Continuous monitoring loop."""
        while True:
            try:
                await self._check_alerts()
                self._last_check_time = datetime.utcnow()
            except Exception as e:
                print(f"Alert monitoring error: {e}")
            await asyncio.sleep(self.config.thresholds.check_interval_seconds)

    async def _check_alerts(self) -> None:
        """Check all configured alerts."""
        await asyncio.gather(
            self._check_error_rate(),
            self._check_latency(),
            self._check_database_errors(),
        )

    async def _check_error_rate(self) -> None:
        """Check error rate threshold."""
        total_requests = self._get_metric_total(http_requests_total)
        error_requests = self._get_metric_total(error_requests_total)

        if total_requests == 0:
            return

        error_rate = (error_requests / total_requests) * 100

        if error_rate >= self.config.thresholds.error_rate_critical:
            await self._trigger_alert(
                severity="critical",
                title="Critical Error Rate",
                message=f"Error rate is {error_rate:.2f}%, exceeding critical threshold of {self.config.thresholds.error_rate_critical}%",
                metric_name="error_rate",
                current_value=error_rate,
                threshold=self.config.thresholds.error_rate_critical,
            )
        elif error_rate >= self.config.thresholds.error_rate_warning:
            await self._trigger_alert(
                severity="warning",
                title="High Error Rate",
                message=f"Error rate is {error_rate:.2f}%, exceeding warning threshold of {self.config.thresholds.error_rate_warning}%",
                metric_name="error_rate",
                current_value=error_rate,
                threshold=self.config.thresholds.error_rate_warning,
            )

    async def _check_latency(self) -> None:
        """Check latency thresholds."""
        pass

    async def _check_database_errors(self) -> None:
        """Check database error thresholds."""
        pass

    def _get_metric_total(self, metric: Any) -> float:
        """Get total value from Prometheus metric."""
        try:
            return float(sum(metric._samples.values()))
        except Exception:
            return 0.0

    async def _trigger_alert(
        self,
        severity: str,
        title: str,
        message: str,
        metric_name: str,
        current_value: float,
        threshold: float,
    ) -> None:
        """Trigger an alert if cooldown has passed."""
        alert_id = f"{severity}_{metric_name}_{current_value:.2f}"

        if alert_id in self._active_alerts:
            last_alert = self._active_alerts[alert_id]
            cooldown_expiry = last_alert.triggered_at + timedelta(minutes=self.config.cooldown_minutes)
            if datetime.utcnow() < cooldown_expiry:
                return

        alert = Alert(
            id=alert_id,
            severity=severity,
            title=title,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            triggered_at=datetime.utcnow(),
        )

        self._active_alerts[alert_id] = alert

        await self._send_notification(alert)

    async def _send_notification(self, alert: Alert) -> None:
        """Send notification via configured channels."""
        tasks = []

        if "email" in self.config.notification_channels and self.notification_config.email_enabled:
            tasks.append(self._send_email_notification(alert))

        if "slack" in self.config.notification_channels and self.notification_config.slack_enabled:
            tasks.append(self._send_slack_notification(alert))

        if "webhook" in self.config.notification_channels and self.notification_config.webhook_enabled:
            tasks.append(self._send_webhook_notification(alert))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_email_notification(self, alert: Alert) -> None:
        """Send email notification."""
        if not all(
            [
                self.notification_config.smtp_username,
                self.notification_config.smtp_password,
                self.notification_config.email_from,
                self.notification_config.email_to,
            ]
        ):
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{alert.severity.upper()}] {alert.title}"
        msg["From"] = self.notification_config.email_from
        msg["To"] = ", ".join(self.notification_config.email_to)

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .alert-box {{ border-left: 4px solid; padding: 15px; margin: 20px 0; }}
                .critical {{ border-color: #dc3545; background-color: #f8d7da; }}
                .warning {{ border-color: #ffc107; background-color: #fff3cd; }}
                .info {{ border-color: #17a2b8; background-color: #d1ecf1a; }}
                .metric {{ font-size: 1.2em; font-weight: bold; color: #333; }}
                .timestamp {{ color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="alert-box {alert.severity}">
                <h2>{alert.title}</h2>
                <p>{alert.message}</p>
                <div class="metric">Current: {alert.current_value:.2f} / Threshold: {alert.threshold:.2f}</div>
                <div class="timestamp">Triggered at: {alert.triggered_at.isoformat()}</div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(
                self.notification_config.smtp_server,
                self.notification_config.smtp_port,
            ) as server:
                server.starttls()
                server.login(
                    self.notification_config.smtp_username,
                    self.notification_config.smtp_password,
                )
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email notification: {e}")

    async def _send_slack_notification(self, alert: Alert) -> None:
        """Send Slack notification."""
        if not self.notification_config.slack_webhook_url:
            return

        emoji = "🚨" if alert.severity == "critical" else "⚠️"

        payload = {
            "text": f"{emoji} *{alert.title}*",
            "attachments": [
                {
                    "color": "danger" if alert.severity == "critical" else "warning",
                    "fields": [
                        {"title": "Severity", "value": alert.severity.upper(), "short": True},
                        {
                            "title": "Metric",
                            "value": alert.metric_name,
                            "short": True,
                        },
                        {
                            "title": "Current Value",
                            "value": f"{alert.current_value:.2f}",
                            "short": True,
                        },
                        {
                            "title": "Threshold",
                            "value": f"{alert.threshold:.2f}",
                            "short": True,
                        },
                        {"title": "Time", "value": alert.triggered_at.isoformat(), "short": True},
                    ],
                    "text": alert.message,
                }
            ],
        }

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    str(self.notification_config.slack_webhook_url),
                    json=payload,
                    timeout=10.0,
                )
        except Exception as e:
            print(f"Failed to send Slack notification: {e}")

    async def _send_webhook_notification(self, alert: Alert) -> None:
        """Send webhook notification."""
        if not self.notification_config.webhook_url:
            return

        payload = {
            "alert_id": alert.id,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "metric_name": alert.metric_name,
            "current_value": alert.current_value,
            "threshold": alert.threshold,
            "triggered_at": alert.triggered_at.isoformat(),
        }

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    str(self.notification_config.webhook_url),
                    json=payload,
                    timeout=10.0,
                )
        except Exception as e:
            print(f"Failed to send webhook notification: {e}")

    def get_active_alerts(self) -> list[Alert]:
        """Get all currently active alerts."""
        return list(self._active_alerts.values())

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        if alert_id in self._active_alerts:
            self._active_alerts[alert_id].resolved_at = datetime.utcnow()
            return True
        return False


_global_alert_manager: AlertManager | None = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance."""
    global _global_alert_manager
    if _global_alert_manager is None:
        config = AlertConfig(enabled=settings.alerting_enabled)
        _global_alert_manager = AlertManager(config)
    return _global_alert_manager


async def start_alerting() -> None:
    """Start alerting system."""
    manager = get_alert_manager()
    await manager.start()


async def stop_alerting() -> None:
    """Stop alerting system."""
    manager = get_alert_manager()
    await manager.stop()
