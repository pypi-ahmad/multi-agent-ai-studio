from __future__ import annotations

from os import getenv
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import Document, User
from ai_studio.schemas.rag import (
    ConnectorIngestRequest,
    ConnectorIngestResponse,
    DocumentCreate,
    DocumentRead,
    RetrievalRequest,
    RetrievalResponse,
)
from ai_studio.services.rag_service import RagService
from ai_studio.state import get_app_state

router = APIRouter(prefix="/rag", tags=["rag"])


def _resolve_upload_dir() -> Path:
    configured = getenv("AI_STUDIO_UPLOAD_DIR", "").strip()
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend(
        [
            Path("/app/data/uploads"),
            Path("/home/ahmad/AI/multi-agent-ai-studio/data/uploads"),
            Path("/tmp/ai-studio-uploads"),
        ]
    )

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue

    # Final fallback: bubble up filesystem error at call site if even tmp is unavailable.
    return Path("/tmp/ai-studio-uploads")


@router.get("/documents", response_model=list[DocumentRead])
async def list_documents(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("rag.documents.list")),
) -> list[DocumentRead]:
    result = await session.execute(
        select(Document).where(Document.owner_id == user.id).order_by(Document.updated_at.desc())
    )
    return [DocumentRead.model_validate(item) for item in result.scalars().all()]


@router.post("/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("rag.documents.create")),
) -> DocumentRead:
    app_state = get_app_state()
    rag: RagService = app_state.rag_service
    doc = await rag.register_document(session, user.id, payload)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="rag.document.register",
        target_type="document",
        target_id=doc.id,
        details={"source_uri": doc.source_uri},
        commit=True,
    )
    return DocumentRead.model_validate(doc)


@router.get("/connectors")
async def list_connectors(
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("rag.connectors.list")),
) -> dict[str, list[dict[str, object]]]:
    return {
        "connectors": [
            {
                "name": "file_upload",
                "route": "/rag/documents/{document_id}/ingest",
                "formats": ["pdf", "docx", "md", "txt", "html", "csv", "xlsx"],
            },
            {
                "name": "github",
                "route": "/rag/connectors/ingest",
                "options": {"branch": "main", "max_files": 80, "max_file_bytes": 250000},
            },
            {
                "name": "web",
                "route": "/rag/connectors/ingest",
                "options": {"max_pages": 8, "max_depth": 1, "same_domain": True},
            },
        ]
    }


@router.post("/connectors/ingest", response_model=ConnectorIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_connector(
    payload: ConnectorIngestRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("rag.connector.ingest")),
) -> ConnectorIngestResponse:
    app_state = get_app_state()
    rag: RagService = app_state.rag_service
    try:
        document, chunks = await rag.ingest_connector(session, user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="rag.connector.ingest",
        target_type="document",
        target_id=document.id,
        details={"connector": payload.connector, "source_uri": payload.source_uri, "chunks_indexed": chunks},
        commit=True,
    )
    return ConnectorIngestResponse(document=DocumentRead.model_validate(document), chunks_indexed=chunks)


@router.post("/documents/{document_id}/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_document_file(
    document_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("rag.file.ingest")),
) -> dict[str, int]:
    uploads = _resolve_upload_dir()
    uploads.mkdir(parents=True, exist_ok=True)
    target = uploads / f"{document_id}-{file.filename}"
    target.write_bytes(await file.read())

    app_state = get_app_state()
    rag: RagService = app_state.rag_service
    try:
        chunks = await rag.ingest_local_file(session, user.id, document_id, target)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="rag.file.ingest",
        target_type="document",
        target_id=document_id,
        details={"filename": file.filename, "chunks_indexed": chunks},
        commit=True,
    )
    return {"chunks_indexed": chunks}


@router.post("/retrieve", response_model=RetrievalResponse)
async def retrieve(
    payload: RetrievalRequest,
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("rag.retrieve")),
) -> RetrievalResponse:
    app_state = get_app_state()
    rag: RagService = app_state.rag_service
    return await rag.retrieve(user.id, payload)
