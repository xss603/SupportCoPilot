from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings
from app.schemas.auth import AuthUser, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Auth & RBAC"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    """Authenticate reviewer or admin user and issue a JWT bearer token."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication service is scheduled for Milestone M2 implementation.",
    )


@router.get("/me", response_model=AuthUser)
async def get_current_user_profile(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    """Return the authenticated user profile and RBAC role."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token validation service is scheduled for Milestone M2 implementation.",
    )
