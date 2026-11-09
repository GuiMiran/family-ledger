"""Synthetic storefront fixtures, never live price evidence."""
from datetime import datetime, timezone
from decimal import Decimal
import json

import httpx
import pytest

from app.domain.shopping import ShoppingProfile, compare
from app.infrastructure.mercadona import LEAF_CATEGORIES, MAX_BYTES, MercadonaProvider, _classify


def product(name="Leche entera UHT Hacendado", **price):
    return {"id": "synthetic", "display_name": name,
            "share_url": "https://tienda.mercadona.es/product/123/synthetic",
            "published": True, "price_instructions": dict(unit_price="6.60", unit_size="6", size_format="l", is_pack=True, approx_size=False, reference_price="1.10", reference_format="l", **price)}


def collect(fixtures=None, zone="08038", leaf_zone=None, failing_leaf=None):
    requests = []
    def handler(request):
        requests.append(request)
        if request.method == "PUT":
            assert json.loads(request.content) == {"new_postal_code": "08038"}
            headers = {"x-customer-wh": "bcn1"}
            if zone is not None:
                headers["x-customer-pc"] = zone
            return httpx.Response(200, json={}, headers=headers)
        leaf = int(request.url.path.strip("/").split("/")[-1])
        assert request.url.params["wh"] == "bcn1"
        assert request.url.params["lang"] == "es"
        if leaf == failing_leaf:
            return httpx.Response(503)
        headers = {"x-customer-pc": leaf_zone} if leaf_zone else {}
        return httpx.Response(200, headers=headers, json={"categories": [{"products": (fixtures or {}).get(leaf, [])}]})
    return MercadonaProvider(transport=httpx.MockTransport(handler)).collect(ShoppingProfile()), requests


def test_zone_proof_pack_six_and_gross_normalization():
    result, requests = collect({72: [product()]})
    assert len(requests) == 8
    assert [int(r.url.path.strip("/").split("/")[-1]) for r in requests[1:]] == list(LEAF_CATEGORIES)
    offer = result.offers[0]
    assert offer.location_verified and offer.postal_code == "08038"
    assert offer.store_id == "bcn1"
    assert offer.available is None  # Published never establishes stock.
    assert offer.pack_quantity == 6 and offer.packs_required == 1
    assert offer.price == Decimal("6.60") and offer.price_includes_vat
    result = compare(ShoppingProfile(), result.offers)
    row = result["items"][0]["top_offers"][0]
    assert Decimal(row["unit_price"]) == Decimal("1.10")
    assert Decimal(row["required_outlay"]) == Decimal("6.60")


@pytest.mark.parametrize("zone", [None, "08001", "untrusted"])
def test_zone_missing_wrong_or_invalid_never_becomes_local(zone):
    result, _ = collect({72: [product()]}, zone=zone)
    assert result.offers[0].location_verified is False
    assert result.offers[0].postal_code == (zone if zone == "08001" else None)
    assert compare(ShoppingProfile(), result.offers)["coverage"] == 0
    assert result.coverage[0]["status"] == "unlocalized"


def test_contradictory_category_zone_is_preserved_unverified():
    result, _ = collect({72: [product()]}, leaf_zone="08001")
    assert result.offers[0].postal_code == "08001"
    assert not result.offers[0].location_verified


def test_variable_weight_uses_source_reference_not_rounded_pack_division():
    p = product("Filetes pechuga de pollo")
    p["price_instructions"].update(unit_price="4.08", unit_size="0.53", size_format="kg", approx_size=True, reference_price="7.70", reference_format="kg")
    result, _ = collect({38: [p]})
    offer = result.offers[0]
    assert offer.variable_weight and offer.reference_unit_price_gross == Decimal("7.70")
    rows = compare(ShoppingProfile(), result.offers)["items"][5]["top_offers"]
    assert Decimal(rows[0]["unit_price"]) == Decimal("7.70")
    assert rows[0]["outlay_estimated"] is True
    assert Decimal(rows[0]["unit_price"]) != Decimal("4.08") / Decimal("0.53")


def test_eggs_dozen_reference_and_exact_size_group():
    p = product("Huevos frescos L Hacendado")
    p["price_instructions"].update(unit_price="2.10", unit_size="12", size_format="ud", reference_price="2.10", reference_format="dz")
    result, _ = collect({77: [p]})
    assert result.offers[0].comparison_group == "eggs_l"
    assert result.offers[0].reference_unit_price_gross == Decimal("0.175000")
    assert compare(ShoppingProfile(), result.offers)["coverage"] == 0  # Size remains a household decision.


