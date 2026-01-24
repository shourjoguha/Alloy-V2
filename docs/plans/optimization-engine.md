# Implementation Plan: Optimization Engine & Data Strategy

## Overview

This plan implements the optimization engine and data strategy with expanded sports and activities support.

---

## 1. Data Seeding & Cross-Validation

**Action:** Create `scripts/enrich_movement_data.py` to logically seed `fatigue_factor`, `stimulus_factor`, etc.

**Validation:** Generate `movement_audit.csv` for expert review.

---

## 2. The Optimization Engine (OR-Tools)

**Action:** Implement `ConstraintSolver` service using `ortools`.

**Logic:** Maximize Stimulus subject to Fatigue < Capacity and Injury Constraints.

---

## 3. External Activities (Expanded)

**Action:** Create `seed_data/activities.json` with comprehensive list:

**Sports:**
- Tennis, Padel, Pickleball, Golf, Bouldering, Badminton, Squash, Basketball

**Football:**
- Indoor Football (6-a-side), 11-a-side Football

**Water:**
- Surfing, Kayaking

**Endurance:**
- Trail Run, City Run

**Fitness:**
- Pilates

**Metrics:** Each will have a `default_metric_type` (e.g., Duration) and a `cns_impact` rating (e.g., Squash = High, Golf = Low) to estimate fatigue when HR/Power data is missing.

---

## 4. Handling Data Gaps

**Action:** Implement `UserFatigueState` logic that accepts manual "Check-in" signals to override estimated decay.

---

## Implementation Order

1. Create Activity Seeding Data
2. Create Movement Enrichment Script
3. Implement Constraint Solver service
4. Add external activities to seed data
5. Implement fatigue state logic with manual check-in override
6. Add comprehensive tests for optimization engine
7. Update documentation and examples
