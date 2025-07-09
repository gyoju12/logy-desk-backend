from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, get_current_active_user
from app.core.password_utils import get_password_hash
from app.crud.crud_user import create_user, authenticate_user, get_user_by_email
from app.db.session import get_db
from app.schemas.token import Token
from app.schemas.user import User, UserCreate, UserInDB

router = APIRouter()

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.
    
    - **email**: User's email address
    - **password**: User's password (min 8 characters)
    - **is_active**: Whether the user is active (default: True)
    - **is_superuser**: Whether the user is a superuser (default: False)
    """
    # Check if user already exists
    db_user = await get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Create new user
        user = await create_user(db=db, user_in=user_in)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    - **username**: User's email address
    - **password**: User's password
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Login attempt for user: {form_data.username}")
        
        # Debug: Log the form data (without password for security)
        logger.debug(f"Login form data - username: {form_data.username}")
        
        # Debug: Check if user exists
        user = await get_user_by_email(db, email=form_data.username)
        if not user:
            logger.warning(f"Login failed: User {form_data.username} not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        logger.debug(f"User found: {user.email}, is_active: {user.is_active}")
        
        # Verify password
        from app.core.password_utils import verify_password
        is_password_correct = verify_password(form_data.password, user.hashed_password)
        logger.debug(f"Password verification result: {is_password_correct}")
        
        if not is_password_correct:
            logger.warning(f"Login failed: Incorrect password for user {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning(f"Login failed: Inactive user {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # Create access token
        logger.debug("Creating access token...")
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, 
            expires_delta=access_token_expires
        )
        logger.info(f"Login successful for user: {user.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        logger.error(f"Error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )

@router.get("/me", response_model=User)
async def read_users_me(
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Get current user information.
    
    - **Requires authentication**
    """
    return current_user