def test_unpublished_is_unavailable_but_published_is_unknown():
    p = product()
    p["published"] = False
    result, _ = collect({72: [p]})
    assert result.offers[0].available is False
    assert "unavailable" in compare(ShoppingProfile(), result.offers)["items"][0]["excluded"][0]["reasons"]


@pytest.mark.parametrize("name,leaf,expected", [
    ("Huevos frescos M/L Hacendado", 77, "eggs_size_pending"),
    ("Leche entera Hacendado", 72, "milk_whole_unspecified"),
    ("Leche entera sin lactosa UHT", 72, None),
    ("Leche fresca entera", 72, None),
    ("Leche entera UHT ecológica", 72, None),
    ("Leche Puleva Max", 72, "puleva_max"),
    ("Puleva Max cereales", 72, None),
    ("Puleva Max cacao", 72, None),
    ("Filetes pechuga de pollo", 38, "chicken_breast_fresh_boneless"),
    ("Pechuga de pollo", 38, None),
    ("Filetes pechuga pollo extra tiernos", 38, None),
    ("Filetes pechuga pollo con salmuera", 38, None),
    ("Preparado filetes pechuga pollo", 38, None),
    ("Filetes pechuga pollo sazonados", 38, None),
    ("Filetes pechuga pavo", 38, None),
    ("Filetes pechuga pollo marinados", 38, None),
    ("Filetes pechuga pollo empanados", 38, None),
    ("Filetes pechuga pollo congelados", 38, None),
    ("Filetes babilla ternera", 40, "beef_sliced_unknown_cut"),
    ("Queso fresco Burgos Hacendado", 53, "cheese_fresh"),
    ("Queso fresco batido", 53, None),
    ("Queso fresco cabra", 53, None),
    ("Queso fresco 0%", 53, None),
    ("Arroz largo Hacendado", 118, "rice_long"),
    ("Arroz largo integral", 118, None),
    ("Macarrones Hacendado", 120, "pasta_dry_wheat"),
    ("Tallarines al huevo", 120, None),
    ("Macarrones sin gluten", 120, None),
    ("Pasta rellena", 120, None),
])
def test_strict_variants(name, leaf, expected):
    assert _classify(name, leaf) == expected


def test_failure_stops_further_requests_and_keeps_partial_observations():
    result, requests = collect({72: [product()]}, failing_leaf=77)
    assert len(requests) == 3
    assert len(result.offers) == 1
    assert result.coverage[0]["partial"] is True
    assert result.coverage[0]["completed_categories"] == 1
    assert result.coverage[0]["status"] == "partial"
    assert result.coverage[0]["failure_reason"] == "source_unavailable"
    assert all(row["status"] == "source_not_configured" for row in result.coverage[1:])


def test_invalid_items_count_and_no_quantity_invention():
    bad = product()
    del bad["price_instructions"]["unit_size"]
    result, _ = collect({72: [bad, {"display_name": "Leche entera UHT"}]})
    assert not result.offers
    assert result.coverage[0]["invalid_items"] == 2
    assert result.coverage[0]["status"] == "invalid_data"


@pytest.mark.parametrize("kind,expected", [("redirect", "source_redirect_rejected"), ("size", "response_too_large"), ("outage", "source_unavailable")])
def test_bounds_and_no_redirect_follow(kind, expected):
    calls = []
    def handler(request):
        calls.append(request)
        if kind == "redirect":
            return httpx.Response(302, headers={"location": "https://elsewhere.example"})
        if kind == "size":
            return httpx.Response(200, headers={"content-type": "application/json"}, content=b" " * (MAX_BYTES + 1))
        raise httpx.ReadTimeout("not leaked")
    result = MercadonaProvider(transport=httpx.MockTransport(handler)).collect(ShoppingProfile())
    assert len(calls) == 1
    assert result.coverage[0]["status"] == expected
    assert not result.offers


def test_mercadona_not_selected_performs_no_requests():
    def handler(_):
        pytest.fail("store not selected")
    result = MercadonaProvider(transport=httpx.MockTransport(handler)).collect(ShoppingProfile(preferred_stores=["lidl"]))
    assert result.coverage[0]["status"] == "store_not_selected"


