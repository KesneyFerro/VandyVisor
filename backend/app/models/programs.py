from sqlalchemy import Column, Integer, String, ForeignKey, Text, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class Program(Base):
    __tablename__ = "programs"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)
    catalog_year = Column(String(10), nullable=False)
    school = Column(String(100))
    total_credits_required = Column(Integer)
    description = Column(Text)
    
    __table_args__ = (
        CheckConstraint("type IN ('major', 'minor', 'certificate', 'other')"),
    )
    
    # Relationships
    requirement_blocks = relationship("RequirementBlock", back_populates="program")
    user_programs = relationship("UserProgram", back_populates="program")


class RequirementBlock(Base):
    __tablename__ = "requirement_blocks"
    
    id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    parent_block_id = Column(Integer, ForeignKey("requirement_blocks.id"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    required_credits = Column(Numeric(5, 1))
    required_courses = Column(Integer)
    sequence_order = Column(Integer)
    rule = Column(JSONB, nullable=False)
    
    # Relationships
    program = relationship("Program", back_populates="requirement_blocks")
    parent_block = relationship("RequirementBlock", remote_side=[id], backref="child_blocks")
    block_course_matches = relationship("BlockCourseMatch", back_populates="block")
    waivers = relationship("Waiver", back_populates="block")


class BlockCourseMatch(Base):
    __tablename__ = "block_course_matches"
    
    id = Column(Integer, primary_key=True)
    block_id = Column(Integer, ForeignKey("requirement_blocks.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    
    # Relationships
    block = relationship("RequirementBlock", back_populates="block_course_matches")
    course = relationship("Course", back_populates="block_matches")


class CourseUnlock(Base):
    __tablename__ = "course_unlocks"
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    unlocks_course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    
    # Relationships
    course = relationship("Course", foreign_keys=[course_id], back_populates="course_unlocks")
    unlocks_course = relationship("Course", foreign_keys=[unlocks_course_id], back_populates="unlocks_for")


class CourseReachability(Base):
    __tablename__ = "course_reachability"
    
    id = Column(Integer, primary_key=True)
    source_course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    reachable_course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    distance = Column(Integer, nullable=False)
    
    # Relationships
    source_course = relationship("Course", foreign_keys=[source_course_id])
    reachable_course = relationship("Course", foreign_keys=[reachable_course_id])
