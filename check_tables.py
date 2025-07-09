import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).resolve().parent)
sys.path.append(project_root)

from sqlalchemy import text
from app.db.base import async_engine

async def check_tables():
    print("🔍 Checking database tables...")
    
    try:
        async with async_engine.connect() as conn:
            # Check if tables exist
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            if not tables:
                print("❌ No tables found in the database!")
                return
                
            print("\n✅ Found tables:")
            for table in tables:
                print(f"\n📋 Table: {table}")
                
                # Get column info
                cols = await conn.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position;
                """))
                
                print("  Columns:")
                for col in cols:
                    print(f"  - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
    
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting database table check...\n")
    asyncio.run(check_tables())
    print("\n✨ Table check completed!")
