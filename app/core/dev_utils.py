"""Development utilities for temporary authentication and testing."""
from uuid import UUID

# Temporary development user ID
DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

def get_temp_user():
    """
    Get a temporary user object for development.
    
    Returns:
        dict: A dictionary containing user information with a temporary user ID.
    """
    return {
        "id": DEV_USER_ID,
        "email": "temp@example.com",
        "is_active": True,
        "is_superuser": False
    }
