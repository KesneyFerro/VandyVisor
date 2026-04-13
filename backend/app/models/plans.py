from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Numeric, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Plan(Base):
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_primary = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="plans")
    terms = relationship("PlanTerm", back_populates="plan")
    audit_runs = relationship("AuditRun", back_populates="plan")
    recommendations = relationship("Recommendation", back_populates="plan")


class PlanTerm(Base):
    __tablename__ = "plan_terms"
    
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    term_code = Column(String(10), ForeignKey("terms.term_code"), nullable=False)
    term_number = Column(Integer, nullable=False)
    is_final_term = Column(Boolean, default=False)
    
    # Relationships
    plan = relationship("Plan", back_populates="terms")
    term = relationship("Term", back_populates="plan_terms")
    items = relationship("PlanItem", back_populates="plan_term")


class PlanItem(Base):
    __tablename__ = "plan_items"
    
    id = Column(Integer, primary_key=True)
    plan_term_id = Column(Integer, ForeignKey("plan_terms.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    is_pinned = Column(Boolean, default=False)
    is_backup = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Relationships
    plan_term = relationship("PlanTerm", back_populates="items")
    course = relationship("Course", back_populates="plan_items")


class AuditRun(Base):
    __tablename__ = "audit_runs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"))
    run_date = Column(DateTime, nullable=False, server_default=func.now())
    status = Column(String(20), nullable=False, default="complete")
    summary = Column(JSONB)
    details = Column(JSONB)
    
    # Relationships
    user = relationship("User")
    plan = relationship("Plan", back_populates="audit_runs")


class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"))
    term_code = Column(String(10), ForeignKey("terms.term_code"))
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    score = Column(Numeric(10, 5), nullable=False)
    unlock_count = Column(Integer)
    block_satisfaction = Column(JSONB)
    rationale = Column(Text)
    
    # Relationships
    user = relationship("User")
    plan = relationship("Plan", back_populates="recommendations")
    course = relationship("Course")


class UserAuditRow(Base):
    __tablename__ = "user_audit_rows"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    program_id = Column(Integer, ForeignKey("programs.id"))
    audit_section = Column(String(100))
    audit_text = Column(Text)
    raw_import = Column(JSONB)
    
    # Relationships
    user = relationship("User")
    program = relationship("Program")
