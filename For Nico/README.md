# Database Data Export/Import for Nico

This folder contains CSV exports of all database tables and scripts to export/ingest the data.

## Files

### CSV Files
All 39 database tables have been exported to CSV format:
- `activity_definitions.csv` - 19 rows
- `circuit_templates.csv` - 29 rows
- `heuristic_configs.csv` - 10 rows
- `microcycles.csv` - 558 rows
- `movements.csv` - 489 rows
- `programs.csv` - 54 rows
- `sessions.csv` - 4,172 rows
- `users.csv` - 1 row
- And 30 other tables (some empty)

### Python Scripts

#### `export_database_to_csv.py`
Exports all tables from the current database to CSV files.

Usage:
```bash
python export_database_to_csv.py
```

This script:
- Connects to the database using the configured connection string
- Exports all tables to CSV files in this directory
- Handles NULL values and data types appropriately

#### `ingest_database_from_csv.py`
Imports data from CSV files into a fresh database.

Usage:
```bash
python ingest_database_from_csv.py
```

With table truncation (WARNING: deletes existing data):
```bash
python ingest_database_from_csv.py --truncate
```

This script:
- Reads all CSV files in this directory
- Parses data types (integers, floats, booleans, strings)
- Inserts data into corresponding database tables
- Handles conflicts gracefully (skips duplicate rows)
- Preserves foreign key relationships

## Requirements

Before running these scripts, ensure:
1. Python environment is set up with the project dependencies
2. Database is running and accessible
3. Database connection is configured in `app/config/settings.py`
4. All database models are defined in `app/models/`

## Data Export Summary

Export Date: 2026-01-21

Tables with data:
- `activity_definitions` (19 rows)
- `alembic_version` (1 row)
- `circuit_templates` (29 rows)
- `heuristic_configs` (10 rows)
- `microcycles` (558 rows)
- `movements` (489 rows)
- `programs` (54 rows)
- `sessions` (4,172 rows)
- `user_enjoyable_activities` (4 rows)
- `user_movement_rules` (6 rows)
- `user_profiles` (1 row)
- `user_settings` (1 row)
- `users` (1 row)

Empty tables (schema only):
- `activity_instance_links`, `activity_instances`, `activity_muscle_map`
- `conversation_threads`, `conversation_turns`, `disciplines`
- `external_activity_records`, `external_ingestion_runs`, `external_metric_streams`, `external_provider_accounts`
- `goal_checkins`, `goals`, `macro_cycles`
- `movement_muscle_map`, `movement_relationships`, `muscles`
- `pattern_exposures`, `recovery_signals`
- `session_exercises`, `soreness_logs`, `top_set_logs`
- `user_biometrics_history`, `user_fatigue_state`, `user_injuries`, `user_skills`
- `workout_logs`

Total: 39 tables
