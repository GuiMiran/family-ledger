# @spectra BR-014
# @spectra OP-008
"""Operator-provisioned private invitation exchange; no public enrollment."""
import hashlib
import hmac
import os
import math
import re
import threading
import time
import uuid
from collections import deque
from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.core.auth import issue_family_token
from app.core.identity import ALIAS_QUARANTINE_FAMILY_ID
from app.infrastructure.db.orm import Family


class InvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invitation: str = Field(min_length=32, max_length=128)


def install_access_routes(api, database):
    # Configuration is operator-owned and loaded once; never accept a family ID from a client.
    digest = os.environ.get("FAMILY_INVITE_SHA256", "")
    try:
        target = uuid.UUID(os.environ.get("FAMILY_BOOTSTRAP_ID", ""))
        deadline = float(os.environ.get("FAMILY_INVITE_EXPIRES_AT", ""))
    except ValueError:
        target, deadline = None, 0
    configured = bool(re.fullmatch(r"[0-9a-f]{64}", digest)) and math.isfinite(deadline) and target is not None and target != ALIAS_QUARANTINE_FAMILY_ID and bool(api.state.jwt_secret) and len(api.state.jwt_secret) >= 32
    failures = deque(maxlen=20)
    lock = threading.Lock()

    @api.post("/api/v1/access/exchange")
    def exchange(body: InvitationRequest, session=Depends(database)):
        if not configured:
            raise HTTPException(503, "El acceso por invitación no está configurado.")
        now = time.time()
        with lock:
            while failures and failures[0] <= now - 60:
                failures.popleft()
            if len(failures) >= 20:
                raise HTTPException(429, "Espera un minuto antes de volver a intentarlo.", headers={"Retry-After": "60"})
            matches = hmac.compare_digest(hashlib.sha256(body.invitation.encode()).hexdigest(), digest)
            if not matches or now >= deadline:
                failures.append(now)
                raise HTTPException(401, "La invitación no es válida o ha caducado.")
        if session.get(Family, target) is None:
            raise HTTPException(401, "La invitación no es válida o ha caducado.")
        token = issue_family_token(api.state.jwt_secret, target, hours=8)
        return {"access_token": token, "token_type": "bearer", "expires_in": 28800}
