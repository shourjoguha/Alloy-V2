import base64
import json
from datetime import datetime
from typing import Any

def encode_cursor(value: Any, field: str) -> str:
    """Encode a cursor value to a base64 string."""
    data = json.dumps({"field": field, "value": str(value)})
    return base64.b64encode(data.encode()).decode()

def decode_cursor(cursor: str) -> tuple[str, Any]:
    """Decode a base64 cursor string to field and value."""
    try:
        data = base64.b64decode(cursor).decode()
        decoded = json.loads(data)
        return decoded["field"], decoded["value"]
    except Exception:
        raise ValueError("Invalid cursor format")
