"""LLM response schemas for structured output."""

# Output schemas for structured responses
SESSION_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "warmup": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "movement": {"type": "string"},
                    "sets": {"type": "integer"},
                    "reps": {"type": "integer"},
                    "duration_seconds": {"type": "integer"},
                    "notes": {"type": "string"}
                },
                "required": ["movement"]
            }
        },
        "main": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "movement": {"type": "string"},
                    "sets": {"type": "integer"},
                    "rep_range_min": {"type": "integer"},
                    "rep_range_max": {"type": "integer"},
                    "target_rpe": {"type": "number"},
                    "rest_seconds": {"type": "integer"},
                    "superset_with": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["movement", "sets"]
            }
        },
        "accessory": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "movement": {"type": "string"},
                    "sets": {"type": "integer"},
                    "rep_range_min": {"type": "integer"},
                    "rep_range_max": {"type": "integer"},
                    "target_rpe": {"type": "number"},
                    "rest_seconds": {"type": "integer"},
                    "superset_with": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["movement", "sets"]
            }
        },
        "finisher": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "duration_minutes": {"type": "integer"},
                "exercises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "movement": {"type": "string"},
                            "reps": {"type": "integer"},
                            "duration_seconds": {"type": "integer"}
                        }
                    }
                },
                "notes": {"type": "string"}
            }
        },
        "cooldown": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "movement": {"type": "string"},
                    "duration_seconds": {"type": "integer"},
                    "notes": {"type": "string"}
                },
                "required": ["movement"]
            }
        },
        "estimated_duration_minutes": {"type": "integer"},
        "reasoning": {"type": "string"},
        "trade_offs": {"type": "string"}
    },
    "required": ["main", "estimated_duration_minutes", "reasoning"]
}


ADAPTATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "adapted_plan": SESSION_PLAN_SCHEMA,
        "changes_made": {
            "type": "array",
            "items": {"type": "string"}
        },
        "reasoning": {"type": "string"},
        "trade_offs": {"type": "string"},
        "alternative_suggestion": {"type": "string"},
        "follow_up_question": {"type": "string"}
    },
    "required": ["adapted_plan", "changes_made", "reasoning"]
}
