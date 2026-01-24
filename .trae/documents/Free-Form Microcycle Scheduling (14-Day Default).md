## Goals
- Move split-template selection into Advanced Settings as a preference only (not a generator constraint by default).
- Add microcycle duration preference (7–14 days or auto), defaulting to a centralized config value.
- Generate sessions across a 14-day window using goals/preferences/optimization, not PPL/UL/FB templates.
- Enforce even program week counts so 14-day microcycles fit cleanly.

## Config (Single Source of Truth)
- Add a global constant in [activity_distribution.py](file:///Users/shourjosmac/Documents/Gainsly/app/config/activity_distribution.py):
  - `default_microcycle_length_days: int = 14`
- Use this variable anywhere the system needs a default microcycle length (program creation, next-microcycle generation, etc.) so changing it in one place affects behavior everywhere.

## Backend Changes
- **Even-week enforcement**
  - Update [ProgramCreate.duration_weeks](file:///Users/shourjosmac/Documents/Gainsly/app/schemas/program.py) to reject odd values (must be even between 8 and 12).
  - Add defense-in-depth validation in [ProgramService.create_program](file:///Users/shourjosmac/Documents/Gainsly/app/services/program.py#L45-L68).

- **Microcycle length 7–14**
  - Update DB constraint in [Microcycle](file:///Users/shourjosmac/Documents/Gainsly/app/models/program.py#L95-L115) from 7–10 to 7–14.
  - Add an Alembic migration to replace the check constraint.
  - Update schema bounds that assume max 10 days (e.g., [HybridDayDefinition.day](file:///Users/shourjosmac/Documents/Gainsly/app/schemas/program.py#L32-L38) to allow up to 14).
  - Update any hardcoded `length_days=7` in “generate next microcycle” route ([programs.py](file:///Users/shourjosmac/Documents/Gainsly/app/api/routes/programs.py#L260-L326)) to use resolved preference:
    - if user sets a number (7–14) → use it
    - if user sets auto or unset → use `activity_distribution.default_microcycle_length_days`

- **New advanced preference fields (stored under UserProfile.scheduling_preferences JSON)**
  - `microcycle_length_days`: `"auto"` or integer `7..14` (default is effectively `auto`)
  - `split_template_preference`: `"none" | "full_body" | "upper_lower" | "ppl" | "hybrid"` (default `"none"`)
  - Keep existing keys like `mix_disciplines`, `cardio_preference`, `allow_cardio_only_days`, `allow_conditioning_only_days`.

## Program/Microcycle Scheduling Logic (Replace Template Constraints)
- In [ProgramService.create_program](file:///Users/shourjosmac/Documents/Gainsly/app/services/program.py#L45-L242):
  - Stop defaulting/enforcing split templates for schedule generation.
  - Resolve `cycle_length_days` from user preferences with config fallback (default→14).
  - Compute target sessions per cycle as `days_per_week * (cycle_length_days / 7)` → for 14 days this is `days_per_week * 2`.
  - Place sessions optimally across the `cycle_length_days` window (even spacing + recovery-aware placement).
  - Assign each session a type and intent tags using:
    - goal weights (strength/hypertrophy/endurance/fat_loss/mobility)
    - discipline preferences
    - scheduling preferences
  - Session section enforcement stays as-is (cardio/mobility/conditioning-only remain “middle-piece only”) via [SessionGeneratorService._normalize_session_content](file:///Users/shourjosmac/Documents/Gainsly/app/services/session_generator.py#L218-L226).

- Generalize goal distribution from “weekly” to “cycle-aware”:
  - Refactor [_apply_goal_based_weekly_distribution](file:///Users/shourjosmac/Documents/Gainsly/app/services/program.py#L682-L800) to scale cardio/conditioning insertion counts for 14 days (e.g., allow up to 2 dedicated cardio/conditioning-only days per 14-day microcycle when signals justify it).

## Interference Behavior
- Keep the existing pattern interference rules but make them 14-day safe:
  - The 1–2 day gap rules already work across 14 days.
  - Keep the current rolling 7-day “max 2 exposures” cap in [_has_pattern_conflict](file:///Users/shourjosmac/Documents/Gainsly/app/services/program.py#L499-L542) so interference is respected across the 2-week microcycle while still allowing consistent main lifts.

## Frontend Changes (Settings + Types)
- Extend Settings → Advanced Filters → Scheduling Preferences UI in [ProfileTab.tsx](file:///Users/shourjosmac/Documents/Gainsly/frontend/src/components/settings/ProfileTab.tsx) to include:
  - Microcycle duration: Auto (recommended), 7–14 selector
  - Split template preference: None (default), Full Body, Upper/Lower, PPL, Hybrid
- Update frontend types in [types/index.ts](file:///Users/shourjosmac/Documents/Gainsly/frontend/src/types/index.ts) to include the new `scheduling_preferences` keys.
- The wizard’s duration selection UI already only offers 8/10/12 in [CoachStep.tsx](file:///Users/shourjosmac/Documents/Gainsly/frontend/src/components/wizard/CoachStep.tsx#L77-L101), but backend will now enforce even-week counts too.

## Tests + Verification
- Add/extend tests to cover:
  - Reject odd `duration_weeks` (e.g., 9, 11).
  - Default microcycle length uses `activity_distribution.default_microcycle_length_days` when preference is auto/unset.
  - 14-day microcycle creates 14 sessions.
  - 14-day distribution can schedule 2× cardio/conditioning-only days when configured.
- Run migration smoke tests and program generation tests.

Confirm this plan and I’ll implement immediately (backend + migration + frontend + tests).