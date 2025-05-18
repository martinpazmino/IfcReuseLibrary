from sqlalchemy import create_engine, Column, String, Integer, Boolean, JSON, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import text

# Define Base once at the top
Base = declarative_base()

# 👇👇 IMPORTANT: Replace this with your actual password
DATABASE_URL = "postgresql://postgres:080920%40PA1io@localhost:5432/ifc_reuse"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# -- Projects table (defined first because User depends on it)
class Project(Base):
    __tablename__ = "projects"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    location = Column(String, nullable=True)
    filename = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
    components = relationship("Component", back_populates="project")
    user = relationship("User", back_populates="projects")  # Define after User class exists

# -- Users table (defined after Project)
class User(Base):
    __tablename__ = "users"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    email = Column(String)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    projects = relationship("Project", back_populates="user")

# -- Components table
class Component(Base):
    __tablename__ = "components"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
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