from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Numeric, CheckConstraint, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserProgram(Base):
    __tablename__ = "user_programs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    declared_date = Column(String(10))  # Date stored as "YYYY-MM-DD"
    expected_completion = Column(String(10))  # Date stored as "YYYY-MM-DD"
    is_primary = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="programs")
    program = relationship("Program", back_populates="user_programs")


class Preference(Base):
    __tablename__ = "preferences"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    avg_credits_per_term = Column(Integer, default=15)
    max_credits_per_term = Column(Integer, default=18)
    prefer_morning = Column(Boolean, default=False)
    prefer_afternoon = Column(Boolean, default=False)
    prefer_evening = Column(Boolean, default=False)
    prefer_compact_days = Column(Boolean, default=False)
    prefer_spread_days = Column(Boolean, default=False)
    day_preferences = Column(JSONB)
    excluded_times = Column(JSONB)
    settings = Column(JSONB)
    
    # Relationships
    user = relationship("User", back_populates="preferences")


class Completion(Base):
    __tablename__ = "completions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))
    term_code = Column(String(10), ForeignKey("terms.term_code"))
    external_subject = Column(String(10))
    external_number = Column(String(20))
    external_title = Column(String(255))
    credits_earned = Column(Numeric(3, 1), nullable=False)
    grade = Column(String(2))
    completion_type = Column(String(20), nullable=False)
    verified = Column(Boolean, default=False)
    
    __table_args__ = (
        CheckConstraint("completion_type IN ('institutional', 'transfer', 'exam', 'other')"),
        CheckConstraint("(course_id IS NOT NULL) OR (external_subject IS NOT NULL AND external_number IS NOT NULL)"),
    )
    
    # Relationships
    user = relationship("User", back_populates="completions")
    course = relationship("Course", back_populates="completions")


class Waiver(Base):
    __tablename__ = "waivers"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    block_id = Column(Integer, ForeignKey("requirement_blocks.id"))
    required_course_id = Column(Integer, ForeignKey("courses.id"))
    substitute_course_id = Column(Integer, ForeignKey("courses.id"))
    waiver_type = Column(String(20), nullable=False)
    reason = Column(Text)
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_date = Column(DateTime)
    
    __table_args__ = (
        CheckConstraint("waiver_type IN ('block', 'course', 'substitution')"),
        CheckConstraint(
            "(waiver_type = 'block' AND block_id IS NOT NULL) OR "
            "(waiver_type = 'course' AND required_course_id IS NOT NULL) OR "
            "(waiver_type = 'substitution' AND required_course_id IS NOT NULL AND substitute_course_id IS NOT NULL)"
        ),
    )
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="waivers")
    approver = relationship("User", foreign_keys=[approved_by])
    block = relationship("RequirementBlock", back_populates="waivers")
    required_course = relationship("Course", foreign_keys=[required_course_id])
    substitute_course = relationship("Course", foreign_keys=[substitute_course_id])
