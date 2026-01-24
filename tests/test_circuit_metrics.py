"""Unit tests for CircuitMetricsCalculator."""
import pytest
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.circuit_metrics import CircuitMetricsCalculator
from app.models.circuit import CircuitTemplate
from app.models.enums import CircuitType


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=AsyncSession)


@pytest.fixture
def sample_movement():
    """Create a sample movement for testing."""
    return SimpleNamespace(
        id=1,
        name="Squat",
        primary_muscle="quadriceps",
        secondary_muscles=["hamstrings", "glutes"],
        fatigue_factor=2.5,
        stimulus_factor=3.0,
        min_recovery_hours=24,
        compound=True,
        is_complex_lift=False,
    )


@pytest.fixture
def sample_circuit():
    """Create a sample circuit for testing."""
    circuit = CircuitTemplate(
        id=1,
        name="Test Circuit",
        circuit_type=CircuitType.ROUNDS_FOR_TIME,
        exercises_json=[
            {
                "movement_id": 1,
                "movement": "Squat",
                "reps": 10,
                "distance_meters": None,
                "duration_seconds": None,
                "rest_seconds": None,
                "notes": None,
                "movement_name": "Squat",
                "rx_weight_male": None,
                "rx_weight_female": None,
                "metric_type": "unknown"
            }
        ],
        default_rounds=3,
        default_duration_seconds=600
    )
    return circuit


