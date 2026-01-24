"""Ingest database tables from CSV files."""
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import get_settings
from app.models import *  # Import all models to ensure they're registered

settings = get_settings()

if settings.database_url.startswith("postgresql+asyncpg"):
    DATABASE_URL = settings.database_url.replace("+asyncpg", "")
else:
    DATABASE_URL = settings.database_url

CSV_DIR = Path(__file__).parent


def parse_value(value: str, column_name: str) -> Any:
    """Parse a string value into appropriate Python type."""
    if value == '' or value.lower() == 'none':
        return None
    
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    
    try:
        return int(value)
    except ValueError:
        pass
    
    try:
        return float(value)
    except ValueError:
        pass
    
    return value


def load_csv_to_dict(csv_path: Path) -> List[Dict[str, Any]]:
    """Load a CSV file into a list of dictionaries."""
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed_row = {k: parse_value(v, k) for k, v in row.items()}
            rows.append(parsed_row)
    return rows


def get_table_columns(engine, table_name: str) -> List[str]:
    """Get the column names for a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return columns


def truncate_table(engine, table_name: str) -> None:
    """Truncate a table to clear existing data."""
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
        conn.commit()


def ingest_table(csv_path: Path, engine, truncate: bool = False) -> int:
    """Ingest a single table from CSV."""
    table_name = csv_path.stem
    
    try:
        rows = load_csv_to_dict(csv_path)
        
        if not rows:
            print(f"  No data to ingest in {csv_path.name}")
            return 0
        
        if truncate:
            truncate_table(engine, table_name)
            print(f"  Truncated table: {table_name}")
        
        columns = get_table_columns(engine, table_name)
        
        with engine.connect() as conn:
            for row in rows:
                filtered_row = {k: v for k, v in row.items() if k in columns}
                
                if not filtered_row:
                    continue
                
                columns_str = ', '.join(filtered_row.keys())
                values_str = ', '.join([f':{k}' for k in filtered_row.keys()])
                
                insert_sql = text(f"""
                    INSERT INTO {table_name} ({columns_str})
                    VALUES ({values_str})
                    ON CONFLICT DO NOTHING
                """)
                
                conn.execute(insert_sql, filtered_row)
            
            conn.commit()
        
        print(f"  Ingested {len(rows)} rows into {table_name}")
        return len(rows)
        
    except Exception as e:
        print(f"  Error ingesting {table_name}: {e}")
        import traceback
        traceback.print_exc()
        return 0


def ingest_all_tables(truncate: bool = False) -> None:
    """Ingest all CSV files into the database."""
    print(f"Connecting to database: {DATABASE_URL}")
    
    engine = create_engine(DATABASE_URL, echo=False)
    
    csv_files = sorted(CSV_DIR.glob("*.csv"))
    
    print(f"\nFound {len(csv_files)} CSV files to ingest:\n")
    
    total_rows = 0
    for csv_file in csv_files:
        print(f"Ingesting {csv_file.name}...")
        rows = ingest_table(csv_file, engine, truncate=truncate)
        total_rows += rows
    
    engine.dispose()
    
    print(f"\nTotal rows ingested: {total_rows}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Ingest database tables from CSV files'
    )
    parser.add_argument(
        '--truncate',
        action='store_true',
        help='Truncate tables before inserting data'
    )
    
    args = parser.parse_args()
    
    if args.truncate:
        confirm = input("WARNING: This will TRUNCATE all tables before importing. Type 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            return
    
    ingest_all_tables(truncate=args.truncate)


if __name__ == "__main__":
    main()
