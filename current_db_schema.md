# Gainsly Database System Documentation

This document describes the database schema for Gainsly in detail. It serves as the single source of truth for the database architecture, including all core tables, relationships, and enum types.

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

### 2.0 How Enums Are Stored
Gainsly uses SQLAlchemy `Enum(MyPythonEnum)` for many columns. These are materialized as PostgreSQL ENUM types. The database stores the **semantic values** (typically lowercase strings) directly.

### 2.1 MovementPattern
Used to classify movement patterns.
**Allowed Values:**
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
Body region emphasis.
**Allowed Values:**
- `anterior lower`
- `posterior lower`
- `shoulder`
- `anterior upper`
- `posterior upper`
- `full body`
- `lower body`
- `upper body`

### 2.3 PrimaryMuscle
Primary muscular focus.
**Allowed Values:**
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
Measurement units for movements.
**Allowed Values:**
- `reps`
- `time`
- `time_under_tension`
- `distance`

### 2.5 SkillLevel
Movement skill / complexity.
**Allowed Values:**
- `beginner`
- `intermediate`
- `advanced`
- `expert`
- `elite`

### 2.6 CNSLoad
Central nervous system demand.
**Allowed Values:**
- `very_low`
- `low`
- `moderate`
- `high`
- `very_high`

### 2.7 Goal
Program goal categories.
**Allowed Values:**
- `strength`
- `hypertrophy`
- `endurance`
- `fat_loss`
- `mobility`
- `explosiveness`
- `speed`

### 2.8 SplitTemplate
Program split styles.
**Allowed Values:**
- `upper_lower`
- `ppl` (Push/Pull/Legs)
- `full_body`
- `hybrid` (user-customizable)

### 2.9 ProgressionStyle
Progression methodology.
**Allowed Values:**
- `single_progression`
- `double_progression`
- `paused_variations`
- `build_to_drop`
- `wave_loading`

### 2.10 MovementRuleType
User movement preference rules.
**Allowed Values:**
- `hard_no` — never include
- `hard_yes` — must appear at least once per microcycle
- `preferred` — must appear at least once every 2 weeks

### 2.11 RuleCadence
Cadence of movement rules.
**Allowed Values:**
- `per_microcycle`
- `weekly`
- `biweekly`

### 2.12 EnjoyableActivity
Enjoyable non‑gym activities.
**Allowed Values:**
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
Types of training sessions.
**Allowed Values:**
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
Exercise roles within a session.
**Allowed Values:**
- `warmup`
- `main`
- `accessory`
- `skill`
- `finisher`
- `cooldown`

### 2.15 MicrocycleStatus
Microcycle lifecycle status.
**Allowed Values:**
- `planned`
- `active`
- `complete`

### 2.16 E1RMFormula
Estimated 1RM calculation formulas.
**Allowed Values:**
- `epley`
- `brzycki`
- `lombardi`
- `oconner`

### 2.17 RecoverySource
Source of recovery data.
**Allowed Values:**
- `dummy`
- `manual`
- `garmin`
- `apple`
- `aura ring`
- `whoop band`

### 2.18 PersonaTone
Coach persona / tone.
**Allowed Values:**
- `drill_sergeant`
- `supportive`
- `analytical`
- `motivational`
- `minimalist`

### 2.19 RelationshipType
Movement relationship types.
**Allowed Values:**
- `progression`
- `regression`
- `variation`
- `antagonist`
- `prep`

### 2.20 CircuitType
Circuit structure types.
**Allowed Values:**
- `rounds_for_time`
- `amrap`
- `emom`
- `ladder`
- `tabata`
- `chipper`
- `station`

### 2.21 PersonaAggression
Programming aggressiveness (stored as integer SQL enum).
**Allowed Values:**
- `1` (CONSERVATIVE)
- `2` (MODERATE_CONSERVATIVE)
- `3` (BALANCED)
- `4` (MODERATE_AGGRESSIVE)
- `5` (AGGRESSIVE)

### 2.22 ExperienceLevel
User experience level.
**Allowed Values:**
- `beginner`
- `intermediate`
- `advanced`
- `expert`

### 2.23 Visibility
Content visibility.
**Allowed Values:**
- `private`
- `friends`
- `public`

### 2.24 GoalType
Types of long-term goals.
**Allowed Values:**
- `body_composition`
- `strength_1rm`
- `endurance_event`
- `habit_consistency`
- `skill_acquisition`

---

## 3. Table Schema

## TABLE 1: users

**Data Operations:**
- User creation (INSERT)
- User retrieval for authentication (SELECT by email/username)
- User profile updates (UPDATE)
- User deletion with cascade (DELETE)

**Table Relevance:**
Core user account table storing authentication credentials, basic user information, and global experience settings.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- email (String(255), unique, index=True): User email for authentication - OPTIMAL
- name (String(100), nullable): Display name - OPTIMAL
- experience_level (SQLEnum(ExperienceLevel)): User's general experience level - OPTIMAL
- persona_tone (SQLEnum(PersonaTone)): AI coach tone preference - OPTIMAL
- persona_aggression (SQLEnum(PersonaAggression)): AI coach aggression level - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed core user table. Includes Enums for experience levels and persona settings, ensuring type safety.

---

## TABLE 2: user_profiles

**Data Operations:**
- Profile creation (INSERT)
- Profile retrieval for display (SELECT by user_id)
- Profile updates (UPDATE)
- Profile deletion with cascade (DELETE)

**Table Relevance:**
Stores extended user information including physical stats and JSON-based preferences for flexibility.

