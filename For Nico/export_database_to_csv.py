"""Export all database tables to CSV files."""
import csv
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import get_settings

settings = get_settings()

if settings.database_url.startswith("postgresql+asyncpg"):
    DATABASE_URL = settings.database_url.replace("+asyncpg", "")
else:
    DATABASE_URL = settings.database_url

OUTPUT_DIR = Path(__file__).parent


def export_table_to_csv(table_name: str, engine) -> None:
    """Export a single table to CSV."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()
            
            if not rows:
                print(f"  No data in {table_name}")
                return
            
            columns = list(result.keys())
            
            csv_path = OUTPUT_DIR / f"{table_name}.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                writer.writerow(columns)
                
                for row in rows:
                    writer.writerow([str(val) if val is not None else '' for val in row])
            
            print(f"  Exported {len(rows)} rows to {csv_path.name}")
            
    except Exception as e:
        print(f"  Error exporting {table_name}: {e}")


def export_all_tables() -> None:
    """Export all tables in the database to CSV files."""
    print(f"Connecting to database: {DATABASE_URL}")
    
    engine = create_engine(DATABASE_URL, echo=False)
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\nFound {len(tables)} tables to export:\n")
    
    for table in sorted(tables):
        print(f"Exporting {table}...")
        export_table_to_csv(table, engine)
    
    engine.dispose()
    
    print(f"\nAll tables exported to: {OUTPUT_DIR}")


if __name__ == "__main__":
    export_all_tables()
