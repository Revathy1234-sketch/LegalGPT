from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from app.services.langchain_rag_service import langchain_rag_service
import logging
logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
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


def process_contract_background(contract_id: str, file_path: str):
    db = SessionLocal()
    logger.info(f"background task started for {contract_id}")
    try:
        db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not db_contract:
            logger.error(f"Background task failed: Contract {contract_id} not found in DB")
            return

        # Extract text
        logger.info("text extraction started")
        full_text = DocumentParser.extract_text_from_pdf(file_path)
        logger.info("text extraction completed")

        if not full_text or not full_text.strip():
            raise ValueError("Failed to extract any text from the PDF.")

        # Create chunks
        logger.info("chunking started")
        chunks = DocumentParser.get_parent_child_chunks(full_text)
        logger.info("chunking completed")

        if not chunks:
            raise ValueError("No chunks were generated from the contract text.")

        if settings.DEBUG:
            logger.debug("DEBUG MODE: Limiting chunks to 20")
            chunks = chunks[:20]
        else:
            logger.info(f"PRODUCTION MODE: Processing all {len(chunks)} chunks")

        logger.info(f"Document length: {len(full_text)}")
        logger.info(f"Total chunks: {len(chunks)}")

        # Create embeddings + FAISS index (using pgvector)
        vector_service.index_contract_chunks(
            str(contract_id),
            chunks,
            db=db
        )
        logger.info(f"✅ Indexed {len(chunks)} chunks")

        # Update database to Processed before summary so overview is available immediately
        logger.info("setting Processed status before summary generation")
        db_contract.status = "Processed"
        db.commit()
        db.refresh(db_contract)

        # Run core agents in background to populate Overview automatically
        logger.info("Running core agents in background")
        from app.api.v1.analysis import run_summarize, knowledge_graph, extract_clauses, run_risk_analysis
        
        uploader = db.query(User).filter(User.id == db_contract.uploaded_by).first()
        contract_uuid = uuid.UUID(contract_id)
        
        try:
            logger.info("summary generation started via API")
            run_summarize(contract_id=contract_uuid, db=db, current_user=uploader)
        except Exception as e:
            logger.error(f"Background summary agent error: {e}")
            
        try:
            knowledge_graph(contract_id=contract_uuid, force=True, db=db, current_user=uploader)
        except Exception as e:
            logger.error(f"Background KG agent error: {e}")
            
        try:
            extract_clauses(contract_id=contract_uuid, force=True, db=db, current_user=uploader)
        except Exception as e:
            logger.error(f"Background clause agent error: {e}")
            
        try:
            run_risk_analysis(contract_id=contract_uuid, force=True, db=db, current_user=uploader)
        except Exception as e:
            logger.error(f"Background risk agent error: {e}")

        try:
            from app.api.v1.analysis import run_compliance_analysis
            run_compliance_analysis(contract_id=contract_uuid, force=True, db=db, current_user=uploader)
        except Exception as e:
            logger.error(f"Background compliance agent error: {e}")

        try:
            from app.api.v1.analysis import run_negotiation_analysis
            run_negotiation_analysis(contract_id=contract_uuid, force=True, db=db, current_user=uploader)
        except Exception as e:
            logger.error(f"Background negotiation agent error: {e}")

        # Cleanup local PDF file to save space
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up local PDF file: {file_path}")
        except Exception as cleanup_err:
            logger.warning(f"Failed to cleanup PDF file {file_path}: {cleanup_err}")

        logger.info(f"background task completed for {contract_id}")

    except Exception as e:
        import traceback
        logger.error(f"background task exception with full traceback: {traceback.format_exc()}")
        try:
            db.rollback()
            db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
            if db_contract:
                db_contract.status = "Error"
                db_contract.summary = f"Error processing contract: {str(e)}"
                db.commit()
        except Exception as commit_err:
            logger.error("Failed to persist contract error state: %s", commit_err)
    finally:
        db.close()


@router.post("/upload", response_model=ContractResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_contract(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info("upload request received")
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
    logger.info("PDF saved")

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
    logger.info("DB contract created")

    # Queue background processing
    background_tasks.add_task(process_contract_background, str(contract_id), file_path)

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
    
    # If the file was deleted (stateless), return empty string or error
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


@router.delete("/{contract_id}")
def delete_contract(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contract = get_authorized_contract(contract_id, current_user, db)
    
    try:
        if contract.storage_url and os.path.exists(contract.storage_url):
            try:
                os.remove(contract.storage_url)
                logger.info(f"Cleaned up local PDF file: {contract.storage_url}")
            except Exception as e:
                logger.warning(f"Failed to cleanup PDF file {contract.storage_url}: {e}")
                
        contract_id_str = str(contract_id)
        if contract_id_str in vector_service.chunk_cache:
            del vector_service.chunk_cache[contract_id_str]
            logger.info(f"Removed contract {contract_id_str} from chunk cache")
            
        db.delete(contract)
        db.commit()
        
        return {"message": "Contract deleted successfully", "contract_id": contract_id_str}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete contract {contract_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the contract: {str(e)}"
        )