**Field Structure and Datatypes:**
- user_id (Integer, ForeignKey, primary_key): References users table - OPTIMAL
- date_of_birth (Date, nullable): DOB - OPTIMAL
- sex (SQLEnum(Sex), nullable): Biological sex - OPTIMAL
- height_cm (Integer, nullable): Height in cm - OPTIMAL
- discipline_preferences (JSON, nullable): Map of discipline to preference score - OPTIMAL
- discipline_experience (JSON, nullable): Map of discipline to experience level - OPTIMAL
- scheduling_preferences (JSON, nullable): Flexible scheduling rules - OPTIMAL
- long_term_goal_category (String(50), nullable): Goal category - OPTIMAL
- long_term_goal_description (Text, nullable): Detailed goal description - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Refactored to use JSON for complex/variable preferences (`discipline_preferences`, `scheduling_preferences`) while keeping core stats relational. `sex` is now an Enum.

---

## TABLE 3: user_settings

**Data Operations:**
- Settings creation (INSERT)
- Settings retrieval (SELECT by user_id)
- Settings updates (UPDATE)
- Settings deletion with cascade (DELETE)

**Table Relevance:**
Stores technical user preferences like unit systems and calculation formulas.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, unique): References users table - OPTIMAL
- active_e1rm_formula (SQLEnum(E1RMFormula)): Preferred 1RM formula (e.g., Epley) - OPTIMAL
- use_metric (Boolean, default=True): Unit preference (True=kg, False=lbs) - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Streamlined to focus on functional settings. Uses Enums for formulas and Boolean for units.

---

## TABLE 4: user_movement_rules

**Data Operations:**
- Rule creation (INSERT)
- Rule retrieval for session generation (SELECT by user_id)
- Rule updates (UPDATE)
- Rule deletion with cascade (DELETE)

**Table Relevance:**
Stores user-specific movement preferences, restrictions, and rules used by the constraint solver during session generation.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- movement_id (Integer, ForeignKey, nullable, index=True): References movements table - OPTIMAL
- rule_type (SQLEnum(MovementRuleType), nullable): Rule type (e.g., INCLUDE, EXCLUDE) - OPTIMAL
- rule_operator (SQLEnum(RuleOperator), nullable): Comparison operator (e.g., EQ, GT) - OPTIMAL
- cadence (SQLEnum(RuleCadence), nullable): Frequency of rule application - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Uses SQLEnums for rule logic (`rule_type`, `rule_operator`, `cadence`), ensuring type safety and clear constraints.

---

## TABLE 5: user_enjoyable_activities

**Data Operations:**
- Activity creation (INSERT)
- Activity retrieval for session generation (SELECT by user_id)
- Activity updates (UPDATE)
- Activity deletion with cascade (DELETE)

**Table Relevance:**
Stores user-preferred movements/activities used by the constraint solver to increase engagement during session generation.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- movement_id (Integer, ForeignKey, nullable, index=True): References movements table - OPTIMAL
- enjoyment_score (Float, nullable, default=0.5): User preference score (0.0-1.0) - OPTIMAL
- notes (Text, nullable): Additional context - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
GOOD. Well-structured table with proper foreign key relationships. The enjoyment_score field should have a CheckConstraint for range validation (0.0-1.0). Composite index on (user_id, enjoyment_score DESC) would improve queries for sorting by preference. The design effectively supports preference-based session generation.

---

## TABLE 6: programs

**Data Operations:**
- Program creation (INSERT)
- Program retrieval for display (SELECT by user_id and status)
- Program updates (UPDATE)
- Program deletion with cascade (DELETE)

**Table Relevance:**
Stores training programs (8-12 weeks) with ten-dollar method goal weights, serving as the primary organizational unit for workout planning.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- macro_cycle_id (Integer, ForeignKey, nullable, index=True): References macro_cycles table - OPTIMAL
- name (String(100), nullable): Program name - OPTIMAL
- start_date (Date, nullable): Program start date - OPTIMAL
- duration_weeks (Integer, nullable): Program duration - OPTIMAL
- goal_1 (SQLEnum(Goal), nullable): Primary goal - OPTIMAL
- goal_2 (SQLEnum(Goal), nullable): Secondary goal - OPTIMAL
- goal_3 (SQLEnum(Goal), nullable): Tertiary goal - OPTIMAL
- goal_weight_1 (Integer, nullable): Goal 1 weight - OPTIMAL
- goal_weight_2 (Integer, nullable): Goal 2 weight - OPTIMAL
- goal_weight_3 (Integer, nullable): Goal 3 weight - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper use of SQLEnum for goals and CheckConstraints for ten-dollar method validation. The design effectively enforces goal weight sum = 10 and positive weights. Composite index on (user_id, start_date) would improve queries for active programs. The architecture supports microcycle-based program planning with goal prioritization.

---

## TABLE 7: program_goals

**Data Operations:**
- Program goal creation (INSERT)
- Program goal retrieval (SELECT by program_id)
- Program goal updates (UPDATE)
- Program goal deletion with cascade (DELETE)

**Table Relevance:**
Stores goal-specific targets for programs, providing structured goal tracking.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- program_id (Integer, ForeignKey, nullable, index=True): References programs table - OPTIMAL
- goal_type (SQLEnum(Goal), nullable): Goal type - OPTIMAL
- target_value (Float, nullable): Target value - OPTIMAL
- current_value (Float, nullable): Current value - OPTIMAL
- unit (String(50), nullable): Unit of measurement - OPTIMAL
- achieved (Boolean, default=False): Achievement status - OPTIMAL
- achieved_at (Date, nullable): Achievement date - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper use of SQLEnum for goal_type. The achieved flag and achieved_at field support goal completion tracking. Composite index on (program_id, achieved) would improve queries for tracking program progress. The design effectively supports structured goal tracking with measurable targets.

---

## TABLE 8: microcycles

**Data Operations:**
- Microcycle creation (INSERT)
- Microcycle retrieval for session generation (SELECT by program_id)
- Microcycle updates (UPDATE)
- Microcycle deletion with cascade (DELETE)

