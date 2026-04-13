from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Numeric, Date, Time, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True)
    subject_code = Column(String(10), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    department = Column(String(255))
    school = Column(String(100))
    
    # Relationships
    courses = relationship("Course", back_populates="subject")


class Term(Base):
    __tablename__ = "terms"
    
    id = Column(Integer, primary_key=True)
    term_code = Column(String(10), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    registration_start = Column(Date)
    registration_end = Column(Date)
    is_active = Column(Boolean, default=False)
    
    # Relationships
    course_offerings = relationship("CourseOffering", back_populates="term")
    plan_terms = relationship("PlanTerm", back_populates="term")


class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True)
    subject_code = Column(String(10), ForeignKey("subjects.subject_code"), nullable=False)
    catalog_number = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    level = Column(Integer)
    units_earned = Column(Numeric(3, 1), nullable=False)
    credit_hours_min = Column(Integer)
    credit_hours_max = Column(Integer)
    is_offered_fall = Column(Boolean, default=False)
    is_offered_spring = Column(Boolean, default=False)
    is_offered_summer = Column(Boolean, default=False)
    terms_offered_raw = Column(Text)
    prerequisites_raw = Column(Text)
    corequisites_raw = Column(Text)
    antirequisites_raw = Column(Text)
    
    __table_args__ = (
        # Ensure unique subject + catalog_number combination
        CheckConstraint('subject_code IS NOT NULL AND catalog_number IS NOT NULL'),
    )
    
    # Relationships
    subject = relationship("Subject", back_populates="courses")
    course_offerings = relationship("CourseOffering", back_populates="course")
    attributes = relationship("CourseAttribute", back_populates="course")
    requisite_groups = relationship("RequisiteGroup", back_populates="course")
    course_unlocks = relationship(
        "CourseUnlock",
        primaryjoin="Course.id==CourseUnlock.course_id",
        back_populates="course",
    )
    unlocks_for = relationship(
        "CourseUnlock",
        primaryjoin="Course.id==CourseUnlock.unlocks_course_id",
        back_populates="unlocks_course",
    )
    block_matches = relationship("BlockCourseMatch", back_populates="course")
    plan_items = relationship("PlanItem", back_populates="course")
    completions = relationship("Completion", back_populates="course")
