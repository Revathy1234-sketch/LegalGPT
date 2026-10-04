import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user, resolve_user_from_token
from app.core.database import get_db
from app.models.models import ChatMessage, ChatSession, Contract, User
from app.services.vector_service import vector_service
from app.core.config import settings

router = APIRouter()


# ============================
# AI Workspace (global) chat
# ============================

class WorkspaceChatRequest(BaseModel):
    message: str
    session_id: Optional[uuid.UUID] = None
    contract_id: Optional[uuid.UUID] = None


class WorkspaceChatResponse(BaseModel):
    session_id: uuid.UUID
    answer: str
    created_at: str
    error: bool = False
    sources: List[dict] = []


class WorkspaceSessionSummary(BaseModel):
    id: uuid.UUID
    title: str
    created_at: str
    updated_at: str
    message_count: int


class WorkspaceMessage(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: str
    metadata: Optional[dict] = None


WORKSPACE_SYSTEM_PROMPT = """You are LegalGPT, an expert AI legal assistant inside a contract-intelligence workspace.
You help lawyers and business users understand contracts, risks, obligations, compliance and negotiation strategy.

Rules:
- Be precise and professional; ground answers in contract/legal reasoning.
- If the user's question needs a specific contract, say which contract they should open for a deeper analysis.
- Structure longer answers with short headings or bullet points.
- Never invent clause numbers, party names, dates or amounts that were not provided.
- Keep answers concise (max ~300 words) unless asked for detail.
"""


def _workspace_session_for_user(
    db: Session,
    user: User,
    session_id: Optional[uuid.UUID],
) -> ChatSession:
    if session_id:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user.id,
                ChatSession.contract_id.is_(None),
            )
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return session

    session = ChatSession(user_id=user.id, contract_id=None)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _title_from_message(message: str) -> str:
    clean = " ".join(message.split())
    return clean[:70] + ("…" if len(clean) > 70 else "")


def _iso(dt: Optional[datetime]) -> str:
    return dt.isoformat() if dt else ""