**Table Relevance:**
Stores microcycles (1-4 weeks) within programs, with deload support and progression tracking.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- program_id (Integer, ForeignKey, nullable, index=True): References programs table - OPTIMAL
- week_number (Integer, nullable): Week number within program - OPTIMAL
- microcycle_type (SQLEnum(MicrocycleType), nullable): Microcycle type - OPTIMAL
- intensity_percent (Float, nullable): Intensity percentage - OPTIMAL
- volume_percent (Float, nullable): Volume percentage - OPTIMAL
- deload_week (Boolean, default=False): Deload flag - OPTIMAL
- notes (Text, nullable): Additional context - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper use of SQLEnum for microcycle_type. The deload_week flag supports structured deload weeks. Composite index on (program_id, week_number) would improve queries for program timeline navigation. The design effectively supports microcycle-based periodization with intensity and volume modulation.

---

## TABLE 9: sessions

**Data Operations:**
- Session creation during program generation (INSERT)
- Session retrieval for display (SELECT by user_id and date)
- Session updates via adaptation (UPDATE)
- Session deletion with cascade (DELETE)

**Table Relevance:**
Stores workout sessions, serving as the primary workout container. Exercise details are normalized in `session_exercises`.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- program_id (Integer, ForeignKey, nullable, index=True): References programs table - OPTIMAL
- microcycle_id (Integer, ForeignKey, nullable, index=True): References microcycles table - OPTIMAL
- day_number (Integer, nullable): Day number within microcycle (1-14) - OPTIMAL
- date (Date, nullable, index=True): Scheduled workout date - OPTIMAL
- session_type (SQLEnum(SessionType), nullable): Session type - OPTIMAL
- intent_tags (JSON, default=list): Tags for session focus - OPTIMAL
- main_circuit_id (Integer, ForeignKey, nullable): For Crossfit/Hyrox sessions - OPTIMAL
- finisher_circuit_id (Integer, ForeignKey, nullable): Optional finisher circuit - OPTIMAL
- estimated_duration_minutes (Integer, nullable): Estimated duration - OPTIMAL
- coach_notes (Text, nullable): Coach reasoning/instructions - OPTIMAL
- total_stimulus (Float): Actual stimulus load - OPTIMAL
- total_fatigue (Float): Actual fatigue load - OPTIMAL
- cns_fatigue (Float): CNS fatigue impact - OPTIMAL
- muscle_volume_json (JSON): Aggregated muscle volume stats - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Normalized design. JSON blobs (warmup_json, etc.) have been removed in favor of the `session_exercises` relationship, ensuring a single source of truth.

---

## TABLE 10: session_exercises

**Data Operations:**
- Session exercise creation (INSERT)
- Session exercise retrieval for display (SELECT by session_id)
- Session exercise updates via adaptation (UPDATE)
- Session exercise deletion with cascade (DELETE)

**Table Relevance:**
Stores individual exercises within sessions relationally. This is the SINGLE SOURCE OF TRUTH for session content.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- session_id (Integer, ForeignKey, nullable, index=True): References sessions table - OPTIMAL
- movement_id (Integer, ForeignKey, nullable, index=True): References movements table - OPTIMAL
- session_section (SQLEnum(SessionSection), nullable=False): WARMUP, MAIN, ACCESSORY, FINISHER, etc. - OPTIMAL
- circuit_id (Integer, ForeignKey, nullable, index=True): References circuit_templates - OPTIMAL
- role (SQLEnum(ExerciseRole)): Role of the exercise - OPTIMAL
- order_in_session (Integer, nullable=False): Exercise order - OPTIMAL
- superset_group (Integer, nullable=True): Grouping for supersets - OPTIMAL
- target_sets (Integer, nullable=False): Number of sets - OPTIMAL
- target_rep_range_min/max (Integer): Rep range targets - OPTIMAL
- target_rpe (Float, nullable): Target RPE - OPTIMAL
- target_rir (Integer, nullable): Target RIR - OPTIMAL
- target_duration_seconds (Integer, nullable): For time-based exercises - OPTIMAL
- default_rest_seconds (Integer, nullable): Rest time - OPTIMAL
- notes (Text, nullable): Instructions - OPTIMAL
- stimulus/fatigue (Float): Per-exercise metrics - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Fully normalized. Includes sectioning (`session_section`) and detailed prescription fields (`target_rpe`, `target_rir`).

---

## TABLE 11: movements

**Data Operations:**
- Movement creation (INSERT)
- Movement retrieval for session generation (SELECT)
- Movement updates (UPDATE)
- Movement deletion with cascade (DELETE)

**Table Relevance:**
Reference table for exercise movements. Acts as the central node in the knowledge graph.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- name (String(200), nullable, unique, index=True): Movement name - OPTIMAL
- pattern (SQLEnum(MovementPattern)): Fundamental movement pattern - OPTIMAL
- block_type (String): Derived from pattern - OPTIMAL
- primary_muscle (SQLEnum(PrimaryMuscle)): Main muscle worked - OPTIMAL
- primary_region (SQLEnum(PrimaryRegion)): Body region - OPTIMAL
- cns_load (SQLEnum(CNSLoad)): CNS fatigue impact - OPTIMAL
- skill_level (SQLEnum(SkillLevel)): Required skill - OPTIMAL
- spinal_compression (SQLEnum(SpinalCompression)): Injury risk metric - OPTIMAL
- metric_type (SQLEnum(MetricType)): Default tracking metric (reps, time, etc.) - OPTIMAL
- fatigue_factor (Float): Systemic fatigue cost - OPTIMAL
- stimulus_factor (Float): Hypertrophy stimulus - OPTIMAL
- injury_risk_factor (Float): Base injury risk - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Highly structured and normalized. String tags/categories have been replaced with Enums and junction tables (`movement_disciplines`, `movement_equipment`, `movement_tags`, `movement_muscle_map`).

---

## TABLE 12: movement_relationships

