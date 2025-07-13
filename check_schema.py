import asyncio
from sqlalchemy import inspect
from sqlalchemy import text
from app.db.base import async_engine, AsyncSessionLocal
from app.core.config import settings

async def check_database_schema():
    print("🔍 Checking database schema...")
    
    async with async_engine.connect() as conn:
        # Check if tables were created
        result = await conn.execute(text("""SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"""))
        tables = [row[0] for row in await result.fetchall()]
        print("\n📋 Database tables:")
        for table in tables:
            print(f"- {table}")
            
            # Get column info for each table
            result = await conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position;
            """))
            
            print(f"  Columns:")
            for col in result.fetchall():
                print(f"  - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
            
            # Check indexes
            result = await conn.execute(text(f"""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = '{table}';
            """))
            
            indexes = result.fetchall()
            if indexes:
                print(f"  Indexes:")
                for idx in indexes:
                    print(f"  - {idx[0]}")
            
            print()  # Add space between tables

if __name__ == "__main__":
    asyncio.run(check_database_schema())
