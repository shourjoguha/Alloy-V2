# JSONB Interface Migration Strategy

## Current State Analysis

### Existing Database Schema
```python
# Movement Model (app/models/movement.py)
tier = Column(SQLEnum(MovementTier), nullable=False, default=MovementTier.BRONZE, index=True)
metabolic_demand = Column(SQLEnum(MetabolicDemand), nullable=False, default=MetabolicDemand.ANABOLIC, index=True)
biomechanics_profile = Column(JSONB, nullable=True, default=dict)
```

### Existing Enums
```python
# MovementTier (app/models/enums.py)
class MovementTier(str, Enum):
    DIAMOND = "diamond"
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"

# MetabolicDemand (app/models/enums.py)
class MetabolicDemand(str, Enum):
    ANABOLIC = "anabolic"
    METABOLIC = "metabolic"
    NEURAL = "neural"
```

### Missing Components
1. Pydantic schemas don't expose `tier`, `metabolic_demand`, `biomechanics_profile`
2. No validation for `biomechanics_profile` JSONB content
3. Disciplines use junction table (good for referential integrity)
4. No PostgreSQL array/JSONB query optimization

---

## Migration Strategy

### Phase 1: Schema Enhancement

#### 1.1 Update Pydantic Schemas

**MovementResponse Schema Update**
```python
class MovementResponse(BaseModel):
    # Existing fields...
    
    # New fields to expose
    tier: MovementTier | None = None
    metabolic_demand: MetabolicDemand | None = None
    biomechanics_profile: dict[str, Any] | None = None
    
    # Existing computed fields...
```

**MovementCreate Schema Update**
```python
class MovementCreate(BaseModel):
    name: str
    pattern: MovementPattern
    primary_muscle: PrimaryMuscle | None = None
    primary_region: PrimaryRegion | None = None
    
    # New fields
    tier: MovementTier = MovementTier.BRONZE
    metabolic_demand: MetabolicDemand = MetabolicDemand.ANABOLIC
    biomechanics_profile: dict[str, Any] | None = None
    
    # Existing fields...
    secondary_muscles: list[PrimaryMuscle] | None = None
    default_equipment: str | None = None
    skill_level: SkillLevel | None = SkillLevel.INTERMEDIATE
    cns_load: CNSLoad | None = CNSLoad.MODERATE
    metric_type: MetricType | None = MetricType.REPS
    compound: bool = True
    description: str | None = None
```

**MovementUpdate Schema**
```python
class MovementUpdate(BaseModel):
    name: str | None = None
    tier: MovementTier | None = None
    metabolic_demand: MetabolicDemand | None = None
    biomechanics_profile: dict[str, Any] | None = None
    # ... other updatable fields
```

#### 1.2 Biomechanics Profile Structure

**Standardized JSONB Schema**
```python
# Biomechanics Profile Template
BIOMECHANICS_PROFILE_TEMPLATE = {
    "archetype": str,  # e.g., "bilateral_compound", "unilateral_isolation"
    "movement_vectors": {
        "primary": str,  # "sagittal", "frontal", "transverse"
        "secondary": list[str]
    },
    "joint_involvement": {
        "ankle": float,  # 0-10 intensity
        "knee": float,
        "hip": float,
        "lumbar": float,
        "shoulder": float,
        "elbow": float,
        "wrist": float
    },
    "loading_pattern": {
        "type": str,  # "axial", "peripheral", "hybrid"
        "spinal_load": str  # "none", "low", "moderate", "high"
    },
    "stability_demands": {
        "balance": float,  # 0-10
        "coordination": float,  # 0-10
        "core_engagement": float  # 0-10
    },
    "range_of_motion": {
        "flexion": str,  # "full", "partial", "isometric"
        "extension": str,
        "rotation": str
    },
    "temporal_factors": {
        "eccentric_emphasis": bool,
        "isometric_hold": bool,
        "explosive_component": bool
    }
}

# Archetype Enums (Soft Enum)
ARCHETYPE_VALUES = [
    "bilateral_compound",      # Squat, Deadlift, Bench Press
    "unilateral_compound",     # Bulgarian Split Squat, Single-Leg RDL
    "bilateral_isolation",     # Leg Extension, Leg Curl
    "unilateral_isolation",    # Single-Leg Press, Lateral Raise
    "dynamic_compound",        # Clean & Jerk, Snatch
    "static_compound",         # Plank variations, Isometric holds
    "plyometric",              # Box Jumps, Medicine Ball Throws
    "carry_pattern",           # Farmer's Walk, Suitcase Carry
    "rotational_compound",     # Russian Twist, Woodchop
    "conditioning_pattern"     # Burpees, Rowing intervals
]
```