**Data Operations:**
- Relationship creation (INSERT)
- Relationship retrieval for interference checking (SELECT)
- Relationship updates (UPDATE)
- Relationship deletion with cascade (DELETE)

**Table Relevance:**
Stores interference relationships between movements (e.g., squat and deadlift on same day), used by the interference detection logic.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- movement_1_id (Integer, ForeignKey, nullable, index=True): First movement - OPTIMAL
- movement_2_id (Integer, ForeignKey, nullable, index=True): Second movement - OPTIMAL
- relationship_type (SQLEnum(RelationshipType), nullable): Relationship type - OPTIMAL
- severity (Float, default=0.5): Interference severity - OPTIMAL
- notes (Text, nullable): Additional context - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper use of SQLEnum for relationship_type. The design effectively models movement interference patterns for the constraint solver. Composite unique constraint on (movement_1_id, movement_2_id, relationship_type) would prevent duplicate relationships. Composite index on (movement_1_id, relationship_type) would improve queries for interference checking during session generation.

---

## TABLE 13: movement_muscle_map

**Data Operations:**
- Mapping creation (INSERT)
- Mapping retrieval for muscle-level analysis (SELECT)
- Mapping updates (UPDATE)
- Mapping deletion with cascade (DELETE)

**Table Relevance:**
Many-to-many relationship between movements and muscles with magnitude information, used for muscle-level volume and fatigue calculations.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- movement_id (Integer, ForeignKey, nullable, index=True): References movements table - OPTIMAL
- muscle_id (Integer, ForeignKey, nullable, index=True): References muscles table - OPTIMAL
- role (SQLEnum(MuscleRole), nullable): Muscle role - OPTIMAL
- magnitude (Float, default=1.0): Muscle involvement magnitude - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed junction table with proper use of SQLEnum for role type. The design effectively supports muscle-level fatigue calculations with role-based differentiation. Composite index on (movement_id, muscle_id) would improve query performance. The design properly normalizes movement-muscle relationships.

---

## TABLE 14: muscles

**Data Operations:**
- Muscle creation (INSERT)
- Muscle retrieval for categorization (SELECT)
- Muscle updates (UPDATE)

**Table Relevance:**
Reference table for muscle groups used in movement mapping and fatigue calculations.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- name (String(100), nullable, unique, index=True): Muscle name - OPTIMAL
- body_region (String(50), nullable): Body region - OPTIMAL
- description (Text, nullable): Muscle description - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Simple reference table with proper indexing and unique constraint. Well-suited for muscle-level fatigue calculations and movement categorization. Composite index on (body_region, name) would improve queries for region-specific muscle grouping.

---

## TABLE 15: user_skills

**Data Operations:**
- Skill creation (INSERT)
- Skill retrieval for personalization (SELECT by user_id)
- Skill updates (UPDATE)
- Skill deletion with cascade (DELETE)

**Table Relevance:**
Stores user skill levels across disciplines, used for difficulty-appropriate exercise selection during session generation.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- discipline_id (Integer, ForeignKey, nullable, index=True): References disciplines table - OPTIMAL
- skill_level (SQLEnum(SkillLevel), nullable): Skill level - OPTIMAL
- interest_level (Integer, CheckConstraint(0-10)): User interest level - OPTIMAL
- experience_years (Float, nullable): Years of experience - OPTIMAL
- notes (Text, nullable): Additional context - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Composite Constraints:**
- UniqueConstraint(user_id, discipline_id): Ensures only one skill entry per user per discipline.

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper use of SQLEnum for skill_level and CheckConstraint for interest_level. The design effectively supports skill-based exercise difficulty selection.

---

## TABLE 16: user_injuries

**Data Operations:**
- Injury creation (INSERT)
- Injury retrieval for adaptation (SELECT by user_id)
- Injury updates (UPDATE)
- Injury deletion with cascade (DELETE)

**Table Relevance:**
Stores user injuries with severity ratings, used by the adaptation logic to avoid contraindicated movements.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- body_part (String(50), nullable, index=True): Injured body part - SUBOPTIMAL, should be FK to muscles
- severity (Float, default=1.0): Injury severity - OPTIMAL
- description (String(255), nullable): Injury description - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Optimality Assessment:**
MIXED. Well-designed table with proper foreign key relationship. The body_part field uses String instead of foreign key to muscles table, losing referential integrity. The severity field should have a CheckConstraint for range validation (0.0-1.0). Composite index on (user_id, severity DESC) would improve queries for prioritizing high-severity injuries during adaptation.

---

## TABLE 17: workout_logs

**Data Operations:**
- Workout log creation (INSERT)
- Workout log retrieval for history (SELECT by user_id and date)
- Workout log updates (UPDATE)
- Workout log deletion with cascade (DELETE)

**Table Relevance:**
Stores completed workout records with actual performance data, used for progress tracking and analysis.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- session_id (Integer, ForeignKey, nullable, index=True): References sessions table - OPTIMAL
- workout_date (Date, nullable, index=True): Workout date - OPTIMAL for time-series analysis
- duration_seconds (Integer, nullable): Actual duration - OPTIMAL
- perceived_effort (Integer, nullable): Perceived effort (1-10) - OPTIMAL
- mood_before (Integer, nullable): Pre-workout mood - OPTIMAL
- mood_after (Integer, nullable): Post-workout mood - OPTIMAL
- notes (Text, nullable): Additional context - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper foreign key relationships. The perceived_effort field should have a CheckConstraint for range validation (1-10). Composite index on (user_id, workout_date) would significantly improve time-series queries for progress tracking. The design effectively supports workout history analysis with mood tracking.

---

## TABLE 18: top_set_logs

**Data Operations:**
- Top set log creation (INSERT)
- Top set log retrieval for PR tracking (SELECT by user_id and movement_id)
- Top set log updates (UPDATE)
- Top set log deletion with cascade (DELETE)

