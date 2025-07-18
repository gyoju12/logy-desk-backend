import asyncio

from sqlalchemy import text

from app.db.base import async_engine


async def check_database_schema() -> None:
    print("🔍 Checking database schema...")

    async with async_engine.connect() as conn:
        # Check if tables were created
        result = await conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
                """
            )
        )
        tables = [row[0] for row in result.all()]
        print("\n📋 Database tables:")
        for table in tables:
            print(f"- {table}")

            # Get column info for each table
            result = await conn.execute(
                text(
                    f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position;
            """
                )
            )

            print("  Columns:")
            for col in result.all():
                print(
                    f"  - {col[0]}: {col[1]} "
                    f"({'NULL' if col[2] == 'YES' else 'NOT NULL'})"
                )

            # Check indexes
            result = await conn.execute(
                text(
                    f"""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = '{table}';
            """
                )
            )

            indexes = result.all()
            if indexes:
                print("  Indexes:")
                for idx in indexes:
                    print(f"  - {idx[0]}")

            print()  # Add space between tables


if __name__ == "__main__":
    asyncio.run(check_database_schema())
