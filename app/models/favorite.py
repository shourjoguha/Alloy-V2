from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movement_id = Column(Integer, ForeignKey("movements.id", ondelete="CASCADE"), nullable=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    movement = relationship("Movement", back_populates="favorites")
    program = relationship("Program", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "movement_id", name="uq_user_movement_favorite"),
        UniqueConstraint("user_id", "program_id", name="uq_user_program_favorite"),
    )
