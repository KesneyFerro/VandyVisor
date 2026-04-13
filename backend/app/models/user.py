from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    hashed_password = Column(String(255))
    role = Column(String(20), default="student")
    is_active = Column(Boolean, default=True)
    auth_provider = Column(String(50))
    auth_id = Column(String(255))
    metadata = Column(JSONB)
    
    # Relationships
    programs = relationship("UserProgram", back_populates="user")
    preferences = relationship("Preference", back_populates="user", uselist=False)
    completions = relationship("Completion", back_populates="user")
    waivers = relationship("Waiver", back_populates="user")
    plans = relationship("Plan", back_populates="user")
