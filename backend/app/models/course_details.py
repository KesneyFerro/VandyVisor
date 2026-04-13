from sqlalchemy import Column, Integer, String, ForeignKey, Text, CheckConstraint, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class CourseOffering(Base):
    __tablename__ = "course_offerings"
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    term_code = Column(String(10), ForeignKey("terms.term_code"), nullable=False)
    class_number = Column(Integer, nullable=False)
    section_number = Column(String(10), nullable=False)
    component = Column(String(50))
    instructor = Column(Text)
    location = Column(Text)
    days_of_week = Column(String(10))
    start_time = Column(String(10))  # Stored as "HH:MM" format
    end_time = Column(String(10))    # Stored as "HH:MM" format
    seats_total = Column(Integer)
    seats_available = Column(Integer)
    waitlist_count = Column(Integer, default=0)
    meta = Column(JSONB)
    
    # Relationships
    course = relationship("Course", back_populates="course_offerings")
    term = relationship("Term", back_populates="course_offerings")


class Attribute(Base):
    __tablename__ = "attributes"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    attribute_type = Column(String(50))
    
    # Relationships
    course_attributes = relationship("CourseAttribute", back_populates="attribute")


class CourseAttribute(Base):
    __tablename__ = "course_attributes"
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    attribute_id = Column(Integer, ForeignKey("attributes.id"), nullable=False)
    term_code = Column(String(10), ForeignKey("terms.term_code"))
    
    # Relationships
    course = relationship("Course", back_populates="attributes")
    attribute = relationship("Attribute", back_populates="course_attributes")


class RequisiteGroup(Base):
    __tablename__ = "requisite_groups"
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    kind = Column(String(10), nullable=False)
    logic = Column(String(20), nullable=False, default="all")
    min_count = Column(Integer)
    description = Column(Text)
    
    __table_args__ = (
        CheckConstraint("kind IN ('pre', 'co', 'anti')"),
        CheckConstraint("logic IN ('all', 'min_count')"),
    )
    
    # Relationships
    course = relationship("Course", back_populates="requisite_groups")
    members = relationship("RequisiteGroupMember", back_populates="group")


class RequisiteGroupMember(Base):
    __tablename__ = "requisite_group_members"
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("requisite_groups.id"), nullable=False)
    target_course_id = Column(Integer, ForeignKey("courses.id"))
    target_subject = Column(String(10))
    target_catalog = Column(String(20))
    concurrent_ok = Column(Boolean, default=False)
    grade_min = Column(String(2))
    
    # Ensure either target_course_id or (target_subject + target_catalog) is provided
    __table_args__ = (
        CheckConstraint("(target_course_id IS NOT NULL) OR (target_subject IS NOT NULL AND target_catalog IS NOT NULL)"),
    )
    
    # Relationships
    group = relationship("RequisiteGroup", back_populates="members")
    target_course = relationship("Course", foreign_keys=[target_course_id])


class CourseEquivalent(Base):
    __tablename__ = "course_equivalents"
    
    id = Column(Integer, primary_key=True)
    course_id_a = Column(Integer, ForeignKey("courses.id"), nullable=False)
    course_id_b = Column(Integer, ForeignKey("courses.id"), nullable=False)
    equivalence_type = Column(String(50), nullable=False)
    effective_from = Column(String(10))  # Date in "YYYY-MM-DD" format
    effective_to = Column(String(10))    # Date in "YYYY-MM-DD" format
    
    __table_args__ = (
        # Ensure course_id_a != course_id_b
        CheckConstraint("course_id_a != course_id_b"),
    )
    
    # Relationships
    course_a = relationship("Course", foreign_keys=[course_id_a])
    course_b = relationship("Course", foreign_keys=[course_id_b])