**Table Relevance:**
Stores top set records with detailed performance metrics, used for progressive overload tracking and strength analysis.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- session_id (Integer, ForeignKey, nullable, index=True): References sessions table - OPTIMAL
- movement_id (Integer, ForeignKey, nullable, index=True): References movements table - OPTIMAL
- set_number (Integer, nullable): Set number - OPTIMAL
- reps (Integer, nullable): Number of reps - OPTIMAL
- load_kg (Float, nullable): Weight lifted - OPTIMAL
- rpe (Float, nullable): Perceived exertion - OPTIMAL
- velocity (Float, nullable): Bar velocity (m/s) - OPTIMAL
- notes (Text, nullable): Additional context - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper foreign key relationships and detailed performance metrics. Composite unique constraint on (session_id, movement_id, set_number) would prevent duplicate entries. Composite index on (user_id, movement_id, created_at DESC) would improve queries for PR tracking. The design effectively supports progressive overload analysis with velocity tracking.

---

## TABLE 19: pattern_exposure

**Data Operations:**
- Pattern exposure creation (INSERT)
- Pattern exposure retrieval for adaptation (SELECT by user_id and pattern)
- Pattern exposure updates (UPDATE)
- Pattern exposure deletion with cascade (DELETE)

**Table Relevance:**
Stores movement pattern exposure history, used by the adaptation logic to prevent overuse and promote variety.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- pattern_type (SQLEnum(MovementPattern), nullable): Movement pattern - OPTIMAL
- exposure_count (Integer, default=0): Exposure count - OPTIMAL
- last_exposure_date (Date, nullable): Last exposure date - OPTIMAL
- consecutive_exposures (Integer, default=0): Consecutive exposure count - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper use of SQLEnum for pattern_type. The design effectively supports pattern-based variety tracking. Composite unique constraint on (user_id, pattern_type) would prevent duplicate entries. Composite index on (user_id, last_exposure_date) would improve queries for recent exposure analysis.

---

## TABLE 20: soreness_logs

**Data Operations:**
- Soreness log creation (INSERT)
- Soreness log retrieval for recovery analysis (SELECT by user_id and date)
- Soreness log updates (UPDATE)
- Soreness log deletion with cascade (DELETE)

**Table Relevance:**
Stores daily soreness ratings, used for recovery signal calculation and fatigue management.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- log_date (Date, nullable, index=True): Soreness log date - OPTIMAL for time-series analysis
- body_part (String(50), nullable): Affected body part - OPTIMAL
- severity (Integer, nullable): Soreness severity (1-10) - OPTIMAL
- notes (Text, nullable): Additional context - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper foreign key relationship. The severity field should have a CheckConstraint for range validation (1-10). Composite index on (user_id, log_date, body_part) would improve queries for time-series soreness analysis. The design effectively supports recovery signal calculation with body-part specific tracking.

---

## TABLE 21: recovery_signals

**Data Operations:**
- Recovery signal creation (INSERT)
- Recovery signal retrieval for adaptation (SELECT by user_id and date)
- Recovery signal updates (UPDATE)
- Recovery signal deletion with cascade (DELETE)

**Table Relevance:**
Stores aggregated recovery metrics derived from soreness, sleep, and biometric data, used for session adaptation.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- signal_date (Date, nullable, index=True): Recovery signal date - OPTIMAL for time-series analysis
- overall_recovery_score (Float, default=100.0): Overall recovery (0-100) - OPTIMAL, needs CheckConstraint
- muscle_recovery_json (JSON, default=dict): Muscle-level recovery - ACCEPTABLE for nested data
- sleep_quality_score (Float, default=0.0): Sleep quality - OPTIMAL
- soreness_score (Float, default=0.0): Soreness score - OPTIMAL
- hrv_score (Float, nullable): HRV score - OPTIMAL
- resting_heart_rate (Float, nullable): Resting heart rate - OPTIMAL
- readiness_score (Float, default=0.0): Readiness score - OPTIMAL, needs CheckConstraint
- notes (Text, nullable): Additional context - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper foreign key relationship. The JSON field for muscle-level recovery is appropriate given the variable nature of muscle-specific data. Composite index on (user_id, signal_date) would improve time-series queries. The overall_recovery_score and readiness_score fields should have CheckConstraints for range validation (0-100). The design effectively supports multi-factor recovery analysis.

---

## TABLE 22: user_biometrics_history

**Data Operations:**
- Biometric record creation (INSERT)
- Biometric record retrieval for trend analysis (SELECT by user_id and date)
- Biometric record updates (UPDATE)
- Biometric record deletion with cascade (DELETE)

**Table Relevance:**
Stores historical biometric measurements for tracking body composition and health metrics over time.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- measurement_date (Date, nullable, index=True): Measurement date - OPTIMAL for time-series analysis
- weight_kg (Float, nullable): Body weight - OPTIMAL
- body_fat_percentage (Float, nullable): Body fat percentage - OPTIMAL
- lean_mass_kg (Float, nullable): Lean mass - OPTIMAL
- fat_mass_kg (Float, nullable): Fat mass - OPTIMAL
- waist_cm (Float, nullable): Waist circumference - OPTIMAL
- chest_cm (Float, nullable): Chest circumference - OPTIMAL
- hips_cm (Float, nullable): Hip circumference - OPTIMAL
- notes (Text, nullable): Additional context - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper foreign key relationship. Composite index on (user_id, measurement_date) would improve time-series queries for body composition tracking. The design effectively supports comprehensive biometric tracking for goal progress measurement.

---

## TABLE 23: activity_definitions

**Data Operations:**
- Activity definition creation (INSERT)
- Activity definition retrieval for session generation (SELECT)
- Activity definition updates (UPDATE)
- Activity definition deletion with cascade (DELETE)

