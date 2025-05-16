from sqlalchemy import create_engine, Column, String, Integer, Boolean, JSON, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import text  # Added this import
from sqlalchemy.ext.declarative import declarative_base

# 👇👇 IMPORTANT: Replace this with your actual password
DATABASE_URL = "postgresql://postgres:080920%40PA1io@localhost:5432/ifc_reuse"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

# -- Users table
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    email = Column(String)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    projects = relationship("Project", back_populates="user")

Base = declarative_base()  # This line overwrites the previous Base; move it before class definitions or remove the duplicate
# -- Projects table
class Project(Base):
    __tablename__ = "projects"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    location = Column(String, nullable=True)
    filename = Column(String, nullable=True)  # Keep this line
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
    components = relationship("Component", back_populates="project")

# -- Components table
class Component(Base):
    __tablename__ = "components"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"))
    category = Column(String)
    subcategory = Column(String)
    type = Column(String)
    name = Column(String)
    material = Column(String)
    location = Column(String)
    dimensions = Column(JSON)
    quantity = Column(Integer)
    reuse_flag = Column(Boolean, default=True)
    extra_metadata = Column(JSON)
    preview_url = Column(String)
    project = relationship("Project", back_populates="components")

# -- Call this to create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)