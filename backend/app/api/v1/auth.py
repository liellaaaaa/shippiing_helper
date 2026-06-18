"""Authentication API routes."""
from fastapi import APIRouter, HTTPException, status

from app.models.user import LoginRequest, TokenResponse
from app.services.auth_service import authenticate

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """用户登录，验证 name + password，返回 JWT token."""
    try:
        result = authenticate(body.name, body.password)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )
