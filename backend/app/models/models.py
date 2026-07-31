import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import UserRole

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="organization")

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_class: [role.value for role in enum_class],
        ),
        nullable=False,
        default=UserRole.READER,
        server_default=UserRole.READER.value,
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    contracts = relationship("Contract", back_populates="uploader")
    chat_sessions = relationship("ChatSession", back_populates="user")

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    storage_url = Column(String(512), nullable=True)
    status = Column(String(50), default="Pending") # Pending, Processing, Processed, Error
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    uploader = relationship("User", back_populates="contracts")
    clauses = relationship("Clause", back_populates="contract", cascade="all, delete-orphan")
    risk_analysis = relationship("RiskAnalysis", uselist=False, back_populates="contract", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="contract", cascade="all, delete-orphan")
    contract_summary = relationship("ContractSummary", uselist=False, back_populates="contract", cascade="all, delete-orphan")
    clause_extractions = relationship("ContractClauseExtraction", back_populates="contract", cascade="all, delete-orphan")
    risk_assessments = relationship("ContractRiskAssessment", back_populates="contract", cascade="all, delete-orphan")
    embeddings = relationship("ContractEmbedding", back_populates="contract", cascade="all, delete-orphan")
    execution_logs = relationship("AgentExecutionLog", back_populates="contract", cascade="all, delete-orphan")

class Clause(Base):
    __tablename__ = "clauses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    clause_type = Column(String(100), nullable=False)
    original_text = Column(Text, nullable=False)
    modified_text = Column(Text, nullable=True)
    is_modified = Column(Boolean, default=False)
    confidence_score = Column(Float, default=1.0)

    contract = relationship("Contract", back_populates="clauses")

class RiskAnalysis(Base):
    __tablename__ = "risk_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    overall_score = Column(Integer, default=0) # 0 to 100
    risk_matrix = Column(JSONB, nullable=True) # JSON list of identified risks and levels
    mitigation_plan = Column(Text, nullable=True)
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="risk_analysis")

class ContractSummary(Base):
    __tablename__ = "contract_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False, unique=True)
    summary_text = Column(Text, nullable=True)
    key_obligations = Column(JSONB, nullable=True)
    important_dates = Column(JSONB, nullable=True)
    parties_involved = Column(JSONB, nullable=True)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="contract_summary")

class ContractClauseExtraction(Base):
    __tablename__ = "contract_clauses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    clause_type = Column(String(100), nullable=False)
    original_text = Column(Text, nullable=False)
    confidence_score = Column(Float, default=1.0)
    source_parent_id = Column(String(100), nullable=True)
    source_chunk_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="clause_extractions")

class ContractRiskAssessment(Base):
    __tablename__ = "contract_risks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    overall_score = Column(Integer, default=0)
    risk_matrix = Column(JSONB, nullable=True)
    mitigation_plan = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="risk_assessments")

class ContractEmbedding(Base):
    __tablename__ = "contract_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    chunk_id = Column(String(100), nullable=False)
    parent_id = Column(String(100), nullable=False)
    child_text = Column(Text, nullable=False)
    parent_text = Column(Text, nullable=False)
    embedding = Column(JSONB, nullable=True)
    relevance_source = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="embeddings")

class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True)
    agent_name = Column(String(100), nullable=False)
    task_type = Column(String(100), nullable=False)
    input_payload = Column(JSONB, nullable=True)
    output_payload = Column(JSONB, nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=True)
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="execution_logs")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    contract = relationship("Contract", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    sender_role = Column(String(50), nullable=False) # user, assistant, agent
    content = Column(Text, nullable=False)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
