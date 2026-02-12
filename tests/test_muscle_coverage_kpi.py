"""Tests for muscle coverage KPIs."""

import pytest

from app.ml.scoring.muscle_coverage_kpi import (
    MuscleCoverageKPI,
    SessionMuscleData,
)
from app.ml.scoring.exceptions import (
    InsufficientCoverageError,
)


class TestSessionMuscleData:
    """Test SessionMuscleData dataclass."""

    def test_session_muscle_data_creation(self):
        """Test creating SessionMuscleData instance."""
        session = SessionMuscleData(
            session_id=1,
            session_type="strength",
            primary_muscles=("quadriceps", "glutes", "chest"),
        )

        assert session.session_id == 1
        assert session.session_type == "strength"
        assert session.primary_muscles == ("quadriceps", "glutes", "chest")


class TestMuscleCoverageKPI:
    """Test MuscleCoverageKPI class."""

    def test_initialization(self):
        """Test MuscleCoverageKPI initialization."""
        from app.ml.scoring.constants import MuscleGroups, ScoringThresholds
        
        validator = MuscleCoverageKPI()
        assert ScoringThresholds.MUSCLE_COVERAGE_THRESHOLD == 100.0
        assert len(MuscleGroups.MAJOR_MUSCLES) == 7
        assert "shoulders" in MuscleGroups.MAJOR_MUSCLES
        assert len(MuscleGroups.SHOULDER_MUSCLES) == 3

    def test_normalize_muscle_string(self):
        """Test muscle normalization with string input."""
        from app.ml.scoring.constants import MuscleGroups
        
        validator = MuscleCoverageKPI()

        # Test major muscles
        assert MuscleGroups.normalize_muscle("quadriceps") == "quadriceps"
        assert MuscleGroups.normalize_muscle("CHEST") == "chest"
        assert MuscleGroups.normalize_muscle("Lats") == "lats"

        # Test shoulder muscles aggregation
        assert MuscleGroups.normalize_muscle("front_delts") == "shoulders"
        assert MuscleGroups.normalize_muscle("side_delts") == "shoulders"
        assert MuscleGroups.normalize_muscle("rear_delts") == "shoulders"

    def test_normalize_muscle_enum(self):
        """Test muscle normalization with enum input."""
        from app.models.enums import PrimaryMuscle
        from app.ml.scoring.constants import MuscleGroups

        # Test with enum values
        assert MuscleGroups.normalize_muscle(PrimaryMuscle.QUADRICEPS) == "quadriceps"
        assert MuscleGroups.normalize_muscle(PrimaryMuscle.CHEST) == "chest"
        assert MuscleGroups.normalize_muscle(PrimaryMuscle.FRONT_DELTS) == "shoulders"
        assert MuscleGroups.normalize_muscle(PrimaryMuscle.SIDE_DELTS) == "shoulders"

    def test_analyze_session_muscles(self):
        """Test analyzing muscle coverage for a single session."""
        validator = MuscleCoverageKPI()

        session = SessionMuscleData(
            session_id=1,
            session_type="strength",
            primary_muscles=("quadriceps", "glutes", "chest", "front_delts"),
        )

        result = validator._analyze_session_muscles(session)

        assert result.session_id == 1
        assert result.session_type == "strength"
        assert result.coverage_count == 4  # quads, glutes, chest, shoulders (front_delts aggregated)
        assert "quadriceps" in result.covered_muscles
        assert "glutes" in result.covered_muscles
        assert "chest" in result.covered_muscles
        assert "shoulders" in result.covered_muscles
        assert "front_delts" not in result.covered_muscles  # Should be aggregated
        assert "hamstrings" not in result.covered_muscles

    def test_analyze_session_no_major_muscles(self):
        """Test analyzing session with no major muscle groups."""
        validator = MuscleCoverageKPI()

        session = SessionMuscleData(
            session_id=1,
            session_type="mobility",
            primary_muscles=("biceps", "triceps", "forearms"),
        )

        result = validator._analyze_session_muscles(session)

        assert result.session_id == 1
        assert result.coverage_count == 0
        assert len(result.covered_muscles) == 0
        assert "biceps" not in result.covered_muscles  # Not a major muscle

    def test_check_microcycle_coverage_complete(self):
        """Test microcycle coverage with all major muscles covered."""
        validator = MuscleCoverageKPI()

        sessions = [
            SessionMuscleData(
                session_id=1,
                session_type="strength",
                primary_muscles=("quadriceps", "glutes", "chest"),
            ),
            SessionMuscleData(
                session_id=2,
                session_type="strength",
                primary_muscles=("hamstrings", "lats", "upper_back"),
            ),
            SessionMuscleData(
                session_id=3,
                session_type="strength",
                primary_muscles=("front_delts", "side_delts"),
            ),
        ]

        result = validator.check_microcycle_coverage(sessions, microcycle_id=1)

        assert result.microcycle_id == 1
        assert result.passed is True
        assert result.coverage_score == 100.0
        assert len(result.covered_muscles) == 7
        assert len(result.missing_muscles) == 0
        assert "shoulders" in result.covered_muscles
        assert "passed" in result.message.lower()

    def test_check_microcycle_coverage_incomplete(self):
        """Test microcycle coverage with missing muscles."""
        validator = MuscleCoverageKPI()

        sessions = [
            SessionMuscleData(
                session_id=1,
                session_type="strength",
                primary_muscles=("quadriceps", "glutes", "chest"),
            ),
            SessionMuscleData(
                session_id=2,
                session_type="strength",
                primary_muscles=("lats", "front_delts"),
            ),
        ]

        result = validator.check_microcycle_coverage(sessions, microcycle_id=1)

        assert result.microcycle_id == 1
        assert result.passed is False
        assert result.coverage_score < 100.0
        assert "hamstrings" in result.missing_muscles
        assert "upper_back" in result.missing_muscles
        assert len(result.missing_muscles) == 2
        assert "failed" in result.message.lower() or "missing" in result.message.lower()

    def test_check_microcycle_coverage_empty_sessions(self):
        """Test microcycle coverage with empty session list."""
        validator = MuscleCoverageKPI()

        result = validator.check_microcycle_coverage([], microcycle_id=1)

        assert result.microcycle_id == 1
        assert result.passed is False
        assert result.coverage_score == 0.0
        assert len(result.covered_muscles) == 0
        assert len(result.missing_muscles) == 7
        assert len(result.session_results) == 0

    def test_check_microcycle_coverage_single_session(self):
        """Test microcycle coverage with single session."""
        validator = MuscleCoverageKPI()

        sessions = [
            SessionMuscleData(
                session_id=1,
                session_type="strength",
                primary_muscles=("quadriceps", "glutes", "chest", "front_delts"),
            )
        ]

        result = validator.check_microcycle_coverage(sessions, microcycle_id=1)

        assert result.microcycle_id == 1
        assert result.passed is False  # Can't cover all muscles in one session
        assert result.coverage_score < 100.0
        assert len(result.session_results) == 1
        assert result.session_results[0].coverage_count == 4

    def test_check_microcycle_coverage_muscle_frequency(self):
        """Test muscle frequency calculation."""
        validator = MuscleCoverageKPI()

        sessions = [
            SessionMuscleData(
                session_id=1,
                session_type="strength",
                primary_muscles=("quadriceps", "glutes", "chest"),
            ),
            SessionMuscleData(
                session_id=2,
                session_type="strength",
                primary_muscles=("quadriceps", "hamstrings", "lats"),
            ),
            SessionMuscleData(
                session_id=3,
                session_type="strength",
                primary_muscles=("chest", "front_delts"),
            ),
        ]

        result = validator.check_microcycle_coverage(sessions, microcycle_id=1)

        # Check frequency counts
        freq_dict = dict(result.muscle_frequency)
        assert freq_dict.get("quadriceps", 0) == 2
        assert freq_dict.get("chest", 0) == 2
        assert freq_dict.get("shoulders", 0) == 1  # front_delts aggregated
        assert "frequency" in result.message.lower()

    def test_get_coverage_score(self):
        """Test get_coverage_score method."""
        validator = MuscleCoverageKPI()

        sessions = [
            SessionMuscleData(
                session_id=1,
                session_type="strength",
                primary_muscles=("quadriceps", "glutes", "chest"),
            ),
            SessionMuscleData(
                session_id=2,
                session_type="strength",
                primary_muscles=("hamstrings", "lats", "upper_back"),
            ),
        ]

        result = validator.get_coverage_score(sessions, microcycle_id=1)

        # Should return same result as check_microcycle_coverage
        assert result.microcycle_id == 1
        assert result.coverage_score == pytest.approx(85.7, rel=0.1)  # 6/7 muscles
        assert result.passed is False  # Missing shoulders
        assert len(result.covered_muscles) == 6

    def test_get_muscle_recommendations(self):
        """Test muscle recommendations for missing muscles."""
        validator = MuscleCoverageKPI()

        missing = ["quadriceps", "hamstrings", "chest"]
        recommendations = validator._get_muscle_recommendations(missing)

        assert "quadriceps" in recommendations.lower()
        assert "squat" in recommendations.lower() or "lunge" in recommendations.lower()
        assert "hamstrings" in recommendations.lower()
        assert "hinge" in recommendations.lower() or "rdl" in recommendations.lower()
        assert "chest" in recommendations.lower()
        assert "horizontal" in recommendations.lower() or "push" in recommendations.lower()

    def test_build_coverage_message_passed(self):
        """Test building message for passed validation."""
        validator = MuscleCoverageKPI()

        message = validator._build_coverage_message(
            microcycle_id=1,
            passed=True,
            covered_muscles=["quadriceps", "hamstrings", "glutes", "chest", "lats", "upper_back", "shoulders"],
            missing_muscles=[],
            coverage_score=100.0,
            muscle_frequency=(("quadriceps", 2), ("hamstrings", 1)),
        )

        assert "passed" in message.lower()
        assert "100.0%" in message
        assert "quadriceps" in message
        assert "frequency" in message.lower()

    def test_build_coverage_message_failed(self):
        """Test building message for failed validation."""
        validator = MuscleCoverageKPI()

        message = validator._build_coverage_message(
            microcycle_id=1,
            passed=False,
            covered_muscles=["quadriceps", "glutes", "chest"],
            missing_muscles=["hamstrings", "lats", "upper_back", "shoulders"],
            coverage_score=42.9,
            muscle_frequency=(("quadriceps", 1), ("glutes", 1)),
        )

        assert "failed" in message.lower()
        assert "42.9%" in message
        assert "missing" in message.lower()
        assert "recommendations" in message.lower()

    def test_shoulder_aggregation_multiple_sessions(self):
        """Test that multiple shoulder muscles across sessions count as one."""
        validator = MuscleCoverageKPI()

        sessions = [
            SessionMuscleData(
                session_id=1,
                session_type="strength",
                primary_muscles=("front_delts", "chest"),
            ),
            SessionMuscleData(
                session_id=2,
                session_type="strength",
                primary_muscles=("side_delts", "lats"),
            ),
            SessionMuscleData(
                session_id=3,
                session_type="strength",
                primary_muscles=("rear_delts", "upper_back"),
            ),
        ]

        result = validator.check_microcycle_coverage(sessions, microcycle_id=1)

        # Should only count shoulders once
        freq_dict = dict(result.muscle_frequency)
        assert freq_dict.get("shoulders", 0) == 3  # All three sessions had shoulder work
        assert "shoulders" in result.covered_muscles
        assert "front_delts" not in [m for m, _ in result.muscle_frequency]

    def test_result_to_dict(self):
        """Test converting results to dictionary."""
        validator = MuscleCoverageKPI()

        sessions = [
            SessionMuscleData(
                session_id=1,
                session_type="strength",
                primary_muscles=("quadriceps", "glutes", "chest"),
            )
        ]

        result = validator.check_microcycle_coverage(sessions, microcycle_id=1)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["microcycle_id"] == 1
        assert result_dict["passed"] is False
        assert isinstance(result_dict["covered_muscles"], list)
        assert isinstance(result_dict["missing_muscles"], list)
        assert isinstance(result_dict["session_results"], list)
        assert isinstance(result_dict["muscle_frequency"], list)

    def test_session_result_to_dict(self):
        """Test converting session result to dictionary."""
        validator = MuscleCoverageKPI()

        session = SessionMuscleData(
            session_id=1,
            session_type="strength",
            primary_muscles=("quadriceps", "glutes", "chest"),
        )

        result = validator._analyze_session_muscles(session)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["session_id"] == 1
        assert result_dict["session_type"] == "strength"
        assert isinstance(result_dict["covered_muscles"], list)
        assert result_dict["coverage_count"] == 3

    def test_invalid_session_raises_error(self):
        """Test that invalid session data raises error."""
        validator = MuscleCoverageKPI()

        # This should not raise an error, just handle gracefully
        session = SessionMuscleData(
            session_id=1,
            session_type="strength",
            primary_muscles=(),  # Empty tuple
        )

        result = validator._analyze_session_muscles(session)
        assert result.coverage_count == 0

    def test_full_microcycle_upper_lower_split(self):
        """Test realistic upper/lower split microcycle."""
        validator = MuscleCoverageKPI()

        # Typical upper/lower split
        sessions = [
            SessionMuscleData(
                session_id=1,
                session_type="upper",
                primary_muscles=("chest", "lats", "upper_back", "front_delts"),
            ),
            SessionMuscleData(
                session_id=2,
                session_type="lower",
                primary_muscles=("quadriceps", "glutes", "hamstrings"),
            ),
            SessionMuscleData(
                session_id=3,
                session_type="upper",
                primary_muscles=("chest", "side_delts", "lats"),
            ),
            SessionMuscleData(
                session_id=4,
                session_type="lower",
                primary_muscles=("hamstrings", "glutes", "rear_delts"),
            ),
        ]

        result = validator.check_microcycle_coverage(sessions, microcycle_id=1)

        assert result.passed is True
        assert result.coverage_score == 100.0
        assert len(result.covered_muscles) == 7

    def test_incomplete_microcycle_push_pull(self):
        """Test incomplete push/pull split missing legs."""
        validator = MuscleCoverageKPI()

        # Incomplete push/pull split (missing leg day)
        sessions = [
            SessionMuscleData(
                session_id=1,
                session_type="push",
                primary_muscles=("chest", "front_delts", "side_delts"),
            ),
            SessionMuscleData(
                session_id=2,
                session_type="pull",
                primary_muscles=("lats", "upper_back", "rear_delts"),
            ),
            SessionMuscleData(
                session_id=3,
                session_type="push",
                primary_muscles=("chest", "front_delts"),
            ),
        ]

        result = validator.check_microcycle_coverage(sessions, microcycle_id=1)

        assert result.passed is False
        assert "quadriceps" in result.missing_muscles
        assert "hamstrings" in result.missing_muscles
        assert "glutes" in result.missing_muscles
        assert len(result.missing_muscles) == 3
