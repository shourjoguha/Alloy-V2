"""Application configuration settings."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Coach ShowMeGains"
    debug: bool = True

    # Database - Primary (Write)
    database_url: str = "postgresql+asyncpg://gainsly:gainslypass@localhost:5433/gainslydb"

    # Database - Read Replicas (comma-separated list)
    read_replica_urls: str = ""

    # Read Replica Configuration
    read_replica_enabled: bool = False
    read_replica_pool_size: int = 10
    read_replica_max_overflow: int = 10
    read_replica_pool_timeout: int = 30
    read_replica_pool_recycle: int = 300
    read_replica_health_check_interval: int = 30  # seconds
    read_replica_health_check_timeout: float = 2.0  # seconds
    read_replica_max_failures: int = 3  # Mark replica unhealthy after N consecutive failures

    # Replica fallback behavior
    replica_fallback_to_primary: bool = True  # Fall back to primary if all replicas fail
    
    # OpenAI/LLM settings (used for daily adaptation only - session generation uses ML optimization)
    openai_api_key: str = ""  # Set via environment variable OPENAI_API_KEY
    openai_base_url: str = "https://api.openai.com/v1"  # Can be changed for OpenRouter, etc.
    openai_model: str = "gpt-4o-mini"  # Default model for adaptation
    openai_timeout: float = 60.0  # seconds
    
    # LLM Provider
    llm_provider: Literal["openai", "anthropic"] = "openai"
    
    # Default user settings (for MVP without auth)
    default_user_id: int = 1
    
    # e1RM formula options
    default_e1rm_formula: Literal["epley", "brzycki", "lombardi", "oconner"] = "epley"
    
    # Recovery settings
    soreness_decay_hours: int = 10  # Hours for 1 point of soreness decay (default)
    
    # RPE-based recovery rates (percentage recovered per hour)
    # Formula: recovery_rate_percent_per_hour = (100 - initial_recovery) / target_hours
    # Initial recovery after training depends on RPE (higher RPE = lower initial recovery)
    recovery_rate_percent_per_hour_rpe_6_7: float = 1.667   # (100-60)/24 = 1.667% per hour → full recovery in 24h
    recovery_rate_percent_per_hour_rpe_8: float = 1.250   # (100-40)/48 = 1.250% per hour → full recovery in 48h
    recovery_rate_percent_per_hour_rpe_9: float = 0.972   # (100-30)/72 = 0.972% per hour → full recovery in 72h
    recovery_rate_percent_per_hour_rpe_10: float = 0.833  # (100-20)/96 = 0.833% per hour → full recovery in 96h
    
    # Initial recovery percentage after training based on RPE
    initial_recovery_percent_by_rpe_rpe_6_7: int = 60   # 60% recovered (40% fatigued) after RPE 6-7
    initial_recovery_percent_by_rpe_rpe_8: int = 40   # 40% recovered (60% fatigued) after RPE 8
    initial_recovery_percent_by_rpe_rpe_9: int = 30   # 30% recovered (70% fatigued) after RPE 9
    initial_recovery_percent_by_rpe_rpe_10: int = 20  # 20% recovered (80% fatigued) after RPE 10
    
    admin_api_token: str | None = "gainsly-admin-123"
    # also in .env file in the fronend folder

    # JWT Authentication settings
    secret_key: str = "your-secret-key-change-in-production-use-environment-variable"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Performance Monitoring settings
    enable_performance_monitoring: bool = False
    performance_enable_tracemalloc: bool = False
    performance_latency_window_size: int = 1000
    performance_query_window_size: int = 500
    performance_memory_window_size: int = 60

    # Performance Alerting thresholds
    perf_p50_latency_warning: float = 0.1
    perf_p50_latency_critical: float = 0.25
    perf_p95_latency_warning: float = 0.5
    perf_p95_latency_critical: float = 1.0
    perf_p99_latency_warning: float = 1.0
    perf_p99_latency_critical: float = 2.5
    perf_query_duration_warning: float = 0.1
    perf_query_duration_critical: float = 0.5
    perf_memory_usage_warning: int = 512
    perf_memory_usage_critical: int = 1024
    perf_memory_growth_rate_warning: float = 10.0
    perf_error_rate_warning: float = 1.0
    perf_error_rate_critical: float = 5.0
    perf_regression_detection_threshold: float = 20.0
    perf_slow_query_threshold: float = 0.1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars (e.g., deprecated OLLAMA_* settings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
