"""Script to check and reset the database state."""
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal

def check_database():
    # Check if the database is accessible
    try:
        db = SessionLocal()
        conn = db.connection()
        
        # Check if alembic_version table exists
        result = conn.execute(
            text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'alembic_version';
            """)
        )
        alembic_version_exists = result.scalar() is not None
        print(f"Alembic version table exists: {alembic_version_exists}")
        
        if alembic_version_exists:
            # Get current revision
            result = conn.execute(
                text("SELECT version_num FROM alembic_version;")
            )
            current_rev = result.scalar()
            print(f"Current Alembic revision: {current_rev}")
        
        # List all tables
        result = conn.execute(
            text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
            """)
        )
        tables = [row[0] for row in result]
        print("\nTables in database:")
        for table in tables:
            print(f"- {table}")
                
    except Exception as e:
        print(f"Error connecting to database: {e}")

if __name__ == "__main__":
    check_database()