---

### Phase 2: Soft Enum Validation

#### 2.1 Biomechanics Profile Validator

```python
from pydantic import field_validator, model_validator
from typing import Literal

class BiomechanicsProfileValidator(BaseModel):
    """Soft enum validation for biomechanics_profile JSONB."""
    
    archetype: str
    movement_vectors: dict[str, Any]
    joint_involvement: dict[str, float]
    loading_pattern: dict[str, str]
    stability_demands: dict[str, float]
    range_of_motion: dict[str, str]
    temporal_factors: dict[str, bool]
    
    @field_validator('archetype')
    @classmethod
    def validate_archetype(cls, v: str) -> str:
        """Validate archetype against allowed values."""
        valid_archetypes = {
            "bilateral_compound", "unilateral_compound", "bilateral_isolation",
            "unilateral_isolation", "dynamic_compound", "static_compound",
            "plyometric", "carry_pattern", "rotational_compound", "conditioning_pattern"
        }
        if v not in valid_archetypes:
            raise ValueError(f"Invalid archetype '{v}'. Must be one of: {valid_archetypes}")
        return v
    
    @field_validator('movement_vectors')
    @classmethod
    def validate_movement_vectors(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate movement vector structure."""
        valid_planes = {"sagittal", "frontal", "transverse"}
        
        if 'primary' not in v:
            raise ValueError("movement_vectors must contain 'primary' key")
        
        if v['primary'] not in valid_planes:
            raise ValueError(f"Invalid primary plane: {v['primary']}")
        
        if 'secondary' in v:
            if not isinstance(v['secondary'], list):
                raise ValueError("movement_vectors.secondary must be a list")
            for plane in v['secondary']:
                if plane not in valid_planes:
                    raise ValueError(f"Invalid secondary plane: {plane}")
        
        return v
    
    @field_validator('joint_involvement')
    @classmethod
    def validate_joint_involvement(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate joint involvement scores (0-10)."""
        valid_joints = {"ankle", "knee", "hip", "lumbar", "shoulder", "elbow", "wrist"}
        
        for joint, score in v.items():
            if joint not in valid_joints:
                raise ValueError(f"Invalid joint: {joint}")
            if not isinstance(score, (int, float)):
                raise ValueError(f"Joint score must be numeric: {joint}")
            if not 0 <= score <= 10:
                raise ValueError(f"Joint score must be 0-10: {joint}={score}")
        
        return v
    
    @field_validator('loading_pattern')
    @classmethod
    def validate_loading_pattern(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate loading pattern structure."""
        valid_types = {"axial", "peripheral", "hybrid"}
        valid_spinal_loads = {"none", "low", "moderate", "high"}
        
        if 'type' not in v or v['type'] not in valid_types:
            raise ValueError(f"Invalid loading_pattern.type: {v.get('type')}")
        
        if 'spinal_load' not in v or v['spinal_load'] not in valid_spinal_loads:
            raise ValueError(f"Invalid loading_pattern.spinal_load: {v.get('spinal_load')}")
        
        return v
    
    @field_validator('stability_demands')
    @classmethod
    def validate_stability_demands(cls, v: dict[str, float]) -> dict[str, float]:
        """Validate stability demand scores (0-10)."""
        for demand, score in v.items():
            if not isinstance(score, (int, float)):
                raise ValueError(f"Stability demand must be numeric: {demand}")
            if not 0 <= score <= 10:
                raise ValueError(f"Stability demand must be 0-10: {demand}={score}")
        return v
    
    @field_validator('range_of_motion')
    @classmethod
    def validate_range_of_motion(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate range of motion values."""
        valid_rom = {"full", "partial", "isometric", "none"}
        
        for rom_type, value in v.items():
            if value not in valid_rom:
                raise ValueError(f"Invalid ROM value: {rom_type}={value}")
        return v
```

