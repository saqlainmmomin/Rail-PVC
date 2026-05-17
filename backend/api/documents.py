"""P3-011: Document upload endpoint (Supabase Storage).

Stores files to Supabase Storage under tenant/{contract_id}/.
Max 50MB per file. No parsing in v1 — store only.
"""
import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import text

from api.deps import DbDep, TenantDep
from api.schemas import APIModel

router = APIRouter(tags=["documents"])

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
_SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
_STORAGE_BUCKET = "documents"
_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50MB

_VALID_FILE_TYPES = frozenset({"agreement", "mb", "bill", "recovery", "workbook", "other"})


async def _assert_contract_tenant(db, contract_id: UUID, tenant_id: UUID):
    row = (
        await db.execute(
            text("SELECT id FROM contracts WHERE id = :id AND tenant_id = :tid"),
            {"id": str(contract_id), "tid": str(tenant_id)},
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Contract not found")


class DocumentOut(APIModel):
    id: UUID
    contract_id: UUID
    file_type: str
    storage_path: str
    original_filename: str
    uploaded_at: str


@router.post(
    "/api/contracts/{contract_id}/documents",
    status_code=201,
    response_model=DocumentOut,
)
async def upload_document(
    contract_id: UUID,
    tenant_id: TenantDep,
    db: DbDep,
    file: UploadFile = File(...),
    file_type: str = Form(...),
):
    if file_type not in _VALID_FILE_TYPES:
        raise HTTPException(status_code=422, detail=f"file_type must be one of {sorted(_VALID_FILE_TYPES)}")

    await _assert_contract_tenant(db, contract_id, tenant_id)

    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit")

    filename = file.filename or "upload"
    storage_path = f"{tenant_id}/{contract_id}/{filename}"

    # Upload to Supabase Storage via REST API
    import httpx
    async with httpx.AsyncClient() as client:
        upload_url = f"{_SUPABASE_URL}/storage/v1/object/{_STORAGE_BUCKET}/{storage_path}"
        resp = await client.post(
            upload_url,
            content=content,
            headers={
                "Authorization": f"Bearer {_SUPABASE_SERVICE_KEY}",
                "Content-Type": file.content_type or "application/octet-stream",
                "x-upsert": "false",
            },
            timeout=60.0,
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Storage upload failed: {resp.text[:200]}",
        )

    row = (
        await db.execute(
            text("""
                INSERT INTO documents (contract_id, file_type, storage_path, original_filename)
                VALUES (:cid, :ftype::document_type, :path, :fname)
                RETURNING *
            """),
            {
                "cid": str(contract_id),
                "ftype": file_type,
                "path": storage_path,
                "fname": filename,
            },
        )
    ).one()
    await db.commit()

    return {
        "id": row.id,
        "contract_id": row.contract_id,
        "file_type": row.file_type,
        "storage_path": row.storage_path,
        "original_filename": row.original_filename,
        "uploaded_at": row.uploaded_at.isoformat(),
    }


@router.get("/api/contracts/{contract_id}/documents", response_model=list[DocumentOut])
async def list_documents(contract_id: UUID, tenant_id: TenantDep, db: DbDep):
    await _assert_contract_tenant(db, contract_id, tenant_id)
    rows = (
        await db.execute(
            text("SELECT * FROM documents WHERE contract_id = :cid ORDER BY uploaded_at DESC"),
            {"cid": str(contract_id)},
        )
    ).all()
    return [
        {
            "id": r.id, "contract_id": r.contract_id, "file_type": r.file_type,
            "storage_path": r.storage_path, "original_filename": r.original_filename,
            "uploaded_at": r.uploaded_at.isoformat(),
        }
        for r in rows
    ]
