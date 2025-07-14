"""Script to reset Alembic version and prepare for a fresh migration."""

from app.db.session import get_sync_session


def reset_alembic() -> None:
    """Reset the Alembic version table and prepare for a fresh migration."""
    try:
        # Create a new session
        db = get_sync_session() # Use get_sync_session
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