**Table Relevance:**
Reference table defining activity types (movements, circuits, rest) used in session generation with stress metrics.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- name (String(100), nullable, unique, index=True): Activity name - OPTIMAL
- activity_type (SQLEnum(ActivityType), nullable): Activity type - OPTIMAL
- discipline_id (Integer, ForeignKey, nullable, index=True): References disciplines table - OPTIMAL
- description (Text, nullable): Activity description - OPTIMAL
- default_duration_seconds (Integer, nullable): Default duration - OPTIMAL
- default_intensity (Float, nullable): Default intensity - OPTIMAL
- stress_points (Float, default=1.0): Stress contribution - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed reference table with proper use of SQLEnum for activity_type. The stress_points field enables workload quantification. Composite index on (activity_type, discipline_id) would improve queries for activity selection. The design effectively supports flexible session generation with stress-based load management.

---

## TABLE 24: activity_instances

**Data Operations:**
- Activity instance creation (INSERT)
- Activity instance retrieval for session display (SELECT by session_id)
- Activity instance updates (UPDATE)
- Activity instance deletion with cascade (DELETE)

**Table Relevance:**
Stores concrete activity instances within sessions with actual performance data, serving as the primary activity tracking table.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- session_id (Integer, ForeignKey, nullable, index=True): References sessions table - OPTIMAL
- activity_definition_id (Integer, ForeignKey, nullable, index=True): References activity_definitions table - OPTIMAL
- position (Integer, nullable): Activity order - OPTIMAL
- actual_duration_seconds (Integer, nullable): Actual duration - OPTIMAL
- actual_intensity (Float, nullable): Actual intensity - OPTIMAL
- completed (Boolean, default=False): Completion status - OPTIMAL
- completed_at (DateTime, nullable): Completion timestamp - OPTIMAL
- notes (Text, nullable): Additional context - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper foreign key relationships. The completed flag and completed_at field support activity completion tracking. Composite index on (session_id, position) would improve queries for ordered activity display. The design effectively provides flexible activity tracking with performance data.

---

## TABLE 25: goals

**Data Operations:**
- Goal creation during program setup (INSERT)
- Goal retrieval for program display (SELECT)
- Goal updates during program modification (UPDATE)
- Goal deletion with cascade (DELETE)

**Table Relevance:**
Reference table for standard fitness goals used in program configuration. Note: This table appears to be a reference lookup rather than storing user-specific goal selections (those are stored in the program table with ten-dollar method weights).

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- name (String(100), nullable): Goal name - OPTIMAL
- description (Text, nullable): Goal description - OPTIMAL
- default_weight (Integer, default=1): Default weight for ten-dollar method - OPTIMAL

**Optimality Assessment:**
GOOD. Simple reference table with basic goal information. The default_weight field provides sensible defaults for the ten-dollar method. However, this table may be redundant given that the program table stores goal selections with weights. Consider whether this table is actively used or if goal definitions could be defined purely as enum values.

---

## TABLE 26: goal_checkins

**Data Operations:**
- Checkin creation (INSERT)
- Checkin retrieval for progress tracking (SELECT by date and user_id)
- Checkin updates (UPDATE)
- Checkin deletion with cascade (DELETE)

**Table Relevance:**
Stores periodic checkins for tracking progress toward program goals over time.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- program_id (Integer, ForeignKey, nullable, index=True): References programs table - OPTIMAL
- checkin_date (Date, nullable, index=True): Checkin date - OPTIMAL for time-series analysis
- goal_id (Integer, ForeignKey, nullable, index=True): References goals table - OPTIMAL
- current_value (Float, nullable): Current metric value - OPTIMAL
- target_value (Float, nullable): Target value - OPTIMAL
- notes (Text, nullable): User notes - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Optimality Assessment:**
GOOD. Well-structured table with proper foreign key relationships and indexing. Composite index on (user_id, program_id, checkin_date) would significantly improve time-series queries for program progress tracking. The design allows for tracking progress toward multiple goals within a single program.

---

## TABLE 27: disciplines

**Data Operations:**
- Discipline creation (INSERT)
- Discipline retrieval for categorization (SELECT)
- Discipline updates (UPDATE)

**Table Relevance:**
Reference table for training disciplines used in activity definitions and user skill tracking.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- name (String(100), nullable, unique, index=True): Discipline name - OPTIMAL
- description (Text, nullable): Discipline description - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Simple reference table with proper indexing and unique constraint. Well-suited for categorizing activities and tracking user skills across disciplines.

---

## TABLE 28: activity_muscle_map

**Data Operations:**
- Mapping creation (INSERT)
- Mapping retrieval for muscle-level analysis (SELECT)
- Mapping updates (UPDATE)
- Mapping deletion with cascade (DELETE)

**Table Relevance:**
Many-to-many relationship between activity instances and muscles with magnitude information, used for muscle-level volume and fatigue calculations.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- activity_instance_id (Integer, ForeignKey, nullable, index=True): References activity_instances table - OPTIMAL
- muscle_id (Integer, ForeignKey, nullable, index=True): References muscles table - OPTIMAL
- role (SQLEnum(MuscleRole), nullable): Muscle role - OPTIMAL
- magnitude (Float, default=1.0): Muscle involvement magnitude - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed junction table with proper use of SQLEnum for role type. Consistent design with movement_muscle_map table. Composite index on (activity_instance_id, muscle_id) would improve query performance.

---

## TABLE 29: user_fatigue_state

**Data Operations:**
- Fatigue state creation (INSERT)
- Fatigue state retrieval for adaptation logic (SELECT by date and user_id)
- Fatigue state updates (UPDATE)
- Fatigue state deletion with cascade (DELETE)

