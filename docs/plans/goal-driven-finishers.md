# Fix Goal-Driven Finishers and Add Goal-Based Weekly Distribution

## What's happening now (diagnosis)

- Goals/weights are saved correctly (see [ProgramCreate schema](file:///Users/shourjosmac/Documents/Gainsly/app/schemas/program.py#L75-L124) and persistence in [program.py](file:///Users/shourjosmac/Documents/Gainsly/app/services/program.py)).
- Missing finisher occurs when draft generation fails and we fall back to content builders that always return `finisher=None` ([_get_smart_fallback_session_content](file:///Users/shourjosmac/Documents/Gainsly/app/services/session_generator.py#L1329-L1435)).
- Draft generation is currently likely failing due to concrete bugs:
  - invalid `SessionType.CONDITIONING` reference (SessionType lacks CONDITIONING: [enums.py](file:///Users/shourjosmac/Documents/Gainsly/app/models/enums.py#L141-L153))
  - optimizer duration bug in [optimization.py](file:///Users/shourjosmac/Documents/Gainsly/app/services/optimization.py)

---

## Updated Requirements

- Warmup always.
- Middle piece is either:
  - Main lifts + (Accessory XOR Finisher), OR
  - Cardio-only block, OR
  - Conditioning-only block.
- Cooldown always.
- Cardio-only and conditioning-only days must NOT have accessory/finisher.
- Conditioning definition: ≥5 conditioning movements (e.g., sled push/pull, battle ropes) for ≥30 minutes.
- Cardio/conditioning-only day introduced only when:
  1) overtraining risk, OR
  2) beginner safety steering, OR
  3) advanced profile filters allow it.

---

## Plan

### 1) Fix regression so goal-based finishers return

- Replace invalid enum usage and represent conditioning-only sessions using `SessionType.CUSTOM` + intent tag `"conditioning"` (no DB enum migration required).
- Fix optimizer duration calculation so draft generation succeeds.
- Add universal postprocessing so goal-driven finisher injection happens even on fallback paths.

### 2) Enforce session-structure rules globally

- Implement one normalizer function that enforces:
  - Warmup + cooldown always.
  - If cardio-only or conditioning-only session: only that middle piece.
  - Else: main + (accessory XOR finisher), never both.
- Run this normalizer on all generation paths (draft, LLM, fallback).

### 3) Implement conditioning middle-piece generator

- Define conditioning candidates via Movement fields:
  - `Movement.pattern == "conditioning"` and/or `"conditioning"` in Movement.tags.
- Build a conditioning block with ≥5 movements totaling ≥30 minutes (duration-driven prescriptions).

### 4) Add goal-based weekly time distribution (config-driven)

- Create `app/config/activity_distribution.py` with:
  - caps: `mobility_max_pct = 0.30`, `cardio_max_pct = 0.75`, etc.
  - `preference_deviation_pct = 0.15`
  - allocation parameters (how to convert goal weights → weekly minutes → number of dedicated sessions vs finisher minutes)
  - **BIAS TEXT** (transparency): a `BIAS_RATIONALE` structure containing human-readable strings explaining system's intended mapping:
    - fat_loss biases toward metabolic finishers and/or dedicated cardio-only days
    - endurance biases toward dedicated cardio blocks or interval finishers
    - strength/hypertrophy biases toward main+accessory volume
    - mobility biases toward mobility-only sessions and extended warmup/cooldown
  - **BIAS LINKS**: a `HARDCODED_BIAS_LOCATIONS` list of file/function paths where bias is currently hardcoded today, so it's auditable.
- Modify ProgramService weekly structure builder to:
  - compute total weekly minutes
  - allocate bucket minutes proportional to goal weights, clamp to caps
  - decide cardio-only/conditioning-only days *only* when allowed by the 3 rules
  - otherwise allocate cardio/conditioning minutes into lifting-day finishers

### 5) Make session optimization goal-aware + bounded user preference margin

- Update the solver objective to maximize a weighted goal score rather than stimulus-only.
- Apply user favorites/preferred movements as an additive term bounded by `preference_deviation_pct` from the config.

### 6) Remove hardcoded finisher thresholds and make them configurable

- Replace current hardcoded checks like `fat_loss >= 5` in [_build_goal_finisher](file:///Users/shourjosmac/Documents/Gainsly/app/services/session_generator.py#L800-L823) with config-driven thresholds/weights in `app/config/activity_distribution.py`.
- Ensure any remaining implicit thresholds (durations, minimum finisher minutes, etc.) are represented as named variables in that config module.

### 7) Jerome's Notes ≤200 characters

- Enforce a hard 200-character max on `coach_notes` (prompt + post-trim).

### 8) Verification

- Add regression tests:
  - fat_loss=6 yields finisher on lifting days even when draft fails.
  - lifting days never contain both accessory and finisher.
  - cardio-only/conditioning-only days contain only the correct middle piece.
  - weekly planner respects caps and introduces cardio/conditioning days only under the 3 rules.

---

## Key Transparency Deliverable

- The new config module will contain both:
  - variables controlling behavior (caps, thresholds, preference margin), and
  - plain-text bias rationale + explicit paths to any remaining hardcoded bias.