#### 2.2 Integration with MovementCreate

```python
class MovementCreate(BaseModel):
    name: str
    pattern: MovementPattern
    primary_muscle: PrimaryMuscle | None = None
    primary_region: PrimaryRegion | None = None
    
    tier: MovementTier = MovementTier.BRONZE
    metabolic_demand: MetabolicDemand = MetabolicDemand.ANABOLIC
    biomechanics_profile: dict[str, Any] | None = None
    
    secondary_muscles: list[PrimaryMuscle] | None = None
    default_equipment: str | None = None
    skill_level: SkillLevel | None = SkillLevel.INTERMEDIATE
    cns_load: CNSLoad | None = CNSLoad.MODERATE
    metric_type: MetricType | None = MetricType.REPS
    compound: bool = True
    description: str | None = None
    
    @field_validator('biomechanics_profile')
    @classmethod
    def validate_biomechanics_profile(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate biomechanics_profile if provided."""
        if v is not None:
            try:
                BiomechanicsProfileValidator(**v)
            except ValueError as e:
                raise ValueError(f"Invalid biomechanics_profile: {e}")
        return v
```

---

### Phase 3: Query Optimization

#### 3.1 PostgreSQL Array Operators

**Current Approach (Junction Table)**
```python
# Current: Join with movement_disciplines
query = (
    select(Movement)
    .join(MovementDiscipline)
    .where(MovementDiscipline.discipline == DisciplineType.POWERLIFTING)
)
```

**Optimized with GIN Index**
```sql
-- Create GIN index for faster array/JSONB queries
CREATE INDEX idx_movements_biomechanics_profile_gin 
ON movements USING GIN (biomechanics_profile);

-- Create expression index for archetype
CREATE INDEX idx_movements_archetype 
ON movements USING BTREE ((biomechanics_profile->>'archetype'));

-- Create index for joint involvement queries
CREATE INDEX idx_movements_spinal_load 
ON movements USING BTREE ((biomechanics_profile->'loading_pattern'->>'spinal_load'));
```

**Query Patterns**

**1. Biomechanics Profile Queries**
```python
# Query by archetype
async def get_movements_by_archetype(
    db: AsyncSession, 
    archetype: str
) -> list[Movement]:
    result = await db.execute(
        select(Movement).where(
            Movement.biomechanics_profile['archetype'].astext == archetype
        )
    )
    return result.scalars().all()

# Query by spinal load level
async def get_low_spinal_load_movements(
    db: AsyncSession
) -> list[Movement]:
    result = await db.execute(
        select(Movement).where(
            Movement.biomechanics_profile['loading_pattern']['spinal_load'].astext.in_(['none', 'low'])
        )
    )
    return result.scalars().all()

# Query by joint involvement threshold
async def get_knee_dominant_movements(
    db: AsyncSession,
    min_score: float = 7.0
) -> list[Movement]:
    result = await db.execute(
        select(Movement).where(
            Movement.biomechanics_profile['joint_involvement']['knee'].astext.cast(Float) >= min_score
        )
    )
    return result.scalars().all()

# Complex biomechanics query (high knee involvement, low spinal load)
async def get_knee_dominant_low_spinal_movements(
    db: AsyncSession,
    min_knee: float = 7.0,
    max_spinal: list[str] = ['none', 'low']
) -> list[Movement]:
    result = await db.execute(
        select(Movement).where(
            and_(
                Movement.biomechanics_profile['joint_involvement']['knee'].astext.cast(Float) >= min_knee,
                Movement.biomechanics_profile['loading_pattern']['spinal_load'].astext.in_(max_spinal)
            )
        )
    )
    return result.scalars().all()
```