**Table Relevance:**
Stores daily fatigue state calculations derived from completed sessions and recovery signals, used for session adaptation.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- date (Date, nullable, index=True): Fatigue state date - OPTIMAL for time-series analysis
- muscle_fatigue_json (JSON, default=dict): Muscle-level fatigue - ACCEPTABLE for nested data
- systemic_fatigue (Float, default=0.0): Overall fatigue - OPTIMAL
- cns_fatigue (Float, default=0.0): CNS fatigue - OPTIMAL
- recovery_score (Float, default=100.0): Recovery percentage (0-100) - OPTIMAL, needs CheckConstraint
- notes (Text, nullable): Additional context - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Optimality Assessment:**
GOOD. Well-structured table with proper indexing. The JSON field for muscle-level fatigue is appropriate given the variable nature of muscle-specific data. Composite index on (user_id, date) would improve time-series queries. The recovery_score field should have a CheckConstraint for range validation (0-100).

---

## TABLE 30: activity_instance_links

**Data Operations:**
- Link creation (INSERT)
- Link retrieval for activity relationship tracking (SELECT)
- Link updates (UPDATE)
- Link deletion with cascade (DELETE)

**Table Relevance:**
Stores relationships between activity instances (e.g., warmup linked to main workout), used for comprehensive activity tracking.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- source_activity_instance_id (Integer, ForeignKey, nullable, index=True): Source activity - OPTIMAL
- target_activity_instance_id (Integer, ForeignKey, nullable, index=True): Target activity - OPTIMAL
- link_type (SQLEnum(ActivityLinkType), nullable): Link relationship type - OPTIMAL
- notes (Text, nullable): Additional context - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed junction table with proper use of SQLEnum for link_type. The design allows for flexible activity relationship modeling (e.g., warmup-main, accessory-main). Composite index on (source_activity_instance_id, link_type) would improve query performance.

---

## TABLE 31: circuit_templates

**Data Operations:**
- Circuit template creation (INSERT)
- Circuit template retrieval for session generation (SELECT with type filtering)
- Circuit template updates (UPDATE)
- Circuit template deletion with cascade (DELETE)

**Table Relevance:**
Stores CrossFit-style circuit templates used as finishers or main circuits in sessions, with fitness function metrics for constraint solving.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- name (String(200), nullable, index=True): Circuit name - OPTIMAL
- description (Text, nullable): Circuit description - OPTIMAL
- circuit_type (SQLEnum(CircuitType), nullable): Circuit type (AMRAP, EMOM, etc.) - OPTIMAL
- exercises_json (JSON, default=list): Exercise definitions - ACCEPTABLE for flexible circuit structure
- default_rounds (Integer, nullable): Number of rounds - OPTIMAL
- default_duration_seconds (Integer, nullable): Time duration - OPTIMAL
- bucket_stress (JSON, default=dict): Bucket-level stress values - ACCEPTABLE for dynamic stress mapping
- tags (JSON, default=list): Circuit tags - ACCEPTABLE for flexible categorization
- difficulty_tier (Integer, default=1): Difficulty level - OPTIMAL
- fatigue_factor (Float, default=1.0): Fitness function metric - OPTIMAL
- stimulus_factor (Float, default=1.0): Fitness function metric - OPTIMAL
- min_recovery_hours (Integer, default=24): Recovery time - OPTIMAL

**Optimality Assessment:**
GOOD. Well-designed table with appropriate use of JSON for flexible circuit data. The fitness function metrics (fatigue_factor, stimulus_factor) are consistent with the movement model design. The bucket_stress JSON field allows for dynamic stress mapping across different movement buckets. The exercises_json field provides flexibility for complex circuit structures that would be difficult to model relationally.

---

## TABLE 32: heuristic_configs

**Data Operations:**
- Configuration creation (INSERT)
- Configuration retrieval for behavior customization (SELECT)
- Configuration updates (UPDATE)

**Table Relevance:**
Stores system heuristics and configuration values used for algorithm behavior customization without code changes.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- key (String(255), nullable, unique, index=True): Configuration key - OPTIMAL
- value (Text, nullable): Configuration value - OPTIMAL
- description (Text, nullable): Configuration description - OPTIMAL
- category (String(100), nullable, index=True): Configuration category - OPTIMAL
- data_type (String(50), nullable): Expected data type - SUBOPTIMAL, should be SQLEnum
- is_active (Boolean, default=True): Active status - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
GOOD. Well-designed configuration table with proper indexing and unique constraint on key. The data_type field as String loses type safety and should be an enum. Composite index on (category, is_active) would improve queries for active configurations by category. The design effectively allows runtime customization of algorithm behavior without code deployment.

---

## TABLE 33: conversation_threads

**Data Operations:**
- Conversation thread creation (INSERT)
- Conversation thread retrieval for chat history (SELECT by user_id)
- Conversation thread updates (UPDATE)
- Conversation thread deletion with cascade (DELETE)

**Table Relevance:**
Stores conversation threads for the AI coach chat interface, organizing multi-turn conversations.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- title (String(255), nullable): Conversation title - OPTIMAL
- context_type (SQLEnum(ContextType), nullable, index=True): Conversation context - OPTIMAL
- context_id (Integer, nullable, index=True): Related entity ID - OPTIMAL for linking to programs/sessions
- is_active (Boolean, default=True): Active status - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper indexing and use of SQLEnum for context_type. The context_type/context_id combination allows flexible linkage to different entities (programs, sessions, etc.). Composite index on (user_id, is_active) would improve queries for active conversations.

---

## TABLE 34: conversation_turns

**Data Operations:**
- Conversation turn creation (INSERT)
- Conversation turn retrieval for chat display (SELECT with thread filtering)
- Conversation turn updates (UPDATE)
- Conversation turn deletion with cascade (DELETE)

