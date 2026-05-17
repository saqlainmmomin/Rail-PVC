"""P3-001: Supabase JWT auth middleware + tenant context extraction."""
import os
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import get_db

_SUPABASE_URL = os.environ["SUPABASE_URL"]
_SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

_bearer = HTTPBearer()


async def get_current_tenant(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UUID:
    """Verify Supabase JWT and return the caller's tenant_id.

    Every protected route depends on this. Returns 401 for invalid tokens,
    403 if the Supabase user has no tenant record yet.
    """
    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": _SUPABASE_SERVICE_KEY,
            },
            timeout=10.0,
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supabase_uid = resp.json().get("id")
    if not supabase_uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token payload")

    row = (
        await db.execute(
            text("SELECT tenant_id FROM users WHERE supabase_auth_id = :uid"),
            {"uid": supabase_uid},
        )
    ).one_or_none()

    if row is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not registered in any tenant")

    return UUID(str(row.tenant_id))


TenantDep = Annotated[UUID, Depends(get_current_tenant)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
