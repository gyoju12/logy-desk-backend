"""Script to reset Alembic version and prepare for a fresh migration."""

from sqlalchemy import text

from app.db.session import SessionLocal


def reset_alembic():
    """Reset the Alembic version table and prepare for a fresh migration."""
    try:
        # Create a new session
        db = SessionLocal()
        conn = db.connection()

        # Drop all tables except alembic_version
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))

        # Commit the transaction
        db.commit()
        print("Successfully dropped the alembic_version table.")

    except Exception as e:
        print(f"Error resetting Alembic: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("Resetting Alembic version table...")
    reset_alembic()
    print("Alembic reset complete. You can now create a fresh migration.")
