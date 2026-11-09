"""Synthetic prices test arithmetic and eligibility, never live retailer coverage."""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.shopping import BasketItem, PriceOffer, ShoppingProfile, Store, compare

NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)


def profile(**changes):
    data = dict(basket=[BasketItem(key="milk", label="Whole milk", comparison_group="milk_whole_uht",
                                 unit="l", desired_quantity="7")])
    data.update(changes)
    return ShoppingProfile(**data)


def offer(**changes):
    data = dict(id="a", store="mercadona", product_name="Synthetic milk",
                comparison_group="milk_whole_uht", pack_quantity="1", pack_unit="l", price="1.20",
                source_url="https://tienda.mercadona.es/example", source_name="Synthetic test",
                observed_at=NOW, postal_code="08038", location_verified=True)
    data.update(changes)
    return PriceOffer(**data)


def item_result(offers, household=None):
    return compare(household or profile(), offers, NOW)["items"][0]


def test_defaults_are_editable_references_and_preserve_equivalence():
    p = ShoppingProfile()
    assert p.postal_code == "08038" and len(p.basket) == 8 and len(p.preferred_stores) == 6
    groups = {i.comparison_group for i in p.basket}
    assert {"milk_whole_uht", "puleva_max", "beef_sliced", "cheese_fresh", "eggs_size_pending"} <= groups
    assert p.coupons_enabled is False and p.club_memberships == []
    assert p.max_age_hours == 24
    with pytest.raises(ValidationError):
        ShoppingProfile(postal_code="8038")
    with pytest.raises(ValidationError):
        profile(basket=[p.basket[0], p.basket[0]])


def test_bundle_vat_outlay_overbuy_and_cashback_do_not_use_float_or_discount():
    row = item_result([offer(pack_quantity="1000", pack_unit="ml", packs_required=6,
                             price="6", price_includes_vat=False, vat_rate="0.10", cashback="2")])["top_offers"][0]
    assert Decimal(row["unit_price"]) == Decimal("1.10")
    assert Decimal(row["gross_bundle_price"]) == Decimal("6.60")
    assert row["required_bundles"] == 2
    assert Decimal(row["required_outlay"]) == Decimal("13.20")
    assert Decimal(row["overbuy_quantity"]) == 5
    assert row["cashback"] == "2"
    json.dumps(compare(profile(), [offer()], NOW))


def test_gram_conversion_and_unit_count_multipacks():
    p = profile(basket=[BasketItem(key="rice", label="Rice", comparison_group="rice_long",
                                 unit="kg", desired_quantity="1.1")])
    row = item_result([offer(comparison_group="rice_long", pack_quantity="500", pack_unit="g",
                             packs_required=2, price="2.50")], p)["top_offers"][0]
    assert Decimal(row["unit_price"]) == Decimal("2.50")
    assert Decimal(row["required_outlay"]) == 5
    assert Decimal(row["overbuy_quantity"]) == Decimal("0.9")
    p = profile(basket=[BasketItem(key="eggs", label="Eggs L", comparison_group="eggs_L",
                                 unit="unit", desired_quantity="13")])
    row = item_result([offer(comparison_group="eggs_L", pack_quantity="6", pack_unit="unit",
                             packs_required=2, price="3")], p)["top_offers"][0]
    assert Decimal(row["unit_price"]) == Decimal("0.25")
    assert Decimal(row["required_outlay"]) == 6
    assert Decimal(row["overbuy_quantity"]) == 11


@pytest.mark.parametrize("changes,reason", [
    ({"comparison_group": "milk_semi"}, "comparison_group_mismatch"),
    ({"comparison_group": "puleva_max"}, "comparison_group_mismatch"),
    ({"pack_unit": "kg"}, "incompatible_unit"),
    ({"price_includes_vat": False}, "vat_unknown"),
    ({"observed_at": NOW + timedelta(seconds=1)}, "future_observation"),
    ({"observed_at": NOW - timedelta(hours=24, seconds=1)}, "stale_observation"),
    ({"valid_from": NOW + timedelta(seconds=1)}, "promotion_not_started"),
    ({"valid_until": NOW - timedelta(seconds=1)}, "promotion_expired"),
    ({"club_required": True}, "club_required"),
    ({"coupon_required": True}, "coupon_required"),
    ({"available": False}, "unavailable"),
    ({"postal_code": "08039"}, "postcode_mismatch"),
])
def test_exclusion_gates(changes, reason):
    result = item_result([offer(**changes)])
    assert result["top_offers"] == result["eligible_offers"] == []
    assert reason in result["excluded"][0]["reasons"]