@router.post("/workspace", response_model=WorkspaceChatResponse)
def workspace_chat(
    payload: WorkspaceChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ask a global (or contract-grounded) question. Every prompt and answer is
    persisted in a workspace conversation with an IST-renderable timestamp."""
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session = _workspace_session_for_user(db, current_user, payload.session_id)

    # Context: recent conversation so follow-up questions work
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
        .all()
    )
    history.reverse()

    db.add(ChatMessage(session_id=session.id, sender_role="user", content=message))
    db.commit()

    answer = ""
    error = False
    metadata: dict = {}

    try:
        if payload.contract_id:
            contract = (
                db.query(Contract)
                .filter(Contract.id == payload.contract_id)
                .first()
            )
            if not contract:
                raise HTTPException(status_code=404, detail="Contract not found")
            from app.agents.chat_agent import run_chat_agent
            from app.api.v1.analysis import _agent_payload

            try:
                import time
                start_time = time.time()
                response = run_chat_agent(str(payload.contract_id), message)
                result = _agent_payload(response)
                answer = str(result.get("answer", ""))
                latency_ms = (time.time() - start_time) * 1000
                
                # Fetch provider/model context if available from response, else fallback to settings
                provider = result.get("provider", settings.LLM_PROVIDER if hasattr(settings, 'LLM_PROVIDER') else "openrouter")
                model = result.get("model", settings.LLM_MODEL if hasattr(settings, 'LLM_MODEL') else "llama-3.3-70b-instruct")
                
                metadata = {
                    "citations": result.get("citations", []),
                    "sources": result.get("sources", []),
                    "confidence": result.get("confidence"),
                    "contract_id": str(payload.contract_id),
                    "provider": provider,
                    "model": model,
                    "agent": "chat_agent",
                    "latency_ms": latency_ms
                }
            except HTTPException as agent_exc:
                error = True
                answer = (
                    f"The contract chat agent could not answer ({agent_exc.detail}). "
                    "Check the backend logs / LLM provider keys and try again."
                )
                metadata = {"error": str(agent_exc.detail)}
        else:
            from app.services.llm_service import LLMService

            transcript = "\n".join(
                f"{'User' if m.sender_role == 'user' else 'Assistant'}: {m.content}"
                for m in history
            )
            prompt = (
                f"{WORKSPACE_SYSTEM_PROMPT}\n"
                f"\nConversation so far:\n{transcript}\n"
                f"\nUser: {message}\n\nAssistant:"
            )
            import time
            start_time = time.time()
            answer, usage = LLMService.invoke(prompt, {}, require_json=False)
            latency_ms = (time.time() - start_time) * 1000
            metadata = {
                "usage": usage,
                "provider": settings.LLM_PROVIDER if hasattr(settings, 'LLM_PROVIDER') else "openrouter",
                "model": settings.LLM_MODEL if hasattr(settings, 'LLM_MODEL') else "llama-3.3-70b-instruct",
                "agent": "workspace_chat",
                "latency_ms": latency_ms
            }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - surface LLM provider failures to the UI
        error = True
        answer = (
            "I could not reach any configured LLM provider (Gemini / OpenRouter / NVIDIA). "
            f"Technical detail: {type(exc).__name__}: {exc}. "
            "Check the backend .env API keys and try again."
        )
        metadata = {"error": str(exc)}

    db.add(
        ChatMessage(
            session_id=session.id,
            sender_role="assistant",
            content=answer,
            metadata_json=metadata,
        )
    )
    db.commit()

    last = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    return WorkspaceChatResponse(
        session_id=session.id,
        answer=answer,
        created_at=_iso(last.created_at if last else None),
        error=error,
        sources=(metadata.get("citations") or metadata.get("sources") or [])
        if isinstance(metadata, dict)
        else [],
    )


@router.get("/workspace/sessions", response_model=List[WorkspaceSessionSummary])
def list_workspace_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id, ChatSession.contract_id.is_(None))
        .all()
    )
    summaries: List[WorkspaceSessionSummary] = []
    for session in sessions:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        if not messages:
            continue
        first_user = next((m for m in messages if m.sender_role == "user"), None)
        summaries.append(
            WorkspaceSessionSummary(
                id=session.id,
                title=_title_from_message(first_user.content) if first_user else "Empty conversation",
                created_at=_iso(messages[0].created_at),
                updated_at=_iso(messages[-1].created_at),
                message_count=len(messages),
            )
        )
    summaries.sort(key=lambda s: s.updated_at, reverse=True)
    return summaries


@router.get("/workspace/sessions/{session_id}", response_model=List[WorkspaceMessage])
def get_workspace_session_messages(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
            ChatSession.contract_id.is_(None),
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        WorkspaceMessage(
            id=m.id,
            role=m.sender_role,
            content=m.content,
            created_at=_iso(m.created_at),
            metadata=m.metadata_json,
        )
        for m in messages
    ]


def get_websocket_token(websocket: WebSocket) -> str | None:
    authorization = websocket.headers.get("authorization")
    if authorization:
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() == "bearer" and credentials:
            return credentials
    return websocket.query_params.get("token")


def can_access_contract(user: User, contract: Contract, db: Session) -> bool:
    if user.organization_id:
        uploader = db.query(User).filter(User.id == contract.uploaded_by).first()
        return bool(uploader and uploader.organization_id == user.organization_id)
    return contract.uploaded_by == user.id


@router.websocket("/ws/{contract_id}")
async def websocket_chat(
    websocket: WebSocket,
    contract_id: str,
    db: Session = Depends(get_db),
):
    token = get_websocket_token(websocket)
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return

    try:
        current_user = resolve_user_from_token(token, db)
        parsed_contract_id = uuid.UUID(contract_id)
    except (HTTPException, TypeError, ValueError):
        await websocket.close(code=1008, reason="Invalid authentication or contract")
        return

    contract = db.query(Contract).filter(Contract.id == parsed_contract_id).first()
    if not contract or not can_access_contract(current_user, contract, db):
        await websocket.close(code=1008, reason="Contract access denied")
        return

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            query = payload.get("query", "")
            
            # Fetch context chunks from vector service
            chunks = vector_service.search_contract(contract_id, query, top_k=3)
            context = "\n".join([c["parent_text"] for c in chunks])
            
            prompt = f"""
            You are a Legal Assistant. Answer the user's question using the provided contract context.
            If the context does not contain the answer, say that you don't know based on the contract text.
            Keep your answer professional, concise, and accurate.
            
            Context:
            {context}
            
            Question:
            {query}
            """
            
            # Use LLMService to generate content and send response
            try:
                from app.services.llm_service import LLMService
                answer, _ = LLMService.invoke(prompt, {})
                await websocket.send_text(json.dumps({"token": answer}))
            except Exception as e:
                await websocket.send_text(json.dumps({"token": f"\nError generating response: {str(e)}"}))
                
            await websocket.send_text(json.dumps({"status": "done"}))
    except WebSocketDisconnect:
        pass
