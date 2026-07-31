import json
import uuid

import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.v1.auth import resolve_user_from_token
from app.core.database import get_db
from app.models.models import Contract, User
from app.services.vector_service import vector_service
from app.core.config import settings

router = APIRouter()


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
            
            # Use Gemini to generate content and stream responses
            if settings.GEMINI_API_KEY:
                try:
                    model = genai.GenerativeModel(f"models/{settings.GEMINI_MODEL}")
                    response = model.generate_content(prompt, stream=True)
                    for chunk in response:
                        await websocket.send_text(json.dumps({"token": chunk.text}))
                except Exception as e:
                    await websocket.send_text(json.dumps({"token": f"\nError generating response: {str(e)}"}))
            else:
                await websocket.send_text(json.dumps({"token": "Mock assistant response token: No Gemini API Key set."}))
                
            await websocket.send_text(json.dumps({"status": "done"}))
    except WebSocketDisconnect:
        pass