def test_explicit_proxy_only_and_no_implicit_environment_proxy():
    seen = []
    def factory(**kwargs):
        seen.append(dict(kwargs))
        kwargs.pop("proxy", None)
        return httpx.Client(**kwargs)
    transport = httpx.MockTransport(lambda _: httpx.Response(503))
    MercadonaProvider(transport=transport, client_factory=factory).collect(ShoppingProfile())
    MercadonaProvider(transport=transport, client_factory=factory, proxy="http://operator-proxy.example:8080").collect(ShoppingProfile())
    assert "proxy" not in seen[0]
    assert seen[1]["proxy"] == "http://operator-proxy.example:8080"
    assert all(options["trust_env"] is False for options in seen)


def test_total_product_limit_reports_partial_not_complete(monkeypatch):
    monkeypatch.setattr("app.infrastructure.mercadona.MAX_PRODUCTS", 1)
    result, requests = collect({72: [product(), product()]})
    assert len(result.offers) == 1
    assert result.coverage[0]["status"] == "partial"
    assert result.coverage[0]["failure_reason"] == "offer_limit_exceeded"
    assert len(requests) == 2


@pytest.mark.parametrize("mode,expected,gaps", [("legal_uht", "milk_whole_uht", 0), ("absent", "milk_whole_unspecified", 1), ("wrong_id", "milk_whole_unspecified", 1), ("wrong_zone", "milk_whole_unspecified", 1), ("outage", "milk_whole_unspecified", 1)])
def test_milk_enrichment_is_per_product_verified_legal_name(mode, expected, gaps):
    requests = []
    def handler(request):
        requests.append(request)
        if request.method == "PUT":
            return httpx.Response(200, json={}, headers={"x-customer-pc": "08038", "x-customer-wh": "bcn1"})
        if "/products/" in request.url.path:
            if mode == "outage":
                return httpx.Response(503)
            body = {"id": "123", "details": {"legal_name": "Leche Entera UHT de vaca"}}
            if mode == "absent":
                body = {"id": "123"}
            if mode == "wrong_id":
                body["id"] = "999"
            return httpx.Response(200, json=body, headers={"x-customer-pc": "08001"} if mode == "wrong_zone" else {})
        p = product("Leche entera Hacendado")
        p["id"] = "123"
        return httpx.Response(200, json={"products": [p] if "/72/" in request.url.path else []})
    result = MercadonaProvider(transport=httpx.MockTransport(handler)).collect(ShoppingProfile())
    assert len(requests) == 9
    assert result.offers[0].product_name == "Leche entera Hacendado"
    assert result.offers[0].comparison_group == expected
    assert result.coverage[0]["enrichment_gaps"] == gaps
    assert result.coverage[0]["completed_categories"] == 7


def test_enrichment_cap_three_and_non_digit_id_is_never_requested():
    ids_requested = []
    def handler(request):
        if request.method == "PUT":
            return httpx.Response(200, json={}, headers={"x-customer-pc": "08038", "x-customer-wh": "bcn1"})
        if "/products/" in request.url.path:
            product_id = request.url.path.strip("/").split("/")[-1]
            ids_requested.append(product_id)
            return httpx.Response(200, json={"id": product_id, "details": {"legal_name": "Leche Entera UHT de vaca"}})
        products = []
        if "/72/" in request.url.path:
            for product_id in ["unsafe/123", "101", "102", "103", "104", "105", "106"]:
                p = product("Leche entera Hacendado")
                p["id"] = product_id
                products.append(p)
        return httpx.Response(200, json={"products": products})
    result = MercadonaProvider(transport=httpx.MockTransport(handler)).collect(ShoppingProfile())
    assert ids_requested == ["101", "102", "103"]
    assert sum(offer.comparison_group == "milk_whole_uht" for offer in result.offers) == 3
    assert result.coverage[0]["enrichment_attempts"] == 3
    assert result.coverage[0]["enrichment_gaps"] == 4


def test_environment_proxy_is_explicit_opt_in():
    seen = []
    def factory(**kwargs):
        seen.append(kwargs["trust_env"])
        kwargs["trust_env"] = False  # Synthetic test never uses ambient egress.
        return httpx.Client(**kwargs)
    transport = httpx.MockTransport(lambda _: httpx.Response(503))
    MercadonaProvider(transport=transport, client_factory=factory).collect(ShoppingProfile())
    MercadonaProvider(transport=transport, client_factory=factory, use_env_proxy=True).collect(ShoppingProfile())
    assert seen == [False, True]