**2. Tier-Based Queries**
```python
# Get movements by tier (tier column has index)
async def get_tiered_movements(
    db: AsyncSession,
    tier: MovementTier
) -> list[Movement]:
    result = await db.execute(
        select(Movement).where(Movement.tier == tier)
    )
    return result.scalars().all()

# Get movements by tier range
async def get_premium_tier_movements(
    db: AsyncSession
) -> list[Movement]:
    result = await db.execute(
        select(Movement).where(
            Movement.tier.in_([MovementTier.DIAMOND, MovementTier.GOLD])
        )
    )
    return result.scalars().all()
```

**3. Metabolic Demand Queries**
```python
# Get movements by metabolic demand
async def get_metabolic_movements(
    db: AsyncSession,
    demand: MetabolicDemand
) -> list[Movement]:
    result = await db.execute(
        select(Movement).where(Movement.metabolic_demand == demand)
    )
    return result.scalars().all()

# Get anabolic movements (good for hypertrophy)
async def get_anabolic_movements(db: AsyncSession) -> list[Movement]:
    result = await db.execute(
        select(Movement).where(
            Movement.metabolic_demand == MetabolicDemand.ANABOLIC
        )
    )
    return result.scalars().all()
```

**4. Combined Queries**
```python
# Get high-tier anabolic movements with low spinal load
async def get_hypertrophy_friendly_movements(
    db: AsyncSession
) -> list[Movement]:
    result = await db.execute(
        select(Movement).where(
            and_(
                Movement.tier.in_([MovementTier.DIAMOND, MovementTier.GOLD]),
                Movement.metabolic_demand == MetabolicDemand.ANABOLIC,
                Movement.biomechanics_profile['loading_pattern']['spinal_load'].astext.in_(['none', 'low'])
            )
        )
    )
    return result.scalars().all()

# Tier-weighted movement selection
async def get_tier_weighted_movements(
    db: AsyncSession,
    pattern: MovementPattern,
    limit: int = 10
) -> list[Movement]:
    # Weight tiers: DIAMOND=4, GOLD=3, SILVER=2, BRONZE=1
    tier_weights = {
        MovementTier.DIAMOND: 4,
        MovementTier.GOLD: 3,
        MovementTier.SILVER: 2,
        MovementTier.BRONZE: 1
    }
    
    result = await db.execute(
        select(Movement)
        .where(Movement.pattern == pattern)
        .order_by(
            # This is a conceptual ordering; actual implementation requires CASE expression
            # Order by tier weight (desc), then by stimulus_factor (desc)
        )
        .limit(limit)
    )
    return result.scalars().all()
```

#### 3.2 Database Migration

```python
# alembic/versions/xxx_add_jsonb_indexes.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create GIN index for biomechanics_profile JSONB queries
    op.execute("""
        CREATE INDEX idx_movements_biomechanics_profile_gin 
        ON movements USING GIN (biomechanics_profile);
    """)
    
    # Create expression index for archetype
    op.execute("""
        CREATE INDEX idx_movements_archetype 
        ON movements USING BTREE ((biomechanics_profile->>'archetype'));
    """)
    
    # Create index for spinal load queries
    op.execute("""
        CREATE INDEX idx_movements_spinal_load 
        ON movements USING BTREE ((biomechanics_profile->'loading_pattern'->>'spinal_load'));
    """)
    
    # Create index for joint involvement (knee)
    op.execute("""
        CREATE INDEX idx_movements_knee_involvement 
        ON movements USING BTREE (
            (biomechanics_profile->'joint_involvement'->>'knee')::float
        );
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_movements_knee_involvement")
    op.execute("DROP INDEX IF EXISTS idx_movements_spinal_load")
    op.execute("DROP INDEX IF EXISTS idx_movements_archetype")
    op.execute("DROP INDEX IF EXISTS idx_movements_biomechanics_profile_gin")
```

---

### Phase 4: Safety-First Substitution Logic

#### 4.1 Biomechanics-Based Substitution

```python
from typing import Optional

class MovementSubstitutionService:
    """Service for biomechanics-aware movement substitution."""
    
    async def find_safest_substitution(
        self,
        db: AsyncSession,
        original_movement: Movement,
        user_spinal_tolerance: str = "moderate",  # none, low, moderate, high
        user_joint_health: dict[str, int] | None = None  # joint: max_intensity (0-10)
    ) -> Optional[Movement]:
        """
        Find the safest movement substitution based on biomechanics profile.
        
        Args:
            db: Database session
            original_movement: Movement to substitute
            user_spinal_tolerance: User's spinal load tolerance
            user_joint_health: User's joint health limits (joint: max_intensity)
        
        Returns:
            Safest alternative movement or None
        """
        if not user_joint_health:
            user_joint_health = {
                "ankle": 10, "knee": 10, "hip": 10, "lumbar": 10,
                "shoulder": 10, "elbow": 10, "wrist": 10
            }
        
        # Get movements in same substitution group
        query = (
            select(Movement)
            .where(
                and_(
                    Movement.substitution_group == original_movement.substitution_group,
                    Movement.id != original_movement.id
                )
            )
        )
        result = await db.execute(query)
        candidates = result.scalars().all()
        
        if not candidates:
            return None
        
        # Score each candidate for safety
        safest = None
        best_safety_score = -1
        
        for candidate in candidates:
            safety_score = self._calculate_safety_score(
                candidate,
                user_spinal_tolerance,
                user_joint_health
            )
            
            if safety_score > best_safety_score:
                best_safety_score = safety_score
                safest = candidate
        
        return safest
    
    def _calculate_safety_score(
        self,
        movement: Movement,
        spinal_tolerance: str,
        joint_health: dict[str, int]
    ) -> float:
        """Calculate safety score for a movement (0-1, higher is safer)."""
        if not movement.biomechanics_profile:
            return 0.5  # Neutral score if no biomechanics data
        
        profile = movement.biomechanics_profile
        score = 0.0
        
        # 1. Spinal load safety (weight: 0.4)
        spinal_load = profile.get('loading_pattern', {}).get('spinal_load', 'low')
        spinal_scores = {'none': 1.0, 'low': 0.8, 'moderate': 0.5, 'high': 0.2}
        tolerance_levels = {'none': 0, 'low': 1, 'moderate': 2, 'high': 3}
        
        load_score = spinal_scores.get(spinal_load, 0.5)
        tolerance_level = tolerance_levels.get(spinal_tolerance, 2)
        
        # Penalize if spinal load exceeds tolerance
        if spinal_scores.get(spinal_load, 0.5) < spinal_scores.get(spinal_tolerance, 0.5):
            load_score *= 0.5
        
        score += load_score * 0.4
        
        # 2. Joint involvement safety (weight: 0.4)
        joint_involvement = profile.get('joint_involvement', {})
        joint_score = 1.0
        
        for joint, intensity in joint_involvement.items():
            if joint in joint_health:
                max_intensity = joint_health[joint]
                if intensity > max_intensity:
                    # Penalize exceeding joint health limit
                    joint_score -= (intensity - max_intensity) / 10.0
        
        joint_score = max(0.0, joint_score)
        score += joint_score * 0.4
        
        # 3. Stability demands (weight: 0.2)
        stability = profile.get('stability_demands', {})
        avg_stability = sum(stability.values()) / len(stability) if stability else 5.0
        # Lower stability demands are safer
        stability_score = 1.0 - (avg_stability / 10.0) * 0.3
        score += stability_score * 0.2
        
        return score
    
    async def get_tiered_alternatives(
        self,
        db: AsyncSession,
        movement: Movement,
        tier_direction: str = "down"  # "up" or "down"
    ) -> list[Movement]:
        """
        Get alternative movements of different tiers.
        
        Args:
            db: Database session
            movement: Original movement
            tier_direction: "up" for higher tier, "down" for lower tier
        
        Returns:
            List of alternative movements sorted by tier
        """
        tier_order = [MovementTier.BRONZE, MovementTier.SILVER, MovementTier.GOLD, MovementTier.DIAMOND]
        current_tier_index = tier_order.index(movement.tier)
        
        if tier_direction == "up":
            target_tiers = tier_order[current_tier_index + 1:]
        else:
            target_tiers = tier_order[:current_tier_index]
        
        if not target_tiers:
            return []
        
        query = (
            select(Movement)
            .where(
                and_(
                    Movement.pattern == movement.pattern,
                    Movement.tier.in_(target_tiers)
                )
            )
        )
        result = await db.execute(query)
        return result.scalars().all()
```

