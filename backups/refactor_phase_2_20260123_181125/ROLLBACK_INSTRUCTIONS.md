# Phase 2 Refactor Rollback Instructions

## Backup Location
`backups/refactor_phase_2_20260123_181125/`

## Backup Contents
- **Database State:** `table_counts.txt` (row counts for all tables)
- **Key Files:**
  - `app/models/movement.py`
  - `app/models/program.py`
  - `app/models/enums.py`
  - `frontend/src/types/anatomy.ts`
  - `frontend/src/types/index.ts`
  - `frontend/src/stores/program-wizard-store.ts`

## Quick Rollback Commands

### 1. Restore Key Files
```bash
BACKUP_DIR=backups/refactor_phase_2_20260123_181125
cp $BACKUP_DIR/movement.py app/models/
cp $BACKUP_DIR/program.py app/models/
cp $BACKUP_DIR/enums.py app/models/
cp $BACKUP_DIR/anatomy.ts frontend/src/types/
cp $BACKUP_DIR/index.ts frontend/src/types/
cp $BACKUP_DIR/program-wizard-store.ts frontend/src/stores/
```

### 2. Rollback Database Migrations
```bash
cd /Users/shourjosmac/Documents/Gainsly

# List migrations to identify the ones to rollback
alembic history

# Rollback specific migrations (adjust number as needed)
alembic downgrade -1  # Rollback one migration
# Repeat until back to baseline
```

### 3. Verify Database State
```bash
PYTHONPATH=/Users/shourjosmac/Documents/Gainsly python backups/refactor_phase_2_20260123_181125/backup_database.py
# Compare output with table_counts.txt
```

## Migration Rollback Order

If you need to rollback after any phase:

**Phase 4 Rollback:**
1. Git revert frontend changes
2. Git revert API layer changes

**Phase 3 Rollback:**
1. `alembic downgrade -1` (Drop disciplines_json column)
2. `alembic downgrade -1` (Update Program model)
3. `alembic downgrade -1` (Migrate JSON to relational - check migration script for restore)
4. `alembic downgrade -1` (Drop junction table)

**Phase 2 Rollback:**
1. `alembic downgrade -1` (Drop block_type column)
2. `alembic downgrade -1` (Drop name column)

**Phase 1 Rollback:**
1. Git revert all frontend type changes
2. Run frontend build to verify TypeScript compilation

## Current Database State (Baseline)

Key tables row counts:
- movements: 428 rows
- muscles: 19 rows
- movement_muscle_map: 432 rows
- tags: 16 rows
- movement_tags: 432 rows
- session_exercises: 1655 rows
- programs: 60 rows
- sessions: 4648 rows

## Contact Support

If rollback fails, check:
1. Database connection: Verify PostgreSQL is running
2. Migration status: Check `alembic current` for current version
3. Foreign key constraints: May need to drop constraints before rollback
