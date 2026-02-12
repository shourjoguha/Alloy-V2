from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from typing import Optional
from app.api.routes.dependencies import get_current_user
from app.models.user import User
from app.services.two_factor_service import TwoFactorService
from app.repositories.two_factor_auth_repository import TwoFactorAuthRepository
from app.core.exceptions import ValidationError, NotFoundError
from app.db.database import get_db


router = APIRouter(prefix="/auth/2fa", tags=["Authentication"])


class TwoFactorSetupRequest(BaseModel):
    password: str = Field(..., min_length=8)


class TwoFactorVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class TwoFactorDisableRequest(BaseModel):
    password: str = Field(..., min_length=8)


class TwoFactorSetupResponse(BaseModel):
    qr_code: str
    backup_codes: list[str]
    secret: str


class TwoFactorResponse(BaseModel):
    success: bool
    message: str


@router.post("/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    request: TwoFactorSetupRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    repo = TwoFactorAuthRepository(db)
    service = TwoFactorService(repo)
    
    result = await service.setup_2fa(current_user)
    return TwoFactorSetupResponse(**result)


@router.post("/verify", response_model=TwoFactorResponse)
async def verify_2fa(
    request: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    repo = TwoFactorAuthRepository(db)
    service = TwoFactorService(repo)
    
    success = await service.verify_2fa(current_user, request.code)
    if success:
        return TwoFactorResponse(
            success=True,
            message="2FA code verified successfully"
        )
    raise ValidationError("verification_code", "Invalid 2FA code", details={"user_id": current_user.id, "code_provided": request.code})


@router.post("/enable", response_model=TwoFactorResponse)
async def enable_2fa(
    request: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    repo = TwoFactorAuthRepository(db)
    service = TwoFactorService(repo)
    
    result = await service.enable_2fa(current_user, request.code)
    
    if result["success"]:
        return TwoFactorResponse(**result)
    
    raise ValidationError("enable_code", result["message"], details={"user_id": current_user.id, "message": result["message"]})


@router.post("/disable", response_model=TwoFactorResponse)
async def disable_2fa(
    request: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    repo = TwoFactorAuthRepository(db)
    service = TwoFactorService(repo)
    
    result = await service.disable_2fa(current_user, request.password)
    return TwoFactorResponse(**result)


@router.get("/status")
async def get_2fa_status(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    repo = TwoFactorAuthRepository(db)
    service = TwoFactorService(repo)
    
    is_enabled = await service.require_2fa_for_user(current_user)
    
    return {
        "enabled": is_enabled,
        "user_id": current_user.id,
        "email": current_user.email
    }