---

### Phase 5: API Updates

#### 5.1 Movement Routes Updates

```python
# app/api/routes/settings.py

@router.post("/movements", response_model=MovementResponse)
async def create_movement(
    request: MovementCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Create a new custom movement."""
    new_movement = Movement(
        user_id=user_id,
        name=request.name,
        pattern=request.pattern,
        primary_muscle=request.primary_muscle,
        primary_region=request.primary_region,
        tier=request.tier,
        metabolic_demand=request.metabolic_demand,
        biomechanics_profile=request.biomechanics_profile,
        skill_level=request.skill_level,
        cns_load=request.cns_load,
        metric_type=request.metric_type,
        compound=request.compound,
        description=request.description
    )
    
    db.add(new_movement)
    await db.commit()
    
    # Load relationships for response
    await db.refresh(new_movement)
    await db.refresh(new_movement, ["disciplines", "equipment", "muscle_maps"])
    
    return MovementResponse.model_validate(new_movement)

@router.get("/movements/filter", response_model=list[MovementResponse])
async def filter_movements_by_biomechanics(
    archetype: str | None = None,
    spinal_load: str | None = None,
    min_joint_involvement: dict[str, float] | None = None,
    tier: MovementTier | None = None,
    metabolic_demand: MetabolicDemand | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Filter movements by biomechanics profile attributes."""
    conditions = []
    
    if tier:
        conditions.append(Movement.tier == tier)
    
    if metabolic_demand:
        conditions.append(Movement.metabolic_demand == metabolic_demand)
    
    if archetype:
        conditions.append(
            Movement.biomechanics_profile['archetype'].astext == archetype
        )
    
    if spinal_load:
        conditions.append(
            Movement.biomechanics_profile['loading_pattern']['spinal_load'].astext == spinal_load
        )
    
    if min_joint_involvement:
        for joint, min_score in min_joint_involvement.items():
            conditions.append(
                Movement.biomechanics_profile['joint_involvement'][joint].astext.cast(Float) >= min_score
            )
    
    query = (
        select(Movement)
        .where(and_(*conditions))
        .options(
            selectinload(Movement.disciplines),
            selectinload(Movement.equipment),
            selectinload(Movement.muscle_maps)
        )
    )
    
    result = await db.execute(query)
    movements = result.scalars().all()
    
    return [MovementResponse.model_validate(m) for m in movements]
```

---

## Implementation Checklist

### Phase 1: Schema Enhancement
- [ ] Add `tier`, `metabolic_demand`, `biomechanics_profile` to `MovementResponse`
- [ ] Add fields to `MovementCreate` with defaults
- [ ] Create `MovementUpdate` schema
- [ ] Define `BiomechanicsProfileValidator` class
- [ ] Add biomechanics_profile validation to `MovementCreate`

### Phase 2: Database Migration
- [ ] Create Alembic migration for JSONB indexes
- [ ] Add GIN index for biomechanics_profile
- [ ] Add expression indexes for archetype, spinal_load, knee_involvement
- [ ] Test migration on development database

### Phase 3: Query Optimization
- [ ] Implement `get_movements_by_archetype`
- [ ] Implement `get_low_spinal_load_movements`
- [ ] Implement `get_knee_dominant_movements`
- [ ] Implement `get_hypertrophy_friendly_movements`
- [ ] Implement `get_tier_weighted_movements`