def test_store_brand_ean_and_specific_cut_are_not_silently_equivalent():
    assert "store_not_selected" in item_result([offer()], profile(preferred_stores=[Store.lidl]))["excluded"][0]["reasons"]
    restricted = profile(basket=[BasketItem(key="milk", label="Milk", comparison_group="milk_whole_uht",
                                          unit="l", desired_quantity="1", brand="A", ean="123")])
    assert set(item_result([offer(brand="B", ean="124")], restricted)["excluded"][0]["reasons"]) == {"brand_mismatch", "ean_mismatch"}
    assert len(item_result([offer(brand="a", ean="123")], restricted)["top_offers"]) == 1
    beef = profile(basket=[BasketItem(key="beef", label="Babilla", comparison_group="beef_babilla_sliced",
                                    unit="kg", desired_quantity="1")])
    assert not item_result([offer(comparison_group="beef_sliced", pack_unit="kg")], beef)["top_offers"]


def test_pending_egg_size_never_gets_eligible_ranking():
    p = ShoppingProfile()
    pending = next(i for i in compare(p, [offer(comparison_group="eggs_size_pending", pack_unit="unit")], NOW)["items"] if i["key"] == "eggs")
    assert not pending["top_offers"]
    assert "egg_size_pending" in pending["excluded"][0]["reasons"]


def test_unlocalized_references_are_not_coverage_or_local_ranks():
    offers = [offer(id="no-zone", postal_code=None), offer(id="unverified", location_verified=False),
              offer(id="wrong", postal_code="08039")]
    result = compare(profile(), offers, NOW)
    assert result["coverage"] == 0
    item = result["items"][0]
    assert {o["id"] for o in item["references"]} == {"no-zone", "unverified"}
    assert not item["top_offers"]
    assert item["excluded"][0]["id"] == "wrong"


def test_eligibility_boundaries_and_membership():
    result = item_result([offer(club_required=True, coupon_required=True,
                               observed_at=NOW-timedelta(hours=24), valid_from=NOW, valid_until=NOW)],
                         profile(club_memberships=[Store.mercadona], coupons_enabled=True))
    assert len(result["top_offers"]) == 1


def test_dedup_latest_before_rank_and_top_three_without_padding():
    offers = [offer(id="same", price="0.01", observed_at=NOW-timedelta(hours=1)),
              offer(id="same", price="8"),
              *[offer(id=str(i), price=str(i)) for i in range(1, 6)],
              offer(id="same", store="lidl", source_url="https://www.lidl.es/example", price="0.50")]
    result = compare(profile(), offers, NOW)
    item = result["items"][0]
    assert result["coverage"] == 1
    assert [x["store"] for x in item["top_offers"]] == ["lidl", "mercadona", "mercadona"]
    assert len(item["eligible_offers"]) == 7
    assert [len(s["offers"]) for s in item["per_store"]] == [3, 0, 1, 0, 0, 0]
    assert next(o for o in item["eligible_offers"] if o["id"] == "same" and o["store"] == "mercadona")["price"] == "8"
    assert len(item_result([offer()])["top_offers"]) == 1
    assert item_result([])["top_offers"] == []
    # Latest invalid observation cannot fall back to the older cheap observation.
    assert not item_result([offer(observed_at=NOW-timedelta(hours=1)), offer(available=False)])["top_offers"]


