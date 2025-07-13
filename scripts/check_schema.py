import os
import sys

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import settings after adding to path
from app.core.config import settings


def check_schema():
    # Create a connection URL
    db_url = URL.create(
        "postgresql",
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
    )

    # Create a synchronous engine
    engine = create_engine(db_url)

    # Create an inspector
    inspector = inspect(engine)

    # Get all table names
    tables = inspector.get_table_names()
    print("\n📋 Database Schema Check")
    print("=" * 30)

    if not tables:
        print("❌ No tables found in the database!")
        return

    print(f"✅ Found {len(tables)} tables:")
    for table in tables:
        print(f"\n📄 Table: {table}")
        print("-" * (len(table) + 9))

        # Get columns
        columns = inspector.get_columns(table)
        print("  Columns:")
        for col in columns:
            print(
                f"    - {col['name']}: {col['type']} {'(PK)' if col.get('primary_key', False) else ''}"
            )

        # Get indexes
        indexes = inspector.get_indexes(table)
        if indexes:
            print("\n  Indexes:")
            for idx in indexes:
                print(
                    f"    - {idx['name']}: {', '.join(idx['column_names'])} {'(unique)' if idx.get('unique', False) else ''}"
                )

        # Get foreign keys
        fks = inspector.get_foreign_keys(table)
        if fks:
            print("\n  Foreign Keys:")
            for fk in fks:
                print(
                    f"    - {', '.join(fk['constrained_columns'])} → {fk['referred_table']}({', '.join(fk['referred_columns'])})"
                )

    print("\n✅ Schema check completed!")


if __name__ == "__main__":
    check_schema()