### Phase 4: Safety-First Substitution
- [ ] Implement `MovementSubstitutionService`
- [ ] Implement `_calculate_safety_score`
- [ ] Implement `find_safest_substitution`
- [ ] Implement `get_tiered_alternatives`
- [ ] Write unit tests for substitution logic

### Phase 5: API Updates
- [ ] Update `create_movement` route
- [ ] Add `filter_movements_by_biomechanics` route
- [ ] Update movement detail route to include biomechanics data
- [ ] Update movement update route

---

## Testing Strategy

### Unit Tests
```python
# tests/test_biomechanics_profile.py

def test_biomechanics_profile_validator_valid():
    """Test valid biomechanics profile."""
    profile = {
        "archetype": "bilateral_compound",
        "movement_vectors": {
            "primary": "sagittal",
            "secondary": ["frontal"]
        },
        "joint_involvement": {
            "knee": 8.0,
            "hip": 7.0,
            "lumbar": 5.0
        },
        "loading_pattern": {
            "type": "axial",
            "spinal_load": "high"
        },
        "stability_demands": {
            "balance": 4.0,
            "coordination": 3.0,
            "core_engagement": 6.0
        },
        "range_of_motion": {
            "flexion": "full",
            "extension": "full"
        },
        "temporal_factors": {
            "eccentric_emphasis": True,
            "isometric_hold": False,
            "explosive_component": False
        }
    }
    
    validator = BiomechanicsProfileValidator(**profile)
    assert validator.archetype == "bilateral_compound"

def test_biomechanics_profile_validator_invalid_archetype():
    """Test invalid archetype raises validation error."""
    profile = {
        "archetype": "invalid_archetype",
        # ... minimal required fields
    }
    
    with pytest.raises(ValueError, match="Invalid archetype"):
        BiomechanicsProfileValidator(**profile)
```

### Integration Tests
```python
# tests/test_movement_substitution.py

async def test_find_safest_substitution_low_spinal_load():
    """Test substitution with low spinal load tolerance."""
    # Create movements with different spinal loads
    squat = Movement(
        name="Barbell Back Squat",
        pattern=MovementPattern.SQUAT,
        biomechanics_profile={
            "loading_pattern": {"spinal_load": "high"}
        }
    )
    
    goblet_squat = Movement(
        name="Goblet Squat",
        pattern=MovementPattern.SQUAT,
        biomechanics_profile={
            "loading_pattern": {"spinal_load": "low"}
        }
    )
    
    # Test substitution
    service = MovementSubstitutionService()
    safest = await service.find_safest_substitution(
        db,
        squat,
        user_spinal_tolerance="low"
    )
    
    assert safest == goblet_squat
```

---

## Performance Considerations

### Index Strategy
1. **GIN Index**: Essential for JSONB containment queries
   - `biomechanics_profile` GIN index
   - Use for: `@>` operator, key existence checks

2. **Expression Indexes**: For specific JSONB paths
   - `archetype` BTREE index
   - `spinal_load` BTREE index
   - `knee_involvement` BTREE index

3. **Tier/Metabolic Demand**: Already indexed
   - Use existing indexes for filtering

### Query Optimization Tips
1. Always use expression indexes for frequently accessed JSONB paths
2. Consider materialized views for complex biomechanics queries
3. Use `jsonb_path_query` for complex JSONB path queries
4. Cache biomechanics profile lookups in Redis for high-frequency access

---

## Rollback Plan

If issues arise during migration:

1. **Schema Changes**: Revert Pydantic schema updates
2. **Database Indexes**: Use Alembic downgrade to remove indexes
3. **API Routes**: Revert to original movement endpoints
4. **Service Logic**: Keep substitution service but disable via feature flag

---

## Next Steps

1. Review and approve this design document
2. Create feature branch for implementation
3. Implement Phase 1 (Schema Enhancement)
4. Implement Phase 2 (Database Migration)
5. Implement Phase 3 (Query Optimization)
6. Implement Phase 4 (Safety-First Substitution)
7. Implement Phase 5 (API Updates)
8. Write comprehensive tests
9. Performance testing and optimization
10. Documentation updates
