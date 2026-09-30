from sqlalchemy import create_engine, Column, String, Boolean, JSON, DateTime, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class ActionRecord(Base):
    __tablename__ = "actions_catalog"
    action_id       = Column(String(100), primary_key=True)
    category        = Column(String(50),  nullable=False)
    summary         = Column(Text,        nullable=False)
    path            = Column(String(255), nullable=False)
    method          = Column(String(10),  nullable=False)
    is_mutation     = Column(Boolean,     default=False)
    parameters_schema = Column(JSON,      default=list)

class ExecutionLog(Base):
    __tablename__ = "execution_logs"
    id            = Column(String(36),  primary_key=True)
    action_id     = Column(String(100), nullable=False)
    http_status   = Column(String(10))
    payload       = Column(JSON)
    response_data = Column(JSON)
    created_at    = Column(DateTime, server_default=func.now())

engine       = create_engine(os.getenv("DATABASE_URL", "sqlite:///./badis_mcp.db"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized.")
