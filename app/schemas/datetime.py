from datetime import date, datetime
from pydantic import BeforeValidator, TypeAdapter
from typing import Any


def parse_datetime(value: Any) -> datetime:
    """Parse ISO 8601 datetime string."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid datetime format: {value}")
    raise ValueError(f"Expected datetime, got {type(value)}")


def parse_date(value: Any) -> date:
    """Parse ISO 8601 date string."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ValueError(f"Invalid date format: {value}")
    raise ValueError(f"Expected date, got {type(value)}")


DateTimeStr = TypeAdapter(datetime).validate_python
DateStr = TypeAdapter(date).validate_python
