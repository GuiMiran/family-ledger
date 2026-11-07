# @spectra BR-007
"""Offline-issued, expiring family-scoped access tokens; no public token minting."""
from datetime import datetime, timedelta, timezone
import uuid

import jwt
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends
from app.core.identity import ALIAS_QUARANTINE_FAMILY_ID

bearer = HTTPBearer(auto_error=False)
ISSUER = "family-ledger-admin"
AUDIENCE = "family-ledger"


def issue_family_token(secret: str, family_id: uuid.UUID, hours: int = 8) -> str:
    if family_id == ALIAS_QUARANTINE_FAMILY_ID:
        raise ValueError("Reserved quarantine family cannot authenticate")
    if len(secret) < 32 or not 1 <= hours <= 24:
        raise ValueError("Use a JWT secret of at least 32 characters and a lifetime of 1–24 hours")
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(family_id), "family_id": str(family_id),
                       "iss": ISSUER, "aud": AUDIENCE, "iat": now,
                       "exp": now + timedelta(hours=hours)}, secret, algorithm="HS256")


def current_family(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> uuid.UUID:
    secret = request.app.state.jwt_secret
    if not secret or len(secret) < 32:
        raise HTTPException(503, "Family access is not configured")
    if not credentials:
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(credentials.credentials, secret, algorithms=["HS256"],
                            issuer=ISSUER, audience=AUDIENCE,
                            options={"require": ["exp", "iat", "sub", "family_id", "iss", "aud"]})
        family_id = uuid.UUID(claims["family_id"])
        if family_id == ALIAS_QUARANTINE_FAMILY_ID:
            raise ValueError("Reserved identity")
        if claims["sub"] != str(family_id):
            raise ValueError("Invalid subject")
        return family_id
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"}) from None