**Table Relevance:**
Stores individual turns within conversation threads, representing user messages and AI responses.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- thread_id (Integer, ForeignKey, nullable, index=True): References conversation_threads table - OPTIMAL
- role (SQLEnum(ConversationRole), nullable): Speaker role (user/assistant) - OPTIMAL
- content (Text, nullable): Message content - OPTIMAL
- metadata_json (JSON, default=dict): Additional metadata - ACCEPTABLE for flexible data
- tokens_used (Integer, nullable): Token count for cost tracking - OPTIMAL
- model_used (String(100), nullable): LLM model used - OPTIMAL
- created_at (DateTime): Timestamp - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table with proper indexing and use of SQLEnum for role. The tokens_used field enables cost tracking for cloud LLM usage. Composite index on (thread_id, created_at) would improve queries for chronologically ordered conversation history.

---

## TABLE 35: external_provider_accounts

**Data Operations:**
- Provider account creation (INSERT)
- Provider account retrieval for data ingestion (SELECT by user_id and provider)
- Provider account updates (UPDATE for token refresh)
- Provider account deletion with cascade (DELETE)

**Table Relevance:**
Stores user authentication credentials for external data providers (Garmin, Strava, etc.) used for automated data ingestion.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- provider_type (SQLEnum(ProviderType), nullable, index=True): Provider type - OPTIMAL
- provider_user_id (String(255), nullable): Provider's user ID - OPTIMAL
- access_token (Text, nullable): OAuth access token - OPTIMAL
- refresh_token (Text, nullable): OAuth refresh token - OPTIMAL
- token_expires_at (DateTime, nullable): Token expiration - OPTIMAL
- is_active (Boolean, default=True): Active status - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table for OAuth credential management. Proper token expiration tracking enables automatic refresh workflows. Composite index on (user_id, provider_type, is_active) would improve queries for active provider accounts. The design effectively supports OAuth 2.0 flows for multiple providers.

---

## TABLE 36: external_ingestion_runs

**Data Operations:**
- Ingestion run creation (INSERT)
- Ingestion run retrieval for audit trails (SELECT by user_id and provider)
- Ingestion run status updates (UPDATE)
- Ingestion run deletion with cascade (DELETE)

**Table Relevance:**
Stores execution records of external data ingestion jobs for audit trails and monitoring.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- provider_account_id (Integer, ForeignKey, nullable, index=True): References external_provider_accounts table - OPTIMAL
- run_type (SQLEnum(IngestionRunType), nullable): Run type (full/incremental) - OPTIMAL
- status (SQLEnum(IngestionStatus), nullable, index=True): Run status - OPTIMAL
- started_at (DateTime, nullable): Run start timestamp - OPTIMAL
- finished_at (DateTime, nullable): Run end timestamp - OPTIMAL
- records_processed (Integer, nullable): Records processed - OPTIMAL
- error_message (Text, nullable): Error details - OPTIMAL
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table for ingestion job tracking. Proper status enum allows for job lifecycle management. Composite index on (user_id, provider_account_id, status) would improve queries for monitoring active/failed jobs. The design provides comprehensive audit trail for external data integration.

---

## TABLE 37: external_activity_records

**Data Operations:**
- Activity record creation during ingestion (INSERT)
- Activity record retrieval for analysis (SELECT by user_id and provider)
- Activity record updates (UPDATE)
- Activity record deletion with cascade (DELETE)

**Table Relevance:**
Stores activity data imported from external providers, serving as raw data for processing into activity_instances.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- ingestion_run_id (Integer, ForeignKey, nullable, index=True): References external_ingestion_runs table - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- provider_activity_id (String(255), nullable): Provider's activity ID - OPTIMAL
- activity_type (String(100), nullable): Activity type - OPTIMAL
- performed_at (DateTime, nullable): Activity timestamp - OPTIMAL for time-series analysis
- raw_data_json (JSON, nullable): Original provider data - ACCEPTABLE for schema flexibility
- processed_to_instance_id (Integer, nullable, index=True): Links to activity_instances table - OPTIMAL for tracking processing status
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table for storing raw external activity data. The raw_data_json field accommodates varying schemas from different providers. The processed_to_instance_id field enables tracking of which records have been processed into activity_instances. Composite index on (user_id, performed_at) would improve time-series queries. Composite unique constraint on (ingestion_run_id, provider_activity_id) would prevent duplicate imports.

---

## TABLE 38: external_metric_streams

**Data Operations:**
- Metric stream creation during ingestion (INSERT)
- Metric stream retrieval for recovery analysis (SELECT by user_id and provider)
- Metric stream updates (UPDATE)
- Metric stream deletion with cascade (DELETE)

**Table Relevance:**
Stores time-series metric data from external providers (HRV, sleep, etc.), serving as raw data for processing into recovery_signals.

**Field Structure and Datatypes:**
- id (Integer, primary_key, autoincrement): Unique identifier - OPTIMAL
- ingestion_run_id (Integer, ForeignKey, nullable, index=True): References external_ingestion_runs table - OPTIMAL
- user_id (Integer, ForeignKey, nullable, index=True): References users table - OPTIMAL
- metric_type (String(100), nullable): Metric type - OPTIMAL
- timestamp (DateTime, nullable): Metric timestamp - OPTIMAL for time-series analysis
- value (Float, nullable): Metric value - OPTIMAL
- unit (String(50), nullable): Measurement unit - OPTIMAL
- raw_data_json (JSON, nullable): Original provider data - ACCEPTABLE for schema flexibility
- processed_to_signal_id (Integer, nullable, index=True): Links to recovery_signals table - OPTIMAL for tracking processing status
- created_at/updated_at (DateTime): Timestamps - OPTIMAL

**Optimality Assessment:**
EXCELLENT. Well-designed table for storing time-series metric data. The raw_data_json field accommodates varying schemas from different providers. The processed_to_signal_id field enables tracking of which records have been processed into recovery_signals. Composite index on (user_id, metric_type, timestamp) would significantly improve time-series queries. Composite unique constraint on (ingestion_run_id, metric_type, timestamp) would prevent duplicate imports. The design effectively handles continuous metric streams from health/wearable devices.
