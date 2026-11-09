# @spectra BR-012
# @spectra BR-010
# @spectra BR-011
"""Source-backed shopping comparisons; no network access or purchase actions."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from enum import Enum
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator


class Store(str, Enum):
    mercadona = "mercadona"
    makro = "makro"
    lidl = "lidl"
    dia = "dia"
    carrefour = "carrefour"
    condis = "condis"


class BasketItem(BaseModel):
    key: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=300)
    comparison_group: str = Field(min_length=1, max_length=128)
    unit: str = Field(pattern=r"^(kg|l|unit)$")
    desired_quantity: Decimal = Field(gt=0, le=1000000, max_digits=13, decimal_places=6, allow_inf_nan=False)
    brand: str | None = Field(default=None, max_length=200)
    ean: str | None = Field(default=None, max_length=32)



class ShoppingProfile(BaseModel):
    postal_code: str | None = Field(default=None, pattern=r"^[0-9]{5}$")
    family_name: str | None = Field(default=None, min_length=1, max_length=200)
    preferred_stores: list[Store] = Field(default_factory=list, max_length=6)
    basket: list[BasketItem] = Field(default_factory=list, max_length=30)
    club_memberships: list[Store] = Field(default_factory=list, max_length=6)
    coupons_enabled: bool = False
    max_age_hours: int = Field(default=24, gt=0, le=168)
    max_budget: Decimal | None = Field(default=None, ge=0, le=1000000, max_digits=13, decimal_places=6, allow_inf_nan=False)

    @field_validator("preferred_stores", "club_memberships", mode="before")
    @classmethod
    def deduplicate_stores(cls, value):
        if isinstance(value, (list, tuple)):
            unique = []
            for store in value:
                if store not in unique:
                    unique.append(store)
            return unique
        return value

    @field_validator("family_name")
    @classmethod
    def nonblank_family_name(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("family_name must not be blank")
        return value

    @property
    def configured(self) -> bool:
        return bool(self.postal_code and self.preferred_stores and self.basket)

    @model_validator(mode="after")
    def unique_keys(self):
        if len({item.key for item in self.basket}) != len(self.basket):
            raise ValueError("basket keys must be unique")
        return self


_HOSTS = {
    Store.mercadona: ("mercadona.es", "mercadona.com"),
    Store.makro: ("makro.es",),
    Store.lidl: ("lidl.es",),
    Store.dia: ("dia.es",),
    Store.carrefour: ("carrefour.es",),
    Store.condis: ("condis.es", "condisline.com"),
}


class PriceOffer(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    store: Store
    product_name: str = Field(min_length=1, max_length=500)
    comparison_group: str = Field(min_length=1, max_length=128)
    pack_quantity: Decimal = Field(gt=0, le=1000000, max_digits=13, decimal_places=6, allow_inf_nan=False)
    pack_unit: str = Field(pattern=r"^(kg|g|l|ml|unit)$")
    packs_required: int = Field(default=1, ge=1, le=10000)
    price: Decimal = Field(ge=0, le=1000000, max_digits=13, decimal_places=6, allow_inf_nan=False)
    price_includes_vat: bool = True
    vat_rate: Decimal | None = Field(default=None, ge=0, le=1, max_digits=7, decimal_places=6, allow_inf_nan=False)
    brand: str | None = Field(default=None, max_length=200)
    ean: str | None = Field(default=None, max_length=32)
    club_required: bool = False
    coupon_required: bool = False
    cashback: Decimal = Field(default=Decimal("0"), ge=0, le=1000000, max_digits=13, decimal_places=6, allow_inf_nan=False)
    variable_weight: bool = False
    reference_unit_price_gross: Decimal | None = Field(
        default=None, ge=-1000000, le=1000000, max_digits=13, decimal_places=6, allow_inf_nan=False)
    reference_unit: str | None = Field(default=None, pattern=r"^(kg|l|unit)$")
    conditions: list[Annotated[str, Field(max_length=500)]] = Field(default_factory=list, max_length=20)
    source_url: str = Field(max_length=2048)
    source_name: str = Field(min_length=1, max_length=300)
    observed_at: datetime
    postal_code: str | None = Field(default=None, pattern=r"^[0-9]{5}$")
    location_verified: bool = False
    store_id: str | None = Field(default=None, max_length=200)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    available: bool | None = None

    @field_validator("observed_at", "valid_from", "valid_until")
    @classmethod
    def timezone_required(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamp must include timezone")
        return value

    @model_validator(mode="after")
    def safe_source(self):
        url = urlsplit(self.source_url)
        host = (url.hostname or "").lower()
        if (url.scheme != "https" or url.username or url.password or url.port not in (None, 443)
                or not any(host == domain or host.endswith("." + domain) for domain in _HOSTS[self.store])):
            raise ValueError("source_url must be HTTPS on the selected chain's public domain")
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValueError("promotion dates are reversed")
        return self


def _number(value: Decimal) -> str:
    return format(value, "f")


def compare(profile: ShoppingProfile, offers: list[PriceOffer], now: datetime | None = None) -> dict:
    """Rank compatible verified-local observations, preserving gaps and references.

    ``price`` is the cost of the entire minimum bundle (packs_required packs).
    VAT rates are fractions (0.10 = 10%). Cashback never reduces checkout cost.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include timezone")
    latest = {}
    ambiguous = set()
    for offer in offers:
        key = (offer.store, offer.id)
        if key not in latest or offer.observed_at > latest[key].observed_at:
            latest[key] = offer
            ambiguous.discard(key)
        elif offer.observed_at == latest[key].observed_at and offer != latest[key]:
            ambiguous.add(key)
    results = []
    units = {"kg": ("kg", Decimal(1)), "g": ("kg", Decimal("0.001")),
             "l": ("l", Decimal(1)), "ml": ("l", Decimal("0.001")),
             "unit": ("unit", Decimal(1))}
    for item in profile.basket:
        eligible, references, excluded = [], [], []
        for offer in latest.values():
            reasons = []
            if (offer.store, offer.id) in ambiguous:
                reasons.append("ambiguous_duplicate")
            if offer.store not in profile.preferred_stores:
                reasons.append("store_not_selected")
            if offer.comparison_group != item.comparison_group:
                reasons.append("comparison_group_mismatch")
            if item.comparison_group == "eggs_size_pending":
                reasons.append("egg_size_pending")
            if item.brand and (offer.brand or "").casefold().strip() != item.brand.casefold().strip():
                reasons.append("brand_mismatch")
            if item.ean and offer.ean != item.ean:
                reasons.append("ean_mismatch")
            unit, factor = units[offer.pack_unit]
            if unit != item.unit:
                reasons.append("incompatible_unit")
            if offer.variable_weight:
                if offer.reference_unit_price_gross is None or offer.reference_unit_price_gross <= 0:
                    reasons.append("variable_weight_reference_missing_or_invalid")
                if offer.reference_unit != unit or offer.reference_unit != item.unit:
                    reasons.append("variable_weight_reference_unit_mismatch")
            if not offer.price_includes_vat and offer.vat_rate is None:
                reasons.append("vat_unknown")
            age_hours = Decimal(str((now - offer.observed_at).total_seconds())) / Decimal(3600)
            if age_hours < 0:
                reasons.append("future_observation")
            elif age_hours > profile.max_age_hours:
                reasons.append("stale_observation")
            if offer.valid_from and now < offer.valid_from:
                reasons.append("promotion_not_started")
            if offer.valid_until and now > offer.valid_until:
                reasons.append("promotion_expired")
            if offer.club_required and offer.store not in profile.club_memberships:
                reasons.append("club_required")
            if offer.coupon_required and not profile.coupons_enabled:
                reasons.append("coupon_required")
            if offer.available is False:
                reasons.append("unavailable")
            row = offer.model_dump(mode="json")
            if reasons:
                row["reasons"] = reasons
                excluded.append(row)
                continue
            gross = offer.price if offer.price_includes_vat else offer.price * (1 + offer.vat_rate)
            quantity = offer.pack_quantity * factor * offer.packs_required
            bundles = (item.desired_quantity / quantity).to_integral_value(rounding=ROUND_CEILING)
            row.update(gross_bundle_price=_number(gross), bundle_quantity=_number(quantity),
                       comparison_unit=unit,
                       unit_price=_number(offer.reference_unit_price_gross if offer.variable_weight else gross / quantity),
                       outlay_estimated=offer.variable_weight,
                       required_bundles=int(bundles), required_outlay=_number(bundles * gross),
                       overbuy_quantity=_number(bundles * quantity - item.desired_quantity))
            if not offer.location_verified or offer.postal_code is None:
                row["reasons"] = ["unverified_location"]
                references.append(row)
            elif offer.postal_code != profile.postal_code:
                row["reasons"] = ["postcode_mismatch"]
                excluded.append(row)
            else:
                eligible.append(row)
        def rank(row):
            return (Decimal(row["unit_price"]), Decimal(row["required_outlay"]), row["store"], row["id"])
        eligible.sort(key=rank)
        references.sort(key=rank)
        results.append({"key": item.key, "label": item.label, "top_offers": eligible[:3],
                        "per_store": [{"store": store.value, "offers": [row for row in eligible if row["store"] == store.value][:3]}
                                      for store in dict.fromkeys(profile.preferred_stores)],
                        "eligible_offers": eligible, "references": references, "excluded": excluded})
    return {"postal_code": profile.postal_code, "coverage": sum(bool(item["eligible_offers"]) for item in results),
            "items": results}
