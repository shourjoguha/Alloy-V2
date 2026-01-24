# Database Schema Evolution for Ensemble Coach Architecture

## Overview

The ability to regress a "Back Squat" to a "Box Squat" (due to fatigue) or progress a "Curtsy Squat" to a "Pistol Squat" (due to skill) is critical for an adaptive coach.

The `MovementRelationship` table already exists in the schema ([app/models/movement.py](file:///Users/shourjosmac/Documents/Gainsly/app/models/movement.py)) and is perfectly structured for this. It supports `relationship_type` (Progression, Regression, Variation).

This plan explicitly leverages the existing `MovementRelationship` table in the "Ensemble Coach" workflow and implements missing pieces.

---

## Finalized Schema Implementation Plan

### 1. The Anatomy Bridge (Optimization Engine)

**Action:** Fully expose `MovementMuscleMap` relationship on `Movement`.

**Benefit:** Enables cumulative load calculation (e.g., "Total Posterior Chain Volume") across disciplines.

### 2. The Internal Fitness Function (Reward Logic)

**Action:** Add RL/Optimization metrics to `Movement`:
- `fatigue_factor` (Float): Systemic cost
- `stimulus_factor` (Float): Growth signal
- `injury_risk_factor` (Float): Base complexity
- `min_recovery_hours` (Int): Recovery decay

### 3. The Skill Matrix (Personalization)

**Action:** Create `UserSkill` table (`user_id`, `discipline_id`, `skill_level`, `experience_years`).

**Benefit:** Replaces simple "Global Experience" with granular, discipline-specific capabilities (e.g., Elite Runner, Beginner Lifter).

### 4. Health & Safety (Guardrails)

**Action:** Create `UserInjury` table (`user_id`, `body_part`, `severity`) instead of a JSON list.

**Benefit:** Allows Optimization Engine to "hard exclude" dangerous movements via fast SQL joins, rather than slow application-side filtering.

### 5. Raw Activity Ingestion (Physics)

**Action:** Add physics columns (`distance`, `watts`, `hr`, `elevation`) to `ExternalActivityRecord`.

**Benefit:** Enables instant "Daily Load" calculation without parsing JSON.

### 6. The Adaptation Logic (Leveraging Existing Structure)

**Strategy:** The system will use the existing `MovementRelationship` table to find substitutes.

**Workflow:** If `UserFatigueState` is high → Query `MovementRelationship` for `REGRESSION` of planned lift.

---

## Implementation Steps

1. Generate Alembic migration for new columns/tables
2. Update ORM models in `app/models/`
3. Implement Optimization Engine integration
4. Add adaptation logic leveraging `MovementRelationship`
5. Update tests to cover new functionality
