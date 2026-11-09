"""Read-only anonymous public storefront adapter; no order or login operations."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import re
import time
import unicodedata
from urllib.parse import urlsplit

import httpx

from app.domain.shopping import PriceOffer, ShoppingProfile
from app.infrastructure.prices import CollectionResult, STORE_CATALOGUES

BASE = "https://tienda.mercadona.es"
SOURCE_NAME = "mercadona_public_storefront"
LEAF_CATEGORIES = (72, 77, 38, 40, 53, 118, 120)
MAX_BYTES = 2_000_000
MAX_PRODUCTS = 1000


class _FeedError(ValueError):
    pass


def _plain(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))


def _classify(name: str, leaf: int) -> str | None:
    n = _plain(name)
    def has(*terms):
        return any(term in n for term in terms)
    if leaf == 72:
        if has("puleva") and re.search(r"\bmax\b", n):
            return "puleva_max" if not has("cereal", "cacao", "chocolate", "vainilla") else None
        if (has("leche") and has("entera") 
                and not has("sin lactosa", "desnat", "fresca", "eco", "cabra", "cereal", "cacao", "proteina", "calcio", "omega")):
            return "milk_whole_uht" if has("uht", "esterilizada", "larga duracion") else "milk_whole_unspecified"
    if leaf == 77 and has("huevo") and not has("cocido", "liquid", "clara", "chocolate", "codorniz"):
        sizes = set(re.findall(r"\b(xl|l|m|s)\b", n))
        return "eggs_" + next(iter(sizes)) if len(sizes) == 1 else "eggs_size_pending"
    if leaf == 38 and has("pechuga") and has("pollo") and not has("pavo", "marinad", "adob", "empan", "reboz", "congel", "asada", "cocida", "salsa", "rellen", "ahum", "pincho", "cocin", "hierba", "sazon", "teriyaki", "barbacoa", "extra tiern", "salmuera", "preparado", "sazonad"):
        if has("sin hueso", "filete", "deshues"):
            return "chicken_breast_fresh_boneless"
    if leaf == 40 and has("filete", "bistec") and has("vacuno", "ternera", "vaca", "anojo") and not has("empan", "marinad", "adob", "congel", "hamburg"):
        return "beef_sliced_unknown_cut"
    if leaf == 53 and has("queso") and has("fresco", "burgos") and not has("batido", "cabra", "0%", "0 %", "desnat", "light", "sin lactosa", "hierba", "salmon"):
        return "cheese_fresh"
    if leaf == 118 and has("arroz") and has("largo") and not has("integral", "cocido", "vapor", "mezcla", "salsa", "basmati", "jazmin"):
        return "rice_long"
    if leaf == 120 and has("macarr", "espaguet", "spaghetti", "tallarin", "fusilli", "espiral", "penne", "fideo", "pasta", "tiburon") and not has("huevo", "sin gluten", "integral", "rellen", "fresca", "verdura", "lenteja", "garbanzo", "salsa", "arroz", "maiz", "soja", "quinoa", "sarraceno", "legumbre", "proteic"):
        return "pasta_dry_wheat"
    return None


def _number(value) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("missing numeric source field")
    value = Decimal(str(value))
    if not value.is_finite() or value < 0:
        raise ValueError("invalid numeric source field")
    return value


def _offer(product: dict, leaf: int, observed_at: datetime, postal_code: str | None,
           verified: bool, warehouse: str) -> PriceOffer | None:
    name = product["display_name"]
    if not isinstance(name, str):
        raise ValueError("invalid name")
    group = _classify(name, leaf)
    if group is None:
        return None
    instructions = product["price_instructions"]
    units = {"kg": "kg", "g": "g", "l": "l", "ml": "ml", "ud": "unit", "uds": "unit", "unidad": "unit", "un": "unit"}
    quantity = _number(instructions["unit_size"])
    unit = units.get(str(instructions["size_format"]).lower())
    if quantity <= 0 or unit is None:
        raise ValueError("missing pack quantity/unit")
    variable = instructions.get("approx_size") is True
    reference = None
    reference_unit = None
    if instructions.get("reference_price") is not None:
        reference = _number(instructions["reference_price"])
        reference_format = str(instructions.get("reference_format", "")).lower()
        if reference_format in ("kg", "l"):
            reference_unit = reference_format
        elif reference_format in ("ud", "uds", "unidad", "un"):
            reference_unit = "unit"
        elif reference_format in ("dz", "docena"):
            reference = (reference / 12).quantize(Decimal("0.000001"))
            reference_unit = "unit"
        else:
            reference = None
    url = product["share_url"]
    parsed = urlsplit(url)
    if parsed.query or parsed.fragment:
        raise ValueError("source link contains unneeded query data")
    # Storefront publication is not an in-stock guarantee.
    available = False if product.get("published") is False else None
    brand = "Puleva" if "puleva" in _plain(name) else ("Hacendado" if "hacendado" in _plain(name) else None)
    return PriceOffer(id=str(product["id"]), store="mercadona", product_name=name,
        comparison_group=group, pack_quantity=quantity, pack_unit=unit,
        price=_number(instructions["unit_price"]), price_includes_vat=True,
        variable_weight=variable, reference_unit_price_gross=reference,
        reference_unit=reference_unit, source_name=SOURCE_NAME, source_url=url,
        brand=brand, observed_at=observed_at, postal_code=postal_code,
        location_verified=verified, store_id=warehouse, available=available,
        conditions=["Approximate pack weight and estimated checkout outlay"] if variable else [])


def _products(data: dict):
    """Known category tree only, with bounded nesting and product count."""
    pending = [(data, 0)]
    visited = 0
    while pending:
        node, depth = pending.pop()
        visited += 1
        if visited > 1000 or depth > 8 or not isinstance(node, dict):
            raise _FeedError("invalid_data")
        products = node.get("products", [])
        children = node.get("categories", [])
        if not isinstance(products, list) or not isinstance(children, list):
            raise _FeedError("invalid_data")
        yield from products
        pending.extend((child, depth + 1) for child in children)


class MercadonaProvider:
    def __init__(self, *, transport: httpx.BaseTransport | None = None, client_factory=None,
                 proxy: str | None = None, use_env_proxy: bool = False):
        self._transport = transport
        self._factory = client_factory or httpx.Client
        self._proxy = proxy
        self._use_env_proxy = bool(use_env_proxy)

    def collect(self, profile: ShoppingProfile) -> CollectionResult:
        offers = []
        invalid = 0
        skipped = 0
        completed = 0
        enrichment_gaps = 0
        enrichment_attempts = 0
        selected = "mercadona" in profile.preferred_stores
        status = "store_not_selected"
        failure_reason = None
        zone_verified = False
        observed_postal_code = None
        started = time.monotonic()

        def fetch(client, method, path, **kwargs):
            if time.monotonic() - started > 45:
                raise _FeedError("source_unavailable")
            with client.stream(method, BASE + path, **kwargs) as response:
                if 300 <= response.status_code < 400:
                    raise _FeedError("source_redirect_rejected")
                if response.status_code != 200:
                    raise _FeedError("source_unavailable")
                if ("application/json" not in response.headers.get("content-type", "").lower()
                        or response.headers.get("content-encoding", "identity").lower() != "identity"):
                    raise _FeedError("invalid_data")
                content = bytearray()
                for chunk in response.iter_bytes(chunk_size=65536):
                    if time.monotonic() - started > 45:
                        raise _FeedError("source_unavailable")
                    content.extend(chunk)
                    if len(content) > MAX_BYTES:
                        raise _FeedError("response_too_large")
                body = json.loads(content)
                if not isinstance(body, dict):
                    raise _FeedError("invalid_data")
                return body, response.headers

        if selected:
            try:
                proxy_options = {"proxy": self._proxy} if self._proxy else {}
                with self._factory(transport=self._transport, follow_redirects=False,
                        timeout=httpx.Timeout(12, connect=5), trust_env=self._use_env_proxy,
                        headers={"Accept": "application/json", "Accept-Encoding": "identity"}, **proxy_options) as client:
                    _, headers = fetch(client, "PUT", "/api/postal-codes/actions/change-pc/",
                                       json={"new_postal_code": profile.postal_code})
                    echo = headers.get("x-customer-pc")
                    if echo and re.fullmatch(r"[0-9]{5}", echo):
                        observed_postal_code = echo
                    zone_verified = observed_postal_code == profile.postal_code
                    warehouse = headers.get("x-customer-wh", "")
                    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,32}", warehouse):
                        raise _FeedError("zone_unverified")
                    observed_at = datetime.now(timezone.utc)
                    seen_products = 0
                    for leaf in LEAF_CATEGORIES:
                        body, leaf_headers = fetch(client, "GET", f"/api/categories/{leaf}/",
                                                   params={"lang": "es", "wh": warehouse})
                        # A contradictory per-response zone invalidates this response.
                        leaf_echo = leaf_headers.get("x-customer-pc")
                        local = zone_verified and (leaf_echo is None or leaf_echo == profile.postal_code)
                        pc = leaf_echo if leaf_echo and re.fullmatch(r"[0-9]{5}", leaf_echo) else observed_postal_code
                        for product in _products(body):
                            seen_products += 1
                            if seen_products > MAX_PRODUCTS:
                                raise _FeedError("offer_limit_exceeded")
                            try:
                                offer = _offer(product, leaf, observed_at, pc, local, warehouse)
                                if offer is None:
                                    skipped += 1
                                else:
                                    offers.append(offer)
                            except (ValueError, TypeError, KeyError, InvalidOperation):
                                invalid += 1
                        completed += 1
                    # At most three per-product detail requests: evidence from one
                    # legal name must never classify the other same-title products.
                    for index, offer in list(enumerate(offers)):
                        if offer.comparison_group != "milk_whole_unspecified":
                            continue
                        if enrichment_attempts >= 3:
                            enrichment_gaps += 1
                            continue
                        if not re.fullmatch(r"[0-9]{1,20}", offer.id):
                            enrichment_gaps += 1
                            continue
                        enrichment_attempts += 1
                        try:
                            detail, detail_headers = fetch(client, "GET", f"/api/products/{offer.id}/",
                                                           params={"lang": "es", "wh": warehouse})
                            detail_zone = detail_headers.get("x-customer-pc")
                            if str(detail.get("id")) != offer.id or (detail_zone is not None and detail_zone != offer.postal_code):
                                raise _FeedError("invalid_data")
                            legal_name = detail.get("details", {}).get("legal_name")
                            if not isinstance(legal_name, str) or len(legal_name) > 500 or _classify(legal_name, 72) != "milk_whole_uht":
                                raise _FeedError("classification_unconfirmed")
                            offers[index] = offer.model_copy(update={"comparison_group": "milk_whole_uht"})
                        except (_FeedError, httpx.HTTPError, OSError, ValueError, TypeError, AttributeError, RecursionError):
                            enrichment_gaps += 1
                    status = ("observations_received" if any(o.location_verified for o in offers)
                              else "unlocalized" if offers else "invalid_data" if invalid else "no_offers")
            except _FeedError as exc:
                status = str(exc)
            except ImportError:
                status = "source_configuration_invalid"
            except (httpx.HTTPError, OSError):
                status = "source_unavailable"
            except (ValueError, UnicodeError, RecursionError):
                status = "invalid_data"
        if selected and completed < len(LEAF_CATEGORIES) and offers:
            failure_reason, status = status, "partial"
        coverage = []
        for store, catalogue in STORE_CATALOGUES.items():
            row = {"store": store, "status": status if store == "mercadona" else "source_not_configured",
                   "catalogue_url": catalogue}
            if store == "mercadona":
                row.update(completed_categories=completed, expected_categories=len(LEAF_CATEGORIES),
                           partial=selected and completed < len(LEAF_CATEGORIES), failure_reason=failure_reason, invalid_items=invalid,
                           enrichment_attempts=enrichment_attempts, enrichment_gaps=enrichment_gaps,
                           skipped_non_equivalent_items=skipped, zone_verified=zone_verified,
                           observed_postal_code=observed_postal_code)
            coverage.append(row)
        return CollectionResult(offers, coverage, SOURCE_NAME)