@pytest.mark.parametrize("changes", [
    {"price": "NaN"}, {"pack_quantity": "0"}, {"packs_required": 0}, {"price": "-1"},
    {"vat_rate": "10"}, {"pack_unit": "oz"}, {"observed_at": NOW.replace(tzinfo=None)},
    {"source_url": "http://www.mercadona.es/x"},
    {"source_url": "https://mercadona.es.evil.example/x"},
    {"source_url": "https://user:password@mercadona.es/x"},
    {"source_url": "https://127.0.0.1/x"},
    {"source_url": "https://www.lidl.es/x"},
    {"source_url": "https://mercadona.es:8443/x"},
    {"valid_from": NOW, "valid_until": NOW-timedelta(seconds=1)},
])
def test_malformed_or_unsafe_offers_rejected(changes):
    with pytest.raises(ValidationError):
        offer(**changes)


def test_variable_weight_uses_authoritative_gross_unit_price_and_estimates_outlay():
    p = profile(basket=[BasketItem(key="meat", label="Fresh breast", comparison_group="chicken_breast_fresh_boneless",
                                 unit="kg", desired_quantity="1")])
    variable = offer(comparison_group="chicken_breast_fresh_boneless", pack_quantity="0.53", pack_unit="kg",
                     price="4.08", variable_weight=True, reference_unit_price_gross="7.70", reference_unit="kg",
                     conditions=["Approximate tray weight; final checkout amount may vary"])
    row = item_result([variable], p)["top_offers"][0]
    assert row["unit_price"] == "7.70"
    assert Decimal(row["unit_price"]) != Decimal("4.08") / Decimal("0.53")
    assert row["outlay_estimated"] is True
    assert Decimal(row["required_outlay"]) == Decimal("8.16")
    assert Decimal(row["overbuy_quantity"]) == Decimal("0.06")
    assert row["conditions"] == variable.conditions
    fixed = item_result([offer()])["top_offers"][0]
    assert fixed["outlay_estimated"] is False


@pytest.mark.parametrize("changes,reason", [
    ({}, "variable_weight_reference_missing_or_invalid"),
    ({"reference_unit_price_gross": "0"}, "variable_weight_reference_missing_or_invalid"),
    ({"reference_unit_price_gross": "-1"}, "variable_weight_reference_missing_or_invalid"),
    ({"reference_unit_price_gross": "7.70", "reference_unit": "kg"}, "variable_weight_reference_unit_mismatch"),
])
def test_variable_weight_requires_compatible_positive_source_reference(changes, reason):
    result = item_result([offer(variable_weight=True, **changes)])
    assert not result["eligible_offers"]
    assert reason in result["excluded"][0]["reasons"]


def test_conflicting_equal_timestamp_quotes_are_excluded_in_both_orders():
    cheap = offer(price="1")
    costly = offer(price="2")
    for candidates in ([cheap, costly], [costly, cheap]):
        result = item_result(candidates)
        assert not result["top_offers"]
        assert "ambiguous_duplicate" in result["excluded"][0]["reasons"]
    assert len(item_result([cheap, cheap])["top_offers"]) == 1
    newer = offer(price="3", observed_at=NOW+timedelta(seconds=1))
    result = compare(profile(), [cheap, costly, newer], NOW+timedelta(seconds=1))["items"][0]
    assert result["top_offers"][0]["price"] == "3"
    assert not result["excluded"]


def test_profile_deduplicates_stores_and_bounds_user_inputs():
    p = profile(preferred_stores=["mercadona", "mercadona", "lidl"])
    assert p.preferred_stores == [Store.mercadona, Store.lidl]
    with pytest.raises(ValidationError):
        profile(preferred_stores=[{}])
    with pytest.raises(ValidationError):
        profile(max_age_hours=169)
    with pytest.raises(ValidationError):
        profile(basket=[BasketItem(key=str(i), label="Test", comparison_group="test", unit="kg", desired_quantity=1)
                        for i in range(31)])
    with pytest.raises(ValidationError):
        offer(product_name="x"*501)
    with pytest.raises(ValidationError):
        offer(price="1000001")
    with pytest.raises(ValidationError):
        offer(pack_quantity="Infinity")
    with pytest.raises(ValidationError):
        offer(pack_quantity="1e-100000")
    with pytest.raises(ValidationError):
        offer(conditions=["x"*501])
    with pytest.raises(ValidationError):
        offer(conditions=["x"]*21)
