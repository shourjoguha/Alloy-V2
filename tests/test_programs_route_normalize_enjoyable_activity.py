from app.api.routes.programs import _normalize_enjoyable_activity
from app.models.enums import EnjoyableActivity


def test_normalize_enjoyable_activity_passthrough():
    activity, custom = _normalize_enjoyable_activity("tennis", None)
    assert activity == EnjoyableActivity.TENNIS
    assert custom is None


def test_normalize_enjoyable_activity_custom_maps_to_other():
    activity, custom = _normalize_enjoyable_activity("custom", "skating")
    assert activity == EnjoyableActivity.OTHER
    assert custom == "skating"


def test_normalize_enjoyable_activity_unknown_maps_to_other_with_custom_name():
    activity, custom = _normalize_enjoyable_activity("running", None)
    assert activity == EnjoyableActivity.OTHER
    assert custom == "running"