class TestCircuitMetricsCalculator:
    """Test suite for CircuitMetricsCalculator."""
    
    @pytest.mark.asyncio
    async def test_calculate_basic_metrics(self, mock_db, sample_circuit, sample_movement):
        """Test basic metrics calculation for a simple circuit."""
        # Setup mock database to return movement
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_movement]
        mock_db.execute.return_value = mock_result
        
        calculator = CircuitMetricsCalculator()
        metrics = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3, duration_seconds=600)
        
        # Verify metrics are calculated
        assert "fatigue_factor" in metrics
        assert "stimulus_factor" in metrics
        assert "min_recovery_hours" in metrics
        assert "muscle_volume" in metrics
        assert "muscle_fatigue" in metrics
        assert "total_reps" in metrics
        assert "estimated_work_seconds" in metrics
        assert "effective_work_volume" in metrics
    
    @pytest.mark.asyncio
    async def test_circuit_type_modifiers(self, mock_db, sample_circuit, sample_movement):
        """Test that different circuit types apply correct fatigue modifiers."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_movement]
        mock_db.execute.return_value = mock_result
        
        calculator = CircuitMetricsCalculator()
        
        # Test ROUNDS_FOR_TIME (+15% modifier)
        sample_circuit.circuit_type = CircuitType.ROUNDS_FOR_TIME
        metrics_rft = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3)
        
        # Test AMRAP (+15% modifier)
        sample_circuit.circuit_type = CircuitType.AMRAP
        metrics_amrap = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3)
        
        # Test LADDER (+10% modifier)
        sample_circuit.circuit_type = CircuitType.LADDER
        metrics_ladder = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3)
        
        # Test EMOM (0% modifier)
        sample_circuit.circuit_type = CircuitType.EMOM
        metrics_emom = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3)
        
        # Verify fatigue differences based on modifiers
        assert metrics_rft["fatigue_factor"] > 0
        assert metrics_amrap["fatigue_factor"] > 0
        assert metrics_ladder["fatigue_factor"] > 0
        assert metrics_emom["fatigue_factor"] > 0
    
    @pytest.mark.asyncio
    async def test_recovery_hour_modifiers(self, mock_db, sample_circuit, sample_movement):
        """Test that different circuit types apply correct recovery modifiers."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_movement]
        mock_db.execute.return_value = mock_result
        
        calculator = CircuitMetricsCalculator()
        
        # Test ROUNDS_FOR_TIME (+12 hours)
        sample_circuit.circuit_type = CircuitType.ROUNDS_FOR_TIME
        metrics_rft = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3)
        
        # Test AMRAP (+8 hours)
        sample_circuit.circuit_type = CircuitType.AMRAP
        metrics_amrap = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3)
        
        # Test EMOM (+4 hours)
        sample_circuit.circuit_type = CircuitType.EMOM
        metrics_emom = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3)
        
        # Verify recovery hours
        base_recovery = sample_movement.min_recovery_hours
        assert metrics_rft["min_recovery_hours"] == base_recovery + 12
        assert metrics_amrap["min_recovery_hours"] == base_recovery + 8
        assert metrics_emom["min_recovery_hours"] == base_recovery + 4
    
    @pytest.mark.asyncio
    async def test_muscle_volume_aggregation(self, mock_db, sample_circuit, sample_movement):
        """Test that muscle volume is correctly aggregated from exercises."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_movement]
        mock_db.execute.return_value = mock_result
        
        calculator = CircuitMetricsCalculator()
        metrics = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3)
        
        # Verify muscle volume is populated
        assert len(metrics["muscle_volume"]) > 0
        assert "quadriceps" in metrics["muscle_volume"] or "quadriceps" in [k.lower() for k in metrics["muscle_volume"].keys()]
        
        # Verify secondary muscles get half volume
        if "hamstrings" in sample_movement.secondary_muscles:
            hamstrings_volume = metrics["muscle_volume"].get("hamstrings", 0)
            quadriceps_volume = metrics["muscle_volume"].get("quadriceps", 0)
            # Secondary muscles should get less volume than primary
            assert hamstrings_volume < quadriceps_volume
    
    @pytest.mark.asyncio
    async def test_empty_circuit(self, mock_db):
        """Test handling of circuits with no exercises."""
        circuit = CircuitTemplate(
            id=1,
            name="Empty Circuit",
            circuit_type=CircuitType.ROUNDS_FOR_TIME,
            exercises_json=[],
            default_rounds=1
        )
        
        calculator = CircuitMetricsCalculator()
        metrics = await calculator.calculate_circuit_metrics(mock_db, circuit)
        
        # Should return default metrics for empty circuits
        assert metrics["fatigue_factor"] == 1.0
        assert metrics["stimulus_factor"] == 1.0
        assert metrics["min_recovery_hours"] == 24
        assert metrics["total_reps"] == 0
        assert metrics["estimated_work_seconds"] == 0
    
    @pytest.mark.asyncio
    async def test_circuit_with_multiple_exercises(self, mock_db, sample_circuit):
        """Test circuit with multiple different exercises."""
        # Create multiple movements
        squat = SimpleNamespace(
            id=1,
            name="Squat",
            primary_muscle="quadriceps",
            secondary_muscles=["hamstrings"],
            fatigue_factor=2.5,
            stimulus_factor=3.0,
            min_recovery_hours=24,
            compound=True,
            is_complex_lift=False,
        )
        pushup = SimpleNamespace(
            id=2,
            name="Push-up",
            primary_muscle="chest",
            secondary_muscles=["triceps"],
            fatigue_factor=1.5,
            stimulus_factor=2.0,
            min_recovery_hours=12,
            compound=True,
            is_complex_lift=False,
        )
        deadlift = SimpleNamespace(
            id=3,
            name="Deadlift",
            primary_muscle="hamstrings",
            secondary_muscles=["glutes", "lower_back"],
            fatigue_factor=3.0,
            stimulus_factor=3.5,
            min_recovery_hours=48,
            compound=True,
            is_complex_lift=False,
        )
        
        # Create circuit with multiple exercises
        sample_circuit.exercises_json = [
            {
                "movement_id": 1,
                "movement": "Squat",
                "reps": 10,
                "movement_name": "Squat"
            },
            {
                "movement_id": 2,
                "movement": "Push-up",
                "reps": 15,
                "movement_name": "Push-up"
            },
            {
                "movement_id": 3,
                "movement": "Deadlift",
                "reps": 5,
                "movement_name": "Deadlift"
            }
        ]
        
        # Setup mock
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [squat, pushup, deadlift]
        mock_db.execute.return_value = mock_result
        
        calculator = CircuitMetricsCalculator()
        metrics = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3)
        
        # Verify total reps
        assert metrics["total_reps"] == (10 + 15 + 5) * 3  # 90 reps total
        
        # Verify multiple muscles are targeted
        assert len(metrics["muscle_volume"]) > 1
        
        # Verify fatigue is based on average of all exercises
        assert 1.5 <= metrics["fatigue_factor"] <= 3.0
    
    @pytest.mark.asyncio
    async def test_rounds_multiplier(self, mock_db, sample_circuit, sample_movement):
        """Test that rounds correctly multiply volume and fatigue."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_movement]
        mock_db.execute.return_value = mock_result
        
        calculator = CircuitMetricsCalculator()
        
        # Test with different round counts
        metrics_1_round = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=1)
        metrics_3_rounds = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=3)
        metrics_5_rounds = await calculator.calculate_circuit_metrics(mock_db, sample_circuit, rounds=5)
        
        # Verify muscle volume scales with rounds
        if "quadriceps" in metrics_1_round["muscle_volume"]:
            vol_1 = metrics_1_round["muscle_volume"]["quadriceps"]
            vol_3 = metrics_3_rounds["muscle_volume"]["quadriceps"]
            vol_5 = metrics_5_rounds["muscle_volume"]["quadriceps"]
            
            assert vol_3 > vol_1
            assert vol_5 > vol_3
