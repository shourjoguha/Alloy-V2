# Gainsly Database System Overview

This document describes the database schema for Gainsly in detail:

- All core tables and relationships
- All enum types and **all of their allowed values**
- All categorical fields (including columns that store enum values as strings)
- Notes about JSON blobs and free‑text categorical fields

> Important: Some columns are “categorical” in practice but not enforced by the database (e.g. free‑text strings, tags). For those, this document describes the intended category space, but the **actual distinct values** depend on data in your running database.

---

## 1. Technology & Connection

- **Database engine:** PostgreSQL (via SQLAlchemy async engine)
- **Connection URL (app):**  
  `postgresql+asyncpg://gainsly:gainslypass@localhost:5432/gainslydb`
- **Connection URL (tools / psql / GUI):**  
  `postgresql://gainsly:gainslypass@localhost:5432/gainslydb`
- **ORM base:** `app.db.database.Base`  
- **Migrations:** Alembic (`/alembic`)

All tables described below are created via Alembic migrations plus `Base.metadata`.

---

## 2. Global Enums (Authoritative Categorical Spaces)

Defined in [app/models/enums.py](file:///Users/shourjosmac/Documents/Gainsly/app/models/enums.py).

### 2.0 How Enums Are Stored (Important)

Gainsly uses SQLAlchemy `Enum(MyPythonEnum)` for many columns. In the current migrations, those enums are materialized with **the Python enum member names** (typically UPPERCASE) as the allowed database values (example: `HARD_NO`, `PRIVATE`, `SQUAT`). Application code often uses `enum_member.value` (typically lowercase) for prompts and UI.

This section lists **both**:
- **DB values**: what is actually stored/allowed in enum-typed DB columns
- **Semantic values**: the Python `.value` strings used in business logic and prompts

### 2.1 MovementPattern

Used to classify movement patterns.

- Stored as **string** in `movements.pattern` (not DB-enforced; intended to match semantic values).
- Stored as **SQL enum** in `top_set_logs.pattern` and `pattern_exposures.pattern` (DB-enforced).

DB values (enforced in SQL enum columns):
- `SQUAT`
- `HINGE`
- `HORIZONTAL_PUSH`
- `VERTICAL_PUSH`
- `HORIZONTAL_PULL`
- `VERTICAL_PULL`
- `CARRY`
- `CORE`
- `LUNGE`
- `ROTATION`
- `PLYOMETRIC`
- `OLYMPIC`
- `ISOLATION`
- `MOBILITY`
- `ISOMETRIC`
- `CONDITIONING`
- `CARDIO`

Semantic values (Python `.value`, used in prompts/UI):
- `squat`
- `hinge`
- `horizontal_push`
- `vertical_push`
- `horizontal_pull`
- `vertical_pull`
- `carry`
- `core`
- `lunge`
- `rotation`
- `plyometric`
- `olympic`
- `isolation`
- `mobility`
- `isometric`
- `conditioning`
- `cardio`

### 2.2 PrimaryRegion

Body region emphasis:

- `anterior lower`
- `posterior lower`
- `shoulder`
- `anterior upper`
- `posterior upper`
- `full body`
- `lower body`
- `upper body`

### 2.3 PrimaryMuscle

Primary muscular focus:

- `quadriceps`
- `hamstrings`
- `glutes`
- `calves`
- `chest`
- `lats`
- `upper_back`
- `rear_delts`
- `front_delts`
- `side_delts`
- `biceps`
- `triceps`
- `forearms`
- `core`
- `obliques`
- `lower_back`
- `hip_flexors`
- `adductors`
- `full_body`

### 2.4 MetricType

Measurement units for movements:

- `reps`
- `time`
- `time_under_tension`
- `distance`

### 2.5 SkillLevel

Movement skill / complexity:

- `beginner`
- `intermediate`
- `advanced`
- `expert`
- `elite`

### 2.6 CNSLoad

Central nervous system demand:

- `very_low`
- `low`
- `moderate`
- `high`
- `very_high`

### 2.7 Goal

Program goal categories:

DB values:
- `STRENGTH`
- `HYPERTROPHY`
- `ENDURANCE`
- `FAT_LOSS`
- `MOBILITY`
- `EXPLOSIVENESS`
- `SPEED`

Semantic values:
- `strength`
- `hypertrophy`
- `endurance`
- `fat_loss`
- `mobility`
- `explosiveness`
- `speed`

### 2.8 SplitTemplate

Program split styles:

DB values:
- `UPPER_LOWER`
- `PPL` (Push/Pull/Legs)
- `FULL_BODY`
- `HYBRID` (user-customizable)

Semantic values:
- `upper_lower`
- `ppl`
- `full_body`
- `hybrid`

### 2.9 ProgressionStyle

Progression methodology:

DB values:
- `SINGLE_PROGRESSION`
- `DOUBLE_PROGRESSION`
- `PAUSED_VARIATIONS`
- `BUILD_TO_DROP`
- `WAVE_LOADING`

Semantic values:
- `single_progression`
- `double_progression`
- `paused_variations`
- `build_to_drop`
- `wave_loading`

### 2.10 MovementRuleType

User movement preference rules:

DB values:
- `HARD_NO` — never include
- `HARD_YES` — must appear at least once per microcycle
- `PREFERRED` — must appear at least once every 2 weeks

Semantic values:
- `hard_no`
- `hard_yes`
- `preferred`

### 2.11 RuleCadence

Cadence of movement rules:

DB values:
- `PER_MICROCYCLE`
- `WEEKLY`
- `BIWEEKLY`

Semantic values:
- `per_microcycle`
- `weekly`
- `biweekly`

### 2.12 EnjoyableActivity

Enjoyable non‑gym activities:

DB values:
- `TENNIS`
- `BOULDERING`
- `CYCLING`
- `SWIMMING`
- `HIKING`
- `BASKETBALL`
- `FOOTBALL`
- `YOGA`
- `MARTIAL_ARTS`
- `DANCE`
- `OTHER`

Semantic values:
- `tennis`
- `bouldering`
- `cycling`
- `swimming`
- `hiking`
- `basketball`
- `football`
- `yoga`
- `martial_arts`
- `dance`
- `other`

### 2.13 SessionType

Types of training sessions:

DB values:
- `UPPER`
- `LOWER`
- `PUSH`
- `PULL`
- `LEGS`
- `FULL_BODY`
- `CARDIO`
- `MOBILITY`
- `RECOVERY`
- `SKILL`
- `CUSTOM`

Semantic values:
- `upper`
- `lower`
- `push`
- `pull`
- `legs`
- `full_body`
- `cardio`
- `mobility`
- `recovery`
- `skill`
- `custom`

### 2.14 ExerciseRole

Exercise roles within a session:

DB values:
- `WARMUP`
- `MAIN`
- `ACCESSORY`
- `SKILL`
- `FINISHER`
- `COOLDOWN`

Semantic values:
- `warmup`
- `main`
- `accessory`
- `skill`
- `finisher`
- `cooldown`

### 2.15 MicrocycleStatus

Microcycle lifecycle status:

DB values:
- `PLANNED`
- `ACTIVE`
- `COMPLETE`

Semantic values:
- `planned`
- `active`
- `complete`

### 2.16 E1RMFormula

Estimated 1RM calculation formulas:

DB values:
- `EPLEY`
- `BRZYCKI`
- `LOMBARDI`
- `OCONNER`

Semantic values:
- `epley`
- `brzycki`
- `lombardi`
- `oconner`

### 2.17 RecoverySource

Source of recovery data:

DB values:
- `DUMMY`
- `MANUAL`
- `GARMIN`
- `APPLE`
- `AURA_RING`
- `WHOOP_BAND`

Semantic values:
- `dummy`
- `manual`
- `garmin`
- `apple`
- `aura ring`
- `whoop band`

### 2.18 PersonaTone

Coach persona / tone:

DB values:
- `DRILL_SERGEANT`
- `SUPPORTIVE`
- `ANALYTICAL`
- `MOTIVATIONAL`
- `MINIMALIST`

Semantic values:
- `drill_sergeant`
- `supportive`
- `analytical`
- `motivational`
- `minimalist`

### 2.19 RelationshipType

Movement relationship types:

- `progression`
- `regression`
- `variation`
- `antagonist`
- `prep`

### 2.20 CircuitType

Circuit structure types:

DB values:
- `ROUNDS_FOR_TIME`
- `AMRAP`
- `EMOM`
- `LADDER`
- `TABATA`
- `CHIPPER`
- `STATION`

Semantic values:
- `rounds_for_time`
- `amrap`
- `emom`
- `ladder`
- `tabata`
- `chipper`
- `station`

### 2.21 StressBucket

Stress normalization buckets:

- `strength`
- `conditioning`
- `impact_upper`
- `impact_lower`
- `cns`

### 2.22 PersonaAggression

Programming aggressiveness (stored as integer SQL enum):

DB values:
- `CONSERVATIVE` (semantic value: `1`)
- `MODERATE_CONSERVATIVE` (semantic value: `2`)
- `BALANCED` (semantic value: `3`)
- `MODERATE_AGGRESSIVE` (semantic value: `4`)
- `AGGRESSIVE` (semantic value: `5`)

### 2.23 ExperienceLevel

User experience level:

DB values:
- `BEGINNER`
- `INTERMEDIATE`
- `ADVANCED`
- `EXPERT`

Semantic values:
- `beginner`
- `intermediate`
- `advanced`
- `expert`

### 2.24 Visibility

Content visibility:

DB values:
- `PRIVATE`
- `FRIENDS`
- `PUBLIC`

Semantic values:
- `private`
- `friends`
- `public`

### 2.25 GoalType

Types of long-term goals:

DB values:
- `BODY_COMPOSITION`
- `STRENGTH_1RM`
- `ENDURANCE_EVENT`
- `HABIT_CONSISTENCY`
- `SKILL_ACQUISITION`

### 2.26 DisciplineCategory

Categories of disciplines:

DB values:
- `TRAINING`
- `SPORTS`
- `OUTDOOR`
- `WELLNESS`

### 2.27 ActivityCategory

Categories of activities:

DB values:
- `WORKOUT`
- `SPORT`
- `OUTDOOR`
- `WELLNESS`

### 2.28 ActivitySource

Source of activity data:

DB values:
- `PLANNED`
- `MANUAL`
- `IMPORTED`

---

## 3. Tables and Categorical Columns

This section goes table by table, listing:

- Columns
- Types
- Primary and foreign keys
- Categorical fields and which enum/value sets they use

### 3.1 users

Model: [User](file:///Users/shourjosmac/Documents/Gainsly/app/models/user.py)

- **PK**
  - `id` (Integer, primary key, autoincrement)
- **Identity**
  - `name` (String(100), nullable)
  - `email` (String(255), nullable, unique)
- **Categorical**
  - `experience_level` (SQLEnum(ExperienceLevel), not null, default `INTERMEDIATE`)
    - DB values: `BEGINNER`, `INTERMEDIATE`, `ADVANCED`, `EXPERT`
    - Semantic values: `beginner`, `intermediate`, `advanced`, `expert`
  - `persona_tone` (SQLEnum(PersonaTone), not null, default `SUPPORTIVE`)
    - DB values: `DRILL_SERGEANT`, `SUPPORTIVE`, `ANALYTICAL`, `MOTIVATIONAL`, `MINIMALIST`
    - Semantic values: `drill_sergeant`, `supportive`, `analytical`, `motivational`, `minimalist`
  - `persona_aggression` (SQLEnum(PersonaAggression), not null, default `BALANCED`)
    - DB values: `CONSERVATIVE`, `MODERATE_CONSERVATIVE`, `BALANCED`, `MODERATE_AGGRESSIVE`, `AGGRESSIVE`
    - Semantic values: `1`, `2`, `3`, `4`, `5`
- **Relationships**
  - `movement_rules` → `user_movement_rules`
  - `enjoyable_activities` → `user_enjoyable_activities`
  - `programs` → `programs`
  - `workout_logs` → `workout_logs`
  - `soreness_logs` → `soreness_logs`
  - `recovery_signals` → `recovery_signals`
  - `settings` → `user_settings` (1:1)
  - `conversation_threads` → `conversation_threads`
  - `macro_cycles` → `macro_cycles`
  - `goals` → `goals`
  - `activity_instances` → `activity_instances`

### 3.2 user_settings

Model: `UserSettings` (same file)

- **PK**
  - `id` (Integer, autoincrement)
- **FK**
  - `user_id` (Integer, FK → users.id, unique)
- **Categorical**
  - `active_e1rm_formula` (SQLEnum(E1RMFormula), not null, default `EPLEY`)
    - DB values: `EPLEY`, `BRZYCKI`, `LOMBARDI`, `OCONNER`
    - Semantic values: `epley`, `brzycki`, `lombardi`, `oconner`
- **Other**
  - `use_metric` (Boolean, default True) — `True` = kg, `False` = lbs

### 3.3 user_movement_rules

Model: `UserMovementRule`

- **PK**
  - `id`
- **FK**
  - `user_id` (FK → users.id, indexed)
  - `movement_id` (FK → movements.id, indexed)
- **Categorical**
  - `rule_type` (SQLEnum(MovementRuleType), not null)
    - DB values: `HARD_NO`, `HARD_YES`, `PREFERRED`
    - Semantic values: `hard_no`, `hard_yes`, `preferred`
  - `cadence` (SQLEnum(RuleCadence), not null, default `per_microcycle`)
    - DB values: `PER_MICROCYCLE`, `WEEKLY`, `BIWEEKLY`
    - Semantic values: `per_microcycle`, `weekly`, `biweekly`
- **Other**
  - `notes` (Text, nullable)

### 3.4 user_enjoyable_activities

Model: `UserEnjoyableActivity`

- **PK**
  - `id`
- **FK**
  - `user_id` (FK → users.id, indexed)
- **Categorical**
  - `activity_type` (SQLEnum(EnjoyableActivity), not null)
    - DB values: `TENNIS`, `BOULDERING`, `CYCLING`, `SWIMMING`, `HIKING`, `BASKETBALL`, `FOOTBALL`, `YOGA`, `MARTIAL_ARTS`, `DANCE`, `OTHER`
    - Semantic values: `tennis`, `bouldering`, `cycling`, `swimming`, `hiking`, `basketball`, `football`, `yoga`, `martial_arts`, `dance`, `other`
- **Other**
  - `custom_name` (String(100), nullable)
  - `recommend_every_days` (Integer, not null, default 28)
  - `enabled` (Boolean, default True)
  - `notes` (Text, nullable)

---

### 3.5 programs

Model: [Program](file:///Users/shourjosmac/Documents/Gainsly/app/models/program.py)

- **PK**
  - `id`
- **FK**
  - `user_id` (FK → users.id, not null, indexed)
  - `macro_cycle_id` (FK → macro_cycles.id, nullable, indexed)
- **Identity**
  - `name` (String(100), nullable) — label for historic programs/templates
- **Duration**
  - `start_date` (Date, not null)
  - `duration_weeks` (Integer, not null)
    - Constraint: `8 <= duration_weeks <= 12`
- **Goals (categorical)**
  - `goal_1`, `goal_2`, `goal_3` (SQLEnum(Goal), not null)
    - DB values: `STRENGTH`, `HYPERTROPHY`, `ENDURANCE`, `FAT_LOSS`, `MOBILITY`, `EXPLOSIVENESS`, `SPEED`
    - Semantic values: `strength`, `hypertrophy`, `endurance`, `fat_loss`, `mobility`, `explosiveness`, `speed`
  - `goal_weight_1`, `goal_weight_2`, `goal_weight_3` (Integer, not null)
    - Constraints:
      - Sum to 10: `goal_weight_1 + goal_weight_2 + goal_weight_3 = 10`
      - Each non‑negative: `>= 0`
- **Program structure**
  - `split_template` (SQLEnum(SplitTemplate), not null)
    - DB values: `UPPER_LOWER`, `PPL`, `FULL_BODY`, `HYBRID`
    - Semantic values: `upper_lower`, `ppl`, `full_body`, `hybrid`
  - `days_per_week` (Integer, not null) — expected 2–7 (not enforced by constraint)
  - `progression_style` (SQLEnum(ProgressionStyle), not null)
    - DB values: `SINGLE_PROGRESSION`, `DOUBLE_PROGRESSION`, `PAUSED_VARIATIONS`, `BUILD_TO_DROP`, `WAVE_LOADING`
    - Semantic values: `single_progression`, `double_progression`, `paused_variations`, `build_to_drop`, `wave_loading`
  - `hybrid_definition` (JSON, nullable)  
    - Arbitrary structure describing a custom split.
  - `disciplines_json` (JSON, nullable)  
    - Expected shape: list of `{ "discipline": <str>, "weight": <int> }`.
- **Deload**
  - `deload_every_n_microcycles` (Integer, not null, default 4)
- **Persona snapshot (categorical)**
  - `persona_tone` (SQLEnum(PersonaTone), not null)
  - `persona_aggression` (SQLEnum(PersonaAggression), not null)
- **Status / visibility**
  - `is_active` (Boolean, default True)
  - `is_template` (Boolean, default False)
  - `visibility` (SQLEnum(Visibility), not null, default `private`)
    - DB values: `PRIVATE`, `FRIENDS`, `PUBLIC`
    - Semantic values: `private`, `friends`, `public`
  - `created_at` (DateTime, default now)
- **Relationships**
  - `user` → User
  - `macro_cycle` → MacroCycle
  - `microcycles` → Microcycle (cascade delete)
  - `goals` → UserGoal (cascade delete)

---

### 3.6 microcycles

Model: `Microcycle`

- **PK**
  - `id`
- **FK**
  - `program_id` (FK → programs.id, not null, indexed)
- **Timing**
  - `start_date` (Date, not null)
  - `length_days` (Integer, not null, constraint `7 <= length_days <= 10`)
  - `sequence_number` (Integer, not null) — 1,2,3...
- **Categorical**
  - `status` (SQLEnum(MicrocycleStatus), not null, default `planned`)
    - DB values: `PLANNED`, `ACTIVE`, `COMPLETE`
    - Semantic values: `planned`, `active`, `complete`
  - `is_deload` (Boolean, default False)
- **Relationships**
  - `program` → Program
  - `sessions` → Session (cascade delete)
  - `pattern_exposures` → PatternExposure (cascade delete)

---

### 3.7 sessions

Model: `Session`

- **PK**
  - `id`
- **FK**
  - `microcycle_id` (FK → microcycles.id, not null, indexed)
  - `main_circuit_id` (FK → circuit_templates.id, nullable)
  - `finisher_circuit_id` (FK → circuit_templates.id, nullable)
- **Scheduling**
  - `date` (Date, not null, indexed)
  - `day_number` (Integer, not null) — 1–10 within microcycle
- **Categorical**
  - `session_type` (SQLEnum(SessionType), not null)
    - Values: `upper`, `lower`, `push`, `pull`, `legs`, `full_body`, `cardio`, `mobility`, `recovery`, `skill`, `custom`
- **Intent tags**
  - `intent_tags` (JSON, default list)  
    - Typical values: strings like `"strength"`, `"hypertrophy"`, etc.  
    - This is an open categorical space; actual distinct values depend on your data.
- **Session content (JSON sections)**
  - `warmup_json` (JSON, nullable)
  - `main_json` (JSON, nullable)
  - `accessory_json` (JSON, nullable)
  - `finisher_json` (JSON, nullable)
  - `cooldown_json` (JSON, nullable)
  - These are arrays of exercise objects; structure is application‑level and not enforced by DB.
- **Source-of-truth note**
  - The LLM session generator currently produces these JSON sections directly (see `SESSION_PLAN_SCHEMA`), while `session_exercises` is a parallel normalized representation. If `session_exercises` is not kept in sync with the JSON sections, any logic reading from `session_exercises` will not reflect what the user sees in the session plan.
- **Time estimation**
  - `estimated_duration_minutes` (Integer, nullable)
  - `warmup_duration_minutes`, `main_duration_minutes`, `accessory_duration_minutes`, `finisher_duration_minutes`, `cooldown_duration_minutes` (Integer, nullable)
- **Coach reasoning**
  - `coach_notes` (Text, nullable)
- **Relationships**
  - `microcycle` → Microcycle
  - `exercises` → SessionExercise
  - `workout_logs` → WorkoutLog
  - `main_circuit`, `finisher_circuit` → CircuitTemplate

---

### 3.8 session_exercises

Model: `SessionExercise`

- **PK**
  - `id`
- **FK**
  - `session_id` (FK → sessions.id, not null, indexed)
  - `movement_id` (FK → movements.id, not null, indexed)
  - `user_id` (FK → users.id, nullable, indexed)
- **Categorical**
  - `role` (SQLEnum(ExerciseRole), not null)
    - Values: `warmup`, `main`, `accessory`, `skill`, `finisher`, `cooldown`
- **Ordering / grouping**
  - `order_in_session` (Integer, not null)
  - `superset_group` (Integer, nullable) — same number indicates supersets.
- **Prescription**
  - `target_sets` (Integer, not null)
  - `target_rep_range_min` (Integer, nullable)
  - `target_rep_range_max` (Integer, nullable)
  - `target_rpe` (Float, nullable)
  - `target_rir` (Integer, nullable)
  - `target_duration_seconds` (Integer, nullable)
- **Rest**
  - `default_rest_seconds` (Integer, nullable)
- **Flags**
  - `is_complex_lift` (Boolean, default False)
  - `substitution_allowed` (Boolean, default True)
- **Notes**
  - `notes` (Text, nullable)

---

### 3.9 movements

Model: [Movement](file:///Users/shourjosmac/Documents/Gainsly/app/models/movement.py)

> Note: This table stores enum values as **string columns**, not SQL enum types. The intended value sets come from the enums above.

- **PK**
  - `id`
- **FK**
  - `user_id` (FK → users.id, nullable, indexed)  
    - `NULL` = system movement (global)
    - `Non-null` = user‑defined movement
- **Identity**
  - `name` (String(200), not null, unique, indexed)
- **Categorical / classification**
  - `pattern` (String(50), not null, indexed)
    - Intended values: **MovementPattern** enum values
  - `block_type` (String(50), not null, default `"All"`, indexed)
    - Intended values: `"mobility"`, `"olympic"`, `"Explosiveness"`, `"Endurance"`, `"Fat Loss"`, `"All"`
  - `primary_muscle` (String(50), not null, indexed)
    - Intended values: **PrimaryMuscle** enum values
  - `primary_region` (String(50), not null, indexed)
    - Intended values: **PrimaryRegion** enum values
  - `secondary_muscles` (JSON, default list)
    - Array of strings, each intended to be a **PrimaryMuscle** value
- **Load and complexity**
  - `cns_load` (String(50), not null, default `"moderate"`)
    - Intended values: **CNSLoad** enum values
  - `skill_level` (String(50), not null, default `"intermediate"`)
    - Intended values: **SkillLevel** enum values
- **Movement characteristics**
  - `compound` (Boolean, default True)
  - `is_complex_lift` (Boolean, default False)
  - `is_unilateral` (Boolean, default False)
- **Measurement**
  - `metric_type` (String(50), not null, default `"reps"`)
    - Intended values: **MetricType** enum values
- **Additional categorization**
  - `primary_discipline` (String(50), not null, default `"All"`)
    - Open categorical; typical values: `"All"`, `"powerlifting"`, `"crossfit"`, etc.
  - `discipline_tags` (JSON, default list)
    - Example values: `"powerlifting"`, `"olympic"`, `"calisthenics"`, `"crossfit"`
  - `equipment_tags` (JSON, default list)
    - Example values: `"barbell"`, `"dumbbell"`, `"bodyweight"`, `"kettlebell"`
  - `tags` (JSON, default list)
    - General tags like `"crossfit"`, `"athletic"`, `"mobility"`
- **Description**
  - `description` (Text, nullable)
  - `coaching_cues` (JSON, default list) — array of strings.
- **Substitution helper**
  - `substitution_group` (String(100), nullable, indexed)  
    - Example: `"single_arm_row"` grouping similar movements.
- **Relationships**
  - `user_rules` → UserMovementRule
  - `session_exercises` → SessionExercise
  - `top_set_logs` → TopSetLog
  - `outgoing_relationships` / `incoming_relationships` → MovementRelationship

---

### 3.10 movement_relationships

Model: `MovementRelationship`

- **PK**
  - `id`
- **FK**
  - `source_movement_id` (FK → movements.id, not null, indexed)
  - `target_movement_id` (FK → movements.id, not null, indexed)
- **Categorical**
  - `relationship_type` (String(50), not null, indexed)
    - Intended values: **RelationshipType**
- **Other**
  - `notes` (Text, nullable)

---

### 3.11 circuit_templates

Model: [CircuitTemplate](file:///Users/shourjosmac/Documents/Gainsly/app/models/circuit.py)

- **PK**
  - `id`
- **Identity**
  - `name` (String(200), not null, indexed)
  - `description` (Text, nullable)
- **Categorical**
  - `circuit_type` (SQLEnum(CircuitType), not null)
    - Values: `rounds_for_time`, `amrap`, `emom`, `ladder`, `tabata`, `chipper`, `station`
  - `difficulty_level` (String(50), nullable)
    - Values: `beginner`, `intermediate`, `advanced`, `elite`
- **Content**
  - `rounds` (Integer, nullable)
  - `time_cap_seconds` (Integer, nullable)
  - `movements_json` (JSON, nullable)
    - Array of objects defining the circuit's movements.
- **Relationships**
  - `main_sessions` → Session (as main_circuit)
  - `finisher_sessions` → Session (as finisher_circuit)

---

### 3.12 macro_cycles

Model: `MacroCycle`

- **PK**
  - `id`
- **FK**
  - `user_id` (FK → users.id, not null, indexed)
- **Identity & Timing**
  - `name` (String(200), nullable)
  - `start_date` (Date, not null)
  - `end_date` (Date, not null)
  - `created_at` (DateTime, default now)
- **Relationships**
  - `user` → User
  - `programs` → Program
  - `goals` → UserGoal

---

### 3.13 goals

Model: `UserGoal`

- **PK**
  - `id`
- **FK**
  - `user_id` (FK → users.id, not null, indexed)
  - `macro_cycle_id` (FK → macro_cycles.id, nullable, indexed)
  - `program_id` (FK → programs.id, nullable, indexed)
- **Goal Definition**
  - `goal_type` (SQLEnum(GoalType), nullable=False)
  - `target_json` (JSON, nullable=True) — Stores target values (e.g., target weight, reps)
  - `priority` (Integer, nullable=False, default=3)
  - `status` (SQLEnum(GoalStatus), nullable=False, default=ACTIVE)
- **Timing**
  - `effective_from` (DateTime, nullable=False)
  - `effective_to` (DateTime, nullable=True)
- **Relationships**
  - `user` → User
  - `macro_cycle` → MacroCycle
  - `program` → Program
  - `checkins` → GoalCheckin

---

### 3.14 disciplines

Model: `Discipline`

- **PK**
  - `id`
- **Identity**
  - `slug` (String(100), not null, unique, indexed)
  - `name` (String(200), not null)
  - `category` (SQLEnum(DisciplineCategory), nullable=False)
- **Relationships**
  - Referenced by `activity_definitions`

---

### 3.15 activity_definitions

Model: `ActivityDefinition`

- **PK**
  - `id`
- **Identity**
  - `name` (String(200), not null, index=True)
  - `category` (SQLEnum(ActivityCategory), nullable=False, index=True)
- **FK**
  - `discipline_id` (FK → disciplines.id, nullable=True, index=True)
- **Defaults**
  - `default_metric_type` (SQLEnum(MetricType), nullable=True)
  - `default_equipment_tags` (JSON, nullable=True)
- **Relationships**
  - `discipline` → Discipline
  - `activity_instances` → ActivityInstance
  - `muscle_map` → ActivityMuscleMap

---

### 3.16 activity_instances

Model: `ActivityInstance`

- **PK**
  - `id`
- **FK**
  - `user_id` (FK → users.id, not null, index=True)
  - `planned_session_id` (FK → sessions.id, nullable=True, index=True)
  - `activity_definition_id` (FK → activity_definitions.id, nullable=True, index=True)
- **Source**
  - `source` (SQLEnum(ActivitySource), nullable=False, index=True)
- **Timing**
  - `performed_start` (DateTime, nullable=True, index=True)
  - `performed_end` (DateTime, nullable=True)
  - `duration_seconds` (Integer, nullable=True)
- **Feedback**
  - `notes` (Text, nullable=True)
  - `perceived_difficulty` (Integer, nullable=True)
  - `enjoyment_rating` (Integer, nullable=True)
  - `visibility` (SQLEnum(Visibility), default=PRIVATE)
- **Relationships**
  - `user` → User
  - `activity_definition` → ActivityDefinition
  - `session` → Session (via planned_session_id)


## 4. Debug & Troubleshooting

### 4.1 Schema Mismatch / Missing Columns Error

**Symptoms:**
- Frontend fails to load lists (movements, sessions, circuits) with `500 Internal Server Error`.
- Backend logs show `NameError: name 'user_id' is not defined` or `ProgrammingError: column "user_id" does not exist`.
- "High Level Disjointment": Multiple independent features fail simultaneously.

**Context:**
Recent feature updates for Custom Workout Logging required adding ownership tracking (`user_id`) and metric columns to core tables (`sessions`, `movements`). If the Python models are updated but the database schema is not migrated, queries will fail when trying to select these new columns.

**Affected Tables & Columns:**
1.  **movements**:
    - Missing `user_id` (Integer, FK)
2.  **sessions**:
    - Missing `user_id` (Integer, FK)
    - Missing `total_stimulus`, `total_fatigue`, `cns_fatigue` (Float)
    - Missing `muscle_volume_json` (JSON)
3.  **session_exercises**:
    - Missing `user_id` (Integer, FK)

**Resolution:**
Use the schema patch script or run raw SQL to manually add the missing columns if migrations fail.

```sql
-- PostgreSQL Patch
ALTER TABLE movements ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS total_stimulus FLOAT DEFAULT 0.0;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS total_fatigue FLOAT DEFAULT 0.0;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS cns_fatigue FLOAT DEFAULT 0.0;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS muscle_volume_json JSON DEFAULT '{}';
ALTER TABLE session_exercises ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
```

**Verification:**
Run `scripts/diagnose_system.py` (if available) or check endpoint health:
- `GET /settings/movements`
- `GET /circuits`
- `GET /programs`
