# @spectra US-006
# @spectra US-007
# @spectra INV-006
# @spectra OP-005
"""Family-scoped comparison commands. Source endpoints are never client supplied."""
import uuid
from datetime import datetime, timezone
from fastapi import Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.application.shopping_agent import advise
from app.core.auth import current_family
from app.domain.shopping import PriceOffer, ShoppingProfile, compare
from app.infrastructure.db.orm import Family, PriceObservationRow, ShoppingAuditRow, ShoppingProfileRow
from app.infrastructure.prices import CollectionResult, PriceFeedProvider


class ShoppingCollector:
    def __init__(self):
        from app.infrastructure.mercadona import MercadonaProvider
        import os
        self.public = MercadonaProvider(proxy=os.environ.get("MERCADONA_OUTBOUND_PROXY"),
            use_env_proxy=os.environ.get("MERCADONA_USE_ENV_PROXY") == "1")
        self.feed = PriceFeedProvider()

    def collect(self, profile):
        # One request per configured adapter. No agent retry loop or arbitrary tool calls.
        public = self.public.collect(profile)
        feed = self.feed.collect(profile)
        coverage = []
        for store in profile.preferred_stores:
            candidates = [entry for entry in public.coverage + feed.coverage if entry["store"] == store.value]
            chosen = next((entry for entry in reversed(candidates) if entry["status"] in {"observations_received", "partial", "unlocalized"}), None)
            if chosen is None:
                chosen = next((entry for entry in candidates if entry["status"] != "source_not_configured"), None)
            coverage.append(chosen or {"store": store.value, "status": "source_not_configured"})
        return CollectionResult(public.offers + feed.offers, coverage, "combined")


def install_shopping_routes(api, database, collector=None):
    api.state.shopping_collector = collector

    def profile_for(session, family_id):
        if session.get(Family, family_id) is None:
            raise HTTPException(403, "Family is not provisioned")
        row = session.get(ShoppingProfileRow, family_id)
        return ShoppingProfile.model_validate(row.payload) if row else ShoppingProfile()

    def view(session, family_id, profile):
        rows = session.scalars(select(PriceObservationRow).where(PriceObservationRow.family_id == family_id)).all()
        offers = [PriceOffer.model_validate(row.payload) for row in rows]
        last = session.scalar(select(ShoppingAuditRow).where(ShoppingAuditRow.family_id == family_id)
                              .order_by(ShoppingAuditRow.created_at.desc(), ShoppingAuditRow.id.desc()).limit(1))
        coverage = last.payload.get("coverage", []) if last else [
            {"store": store.value, "status": "not_refreshed"} for store in profile.preferred_stores]
        # A saved profile change invalidates coverage for the old collection context.
        if last and last.payload.get("profile") != profile.model_dump(mode="json"):
            coverage = [{"store": store.value, "status": "not_refreshed"} for store in profile.preferred_stores]
        return {"comparison": compare(profile, offers), "coverage": coverage}

    @api.get("/api/v1/shopping/profile")
    def get_profile(family_id: uuid.UUID = Depends(current_family), session: Session = Depends(database)):
        return profile_for(session, family_id).model_dump(mode="json")

    @api.put("/api/v1/shopping/profile")
    def save_profile(body: ShoppingProfile, family_id: uuid.UUID = Depends(current_family), session: Session = Depends(database)):
        profile_for(session, family_id)
        session.execute(select(Family).where(Family.id == family_id).with_for_update()).scalar_one()
        row = session.get(ShoppingProfileRow, family_id)
        if row:
            row.payload = body.model_dump(mode="json")
        else:
            session.add(ShoppingProfileRow(family_id=family_id, payload=body.model_dump(mode="json")))
        session.commit()
        return body.model_dump(mode="json")

    @api.get("/api/v1/shopping/compare")
    def get_comparison(family_id: uuid.UUID = Depends(current_family), session: Session = Depends(database)):
        return view(session, family_id, profile_for(session, family_id))

    def collect(session, family_id):
        profile = profile_for(session, family_id)
        # Release read transaction while the bounded network collectors run.
        session.rollback()
        configured = api.state.shopping_collector or ShoppingCollector()
        collected = configured.collect(profile)
        if len(collected.offers) > 2000:
            raise HTTPException(502, "Price source exceeded observation limit")
        # Replace this family's snapshot, not another family's quotes. No unbounded history growth.
        with session.begin():
            session.execute(select(Family).where(Family.id == family_id).with_for_update()).scalar_one()
            current = profile_for(session, family_id)
            if current != profile:
                raise HTTPException(409, "Shopping profile changed during refresh; retry")
            session.execute(delete(PriceObservationRow).where(PriceObservationRow.family_id == family_id))
            for offer in collected.offers:
                session.add(PriceObservationRow(family_id=family_id, payload=offer.model_dump(mode="json")))
            compared = compare(profile, collected.offers)
            audit = {"profile": profile.model_dump(mode="json"), "coverage": collected.coverage,
                     "observed_at": datetime.now(timezone.utc).isoformat(), "observation_count": len(collected.offers)}
            session.add(ShoppingAuditRow(family_id=family_id, payload=audit))
            session.flush()
        return profile, {"comparison": compared, "coverage": collected.coverage}

    @api.post("/api/v1/shopping/refresh")
    def refresh(family_id: uuid.UUID = Depends(current_family), session: Session = Depends(database)):
        _, result = collect(session, family_id)
        return result

    @api.post("/api/v1/shopping/agent")
    def shopping_agent(family_id: uuid.UUID = Depends(current_family), session: Session = Depends(database)):
        profile, result = collect(session, family_id)
        result["agent"] = advise(profile, result["comparison"])
        with session.begin():
            row = ShoppingAuditRow(family_id=family_id, payload={"profile": profile.model_dump(mode="json"),
                "coverage": result["coverage"], "agent": result["agent"]})
            session.add(row)
            session.flush()
            result["audit_id"] = str(row.id)
        return result
