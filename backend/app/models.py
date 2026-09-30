from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, Boolean, Table
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Employee(Base):
    __tablename__ = "employee"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    role = Column(String)
    department = Column(String)
    level = Column(String)  # Junior/Mid/Senior/Lead
    location = Column(String)
    manager_id = Column(Integer, ForeignKey("employee.id"), nullable=True)

class Skill(Base):
    __tablename__ = "skill"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)
    half_life_months = Column(Integer, nullable=True)

class SkillAlias(Base):
    __tablename__ = "skill_alias"
    skill_id = Column(Integer, ForeignKey("skill.id"), primary_key=True)
    alias = Column(String, primary_key=True, index=True)

class SkillRelation(Base):
    __tablename__ = "skill_relation"
    skill_a_id = Column(Integer, ForeignKey("skill.id"), primary_key=True)
    skill_b_id = Column(Integer, ForeignKey("skill.id"), primary_key=True)
    strength = Column(Float)

class Domain(Base):
    __tablename__ = "domain"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    keywords = Column(JSON)

class Project(Base):
    __tablename__ = "project"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    domain_id = Column(Integer, ForeignKey("domain.id"), nullable=True)
    complexity = Column(Integer)  # 1-5
    start_date = Column(String)
    end_date = Column(String, nullable=True)
    _truth_skills = Column(JSON, nullable=True)

class ProjectSkill(Base):
    __tablename__ = "project_skill"
    project_id = Column(Integer, ForeignKey("project.id"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skill.id"), primary_key=True)
    confidence = Column(Float)
    source = Column(String)  # extracted / manual

class Assignment(Base):
    __tablename__ = "assignment"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employee.id"))
    project_id = Column(Integer, ForeignKey("project.id"))
    role = Column(String)  # Contributor/Lead/Architect
    allocation_pct = Column(Float)
    start_date = Column(String)
    end_date = Column(String, nullable=True)

class Certification(Base):
    __tablename__ = "certification"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    issuer = Column(String)
    skill_ids = Column(JSON)

class EmployeeCertification(Base):
    __tablename__ = "employee_certification"
    employee_id = Column(Integer, ForeignKey("employee.id"), primary_key=True)
    certification_id = Column(Integer, ForeignKey("certification.id"), primary_key=True)
    issued_on = Column(String)
    expires_on = Column(String, nullable=True)

class TrainingRecord(Base):
    __tablename__ = "training_record"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employee.id"))
    course_name = Column(String)
    skill_ids = Column(JSON)
    completed_on = Column(String)

class SelfDeclaredSkill(Base):
    __tablename__ = "self_declared_skill"
    employee_id = Column(Integer, ForeignKey("employee.id"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skill.id"), primary_key=True)

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employee.id"))
    skill_id = Column(Integer, ForeignKey("skill.id"))
    source_type = Column(String)  # project/certification/training/self_declared
    source_id = Column(Integer)
    weight = Column(Float)
    occurred_on = Column(String)
    description = Column(String)

class Proficiency(Base):
    __tablename__ = "proficiency"
    employee_id = Column(Integer, ForeignKey("employee.id"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skill.id"), primary_key=True)
    score = Column(Float)
    level = Column(String)
    verified = Column(Boolean)
    breakdown = Column(JSON)
    computed_at = Column(String)

class Course(Base):
    __tablename__ = "course"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    provider = Column(String)
    skill_id = Column(Integer, ForeignKey("skill.id"))
    from_level = Column(String)
    to_level = Column(String)
    hours = Column(Float)
    points_gain = Column(Float)

class LlmCache(Base):
    __tablename__ = "llm_cache"
    key = Column(String, primary_key=True)
    response = Column(JSON)
    created_at = Column(String)
