import re

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.core.enums import UserRole

# Organization schemas
class OrganizationBase(BaseModel):
    name: str

class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str
    password: str
    organization_name: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one number")
        return value

class UserResponse(UserBase):
    id: UUID
    organization_id: Optional[UUID] = None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[UUID] = None

# Clause schemas
class ClauseBase(BaseModel):
    clause_type: str
    original_text: str
    modified_text: Optional[str] = None
    is_modified: bool = False
    confidence_score: float = 1.0

class ClauseResponse(ClauseBase):
    id: UUID
    contract_id: UUID

    class Config:
        from_attributes = True

class ClauseUpdate(BaseModel):
    modified_text: str
    is_modified: bool = True

# Risk Analysis schemas
class RiskAnalysisBase(BaseModel):
    overall_score: int
    risk_matrix: Optional[List[dict]] = None
    mitigation_plan: Optional[str] = None

class RiskAnalysisResponse(RiskAnalysisBase):
    id: UUID
    contract_id: UUID
    evaluated_at: datetime

    class Config:
        from_attributes = True

# Contract schemas
class ContractBase(BaseModel):
    file_name: str
    storage_url: Optional[str] = None
    status: str = "Pending"
    summary: Optional[str] = None

class ContractResponse(ContractBase):
    id: UUID
    uploaded_by: UUID
    created_at: datetime
    clauses: List[ClauseResponse] = []
    risk_analysis: Optional[RiskAnalysisResponse] = None

    class Config:
        from_attributes = True

class ContractQuestionSource(BaseModel):
    parent_id: str
    chunk_id: str
    child_text: str
    parent_text: str
    relevance_score: float

    class Config:
        from_attributes = True

class ContractQuestionRequest(BaseModel):
    question: str

class ContractQuestionResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[ContractQuestionSource]

    class Config:
        from_attributes = True

class ContractSummaryResponse(BaseModel):
    contract_id: UUID
    summary_text: str
    key_obligations: Optional[List[str]] = []
    important_dates: Optional[List[str]] = []
    parties_involved: Optional[List[str]] = []
    confidence: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ExtractedClause(BaseModel):
    title: str
    category: str
    content: str
    confidence_score: Optional[float] = 1.0

class ClauseExtractionResponse(BaseModel):
    clauses: List[ExtractedClause]

    class Config:
        from_attributes = True

class ComplianceIssue(BaseModel):
    framework: str
    clause_type: str
    status: str
    gap_analysis: str

class ComplianceResponse(BaseModel):
    compliant: bool
    issues: List[ComplianceIssue]
    recommendations: List[str]

    class Config:
        from_attributes = True
class CompareRequest(BaseModel):
    contract_a_id: UUID
    contract_b_id: UUID

class CompareResponse(BaseModel):
    similarities: List[str]
    differences: List[str]
    missing_clauses: List[str]
    risk_differences: List[str]
    summary: str

    class Config:
        from_attributes = True

# Chat schemas
class ChatMessageBase(BaseModel):
    sender_role: str # user, assistant, agent
    content: str
    metadata_json: Optional[dict] = None

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageResponse(ChatMessageBase):
    id: UUID
    session_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    contract_id: Optional[UUID] = None
    created_at: datetime
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True
