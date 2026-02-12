import pyotp
import qrcode
from io import BytesIO
from app.models.two_factor_auth import TwoFactorAuth
from app.models.user import User, UserRole
from app.repositories.base import Repository
from app.core.exceptions import ValidationError
from app.core.logging import get_logger


logger = get_logger(__name__)


class TwoFactorService:
    def __init__(self, two_factor_repo: Repository[TwoFactorAuth, int]):
        self._repo = two_factor_repo
    
    async def setup_2fa(self, user: User) -> dict:
        if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            raise ValidationError(
                "role",
                "Two-factor authentication is only available for admin users"
            )
        
        existing = await self._repo.list({"user_id": user.id})
        if existing.items:
            await self._repo.delete(existing.items[0].id)
        
        secret = pyotp.random_base32()
        backup_codes = [pyotp.random_base32()[:6] for _ in range(8)]
        
        two_factor = TwoFactorAuth(
            user_id=user.id,
            secret=secret,
            backup_codes=",".join(backup_codes),
            is_enabled=False,
            is_verified=False,
        )
        await self._repo.create(two_factor)
        
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="Alloy"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        return {
            "qr_code": f"data:image/png;base64,{buffer.getvalue().hex()}",
            "backup_codes": backup_codes,
            "secret": secret
        }
    
    async def verify_2fa(self, user: User, code: str) -> bool:
        two_factor = await self._repo.get_by_user_id(user.id)
        
        if not two_factor or not two_factor.is_enabled:
            raise ValidationError(
                "2fa",
                "Two-factor authentication not enabled for this user"
            )
        
        totp = pyotp.totp.TOTP(two_factor.secret)
        
        if totp.verify(code, valid_window=1):
            if not two_factor.is_verified:
                two_factor.is_verified = True
                two_factor.verified_at = func.now()
                await self._repo.update(two_factor.id, {
                    "is_verified": True,
                    "verified_at": datetime.utcnow()
                })
            return True
        
        backup_codes = two_factor.backup_codes_list
        if code in backup_codes:
            backup_codes.remove(code)
            two_factor.set_backup_codes(backup_codes)
            await self._repo.update(two_factor.id, {
                "backup_codes": two_factor.backup_codes
            })
            return True
        
        logger.warning(
            "Invalid 2FA code attempt",
            extra={
                "user_id": user.id,
                "email": user.email,
            }
        )
        return False
    
    async def enable_2fa(self, user: User, code: str) -> dict:
        if await self.verify_2fa(user, code):
            two_factor = await self._repo.get_by_user_id(user.id)
            await self._repo.update(two_factor.id, {"is_enabled": True})
            return {"success": True, "message": "2FA enabled successfully"}
        return {"success": False, "message": "Invalid verification code"}
    
    async def disable_2fa(self, user: User, password: str) -> dict:
        from app.security.password import verify_password
        
        if not verify_password(password, user.hashed_password):
            raise ValidationError("password", "Invalid password")
        
        two_factor = await self._repo.get_by_user_id(user.id)
        if two_factor:
            await self._repo.delete(two_factor.id)
        
        return {"success": True, "message": "2FA disabled successfully"}
    
    async def require_2fa_for_user(self, user: User) -> bool:
        if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            return False
        
        two_factor = await self._repo.get_by_user_id(user.id)
        return two_factor and two_factor.is_enabled
