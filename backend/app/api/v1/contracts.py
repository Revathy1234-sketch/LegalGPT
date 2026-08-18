from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from app.services.langchain_rag_service import langchain_rag_service
import logging
logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.models import User, Contract
from app.schemas.schemas import (
    ContractResponse,
    ContractQuestionRequest,
    ContractQuestionResponse,
)
from app.services.document_parser import DocumentParser
from app.services.vector_service import vector_service
from app.core.config import settings
import ast
import os
import time

import uuid
import google.generativeai as genai

router = APIRouter()
PDF_MIME_TYPE = "application/pdf"
PDF_SIGNATURE = b"%PDF-"


async def read_validated_pdf(file: UploadFile) -> bytes:
    if file.content_type != PDF_MIME_TYPE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files with application/pdf MIME type are supported."
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF contracts are supported."
        )

    content = await file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes."
        )

    if not content.startswith(PDF_SIGNATURE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content is not a valid PDF."
        )

    return content


@router.post("/upload", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def upload_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = await read_validated_pdf(file)

    # Ensure upload folder exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Generate unique filename
    contract_id = uuid.uuid4()
    file_extension = os.path.splitext(file.filename)[1]
    saved_filename = f"{contract_id}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, saved_filename)

    # Save PDF
    with open(file_path, "wb") as f:
        f.write(content)

    # Create database record
    db_contract = Contract(
        id=contract_id,
        uploaded_by=current_user.id,
        file_name=file.filename,
        storage_url=file_path,
        status="Processing"
    )

    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)

    # Process file
    try:
        # Extract text
        full_text = DocumentParser.extract_text_from_pdf(file_path)

        if not full_text or not full_text.strip():
            raise ValueError("Failed to extract any text from the PDF.")

        # Create chunks
        chunks = DocumentParser.get_parent_child_chunks(full_text)

        if not chunks:
            raise ValueError("No chunks were generated from the contract text.")

        if settings.DEBUG:
            logger.debug("DEBUG MODE: Limiting chunks to 20")
            chunks = chunks[:20]
        else:
            logger.info(f"PRODUCTION MODE: Processing all {len(chunks)} chunks")

        logger.info(f"Document length: {len(full_text)}")
        logger.info(f"Total chunks: {len(chunks)}")

        # Create embeddings + FAISS index
        try:
            vector_service.index_contract_chunks(
                str(contract_id),
                chunks,
                db=db
            )
            logger.info(f"✅ Indexed {len(chunks)} chunks")

        except Exception as embedding_error:
            logger.warning(f"⚠️ Embedding Error: {embedding_error}")

        # Generate contract summary
        summary = "No primary or fallback LLM providers configured."

        try:
            logger.info("Generating contract summary via LLMService...")
            prompt = f"""
Summarize the following document in a professional executive summary.

DOCUMENT:

{full_text[:settings.MAX_SUMMARY_CHARS]}
"""
            from app.services.llm_service import LLMService
            summary, _ = LLMService.invoke(prompt, {})
            if not summary or not summary.strip():
                summary = "No summary generated."
            logger.info("Summary generated successfully")
        except Exception as summary_error:
            logger.error("\n========== SUMMARY GENERATION ERROR ==========\n" + str(summary_error) + "\n==================================\n")
            summary = f"Summary generation failed: {str(summary_error)}"

        # Update database
        db_contract.summary = summary
        db_contract.status = "Processed"

        db.commit()
        db.refresh(db_contract)

    except Exception as e:
        db_contract.status = "Error"
        db_contract.summary = f"Error processing contract: {str(e)}"

        db.commit()
        db.refresh(db_contract)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process contract: {str(e)}"
        )

    return db_contract


@router.get("/", response_model=list[ContractResponse])
def get_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.organization_id:
        return (
            db.query(Contract)
            .join(User)
            .filter(
                User.organization_id ==
                current_user.organization_id
            )
            .all()
        )

    return (
        db.query(Contract)
        .filter(
            Contract.uploaded_by == current_user.id
        )
        .all()
    )


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contract = (
        db.query(Contract)
        .filter(Contract.id == contract_id)
        .first()
    )

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Contract not found"
        )

    # Authorization check
    if current_user.organization_id:
        uploader = (
            db.query(User)
            .filter(User.id == contract.uploaded_by)
            .first()
        )

        if (
            not uploader
            or uploader.organization_id != current_user.organization_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this contract"
            )

    elif contract.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this contract"
        )

    return contract


def load_contract_text_from_storage(contract: Contract) -> str:
    if contract.summary:
        return contract.summary
    if contract.storage_url and os.path.exists(contract.storage_url):
        try:
            return DocumentParser.extract_text_from_pdf(contract.storage_url)
        except Exception as e:
            logger.warning("Unable to load contract text from storage: %s", e)
    return ""


def get_authorized_contract(
    contract_id: uuid.UUID,
    current_user: User,
    db: Session
) -> Contract:
    contract = (
        db.query(Contract)
        .filter(Contract.id == contract_id)
        .first()
    )

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Contract not found"
        )

    if current_user.organization_id:
        uploader = (
            db.query(User)
            .filter(User.id == contract.uploaded_by)
            .first()
        )

        if (
            not uploader
            or uploader.organization_id != current_user.organization_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this contract"
            )

    elif contract.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this contract"
        )

    return contract
