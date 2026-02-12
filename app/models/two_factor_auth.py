from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta


class TwoFactorAuth:
    __tablename__ = "two_factor_auths"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    secret = Column(String(32), nullable=False)
    backup_codes = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    user = relationship("User", back_populates="two_factor_auth")
    
    @property
    def is_expired(self) -> bool:
        if not self.verified_at:
            return False
        return datetime.utcnow() - self.verified_at > timedelta(days=1)
    
    @property
    def backup_codes_list(self) -> list[str]:
        if self.backup_codes:
            return self.backup_codes.split(",")
        return []
    
    def set_backup_codes(self, codes: list[str]):
        self.backup_codes = ",".join(codes)
