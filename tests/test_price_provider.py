"""Synthetic transport checks; no retailer connections or live price evidence."""
import json

import httpx
import pytest

from app.domain.shopping import ShoppingProfile, compare
from app.infrastructure.prices import MAX_OFFERS, MAX_RESPONSE_BYTES, PriceFeedProvider


def observation(**changes):
    return dict(id="synthetic-milk", store="mercadona", product_name="SYNTHETIC milk",
                comparison_group="milk_whole_uht", pack_quantity="1", pack_unit="l",
                price="1.20", source_url="https://www.mercadona.es/",
                source_name="SYNTHETIC ONLY", observed_at="2026-11-08T10:00:00Z", **changes)


def adapter(handler):
    return PriceFeedProvider("https://partner.example/prices", token="secret-bearer",
                             transport=httpx.MockTransport(handler))


def test_unconfigured_is_six_observable_gaps(monkeypatch):
    monkeypatch.delenv("SHOPPING_PRICE_FEED_URL", raising=False)
    result = PriceFeedProvider().collect(ShoppingProfile())
    assert result.offers == []
    assert len(result.coverage) == 6
    assert {row["status"] for row in result.coverage} == {"source_not_configured"}
    assert all(row["catalogue_url"].startswith("https://") for row in result.coverage)


def test_post_contract_and_generic_observation_never_inherits_requested_zone():
    def handler(request):
        assert request.method == "POST"
        assert request.headers["Authorization"] == "Bearer secret-bearer"
        payload = json.loads(request.content)
        assert payload["postal_code"] == "08038"
        assert len(payload["stores"]) == 6
        assert payload["basket"][0]["desired_quantity"] == "1"
        return httpx.Response(200, json={"offers": [observation()], "coverage": [{"store": "mercadona", "status": "verified"}]})
    result = adapter(handler).collect(ShoppingProfile())
    assert result.offers[0].postal_code is None
    assert result.offers[0].location_verified is False
    assert result.coverage[0]["status"] == "unlocalized"


def test_wrong_zone_is_preserved_and_excluded_from_core():
    from datetime import datetime, timezone
    result = adapter(lambda _: httpx.Response(200, json={"offers": [observation(postal_code="08001", location_verified=True)]})).collect(ShoppingProfile())
    assert result.offers[0].postal_code == "08001"
    assert result.coverage[0]["status"] == "unlocalized"
    comparison = compare(ShoppingProfile(), result.offers, now=datetime(2026, 11, 8, 11, tzinfo=timezone.utc))
    assert comparison["coverage"] == 0
    assert "postcode_mismatch" in comparison["items"][0]["excluded"][0]["reasons"]


def test_empty_success_and_upstream_outage_are_distinct():
    result = adapter(lambda _: httpx.Response(200, json={"offers": [], "coverage": [{"store": "lidl", "status": "source_unavailable"}]})).collect(ShoppingProfile())
    assert result.coverage[0]["status"] == "no_offers"
    assert result.coverage[2]["status"] == "source_unavailable"


@pytest.mark.parametrize("status", [401, 429, 503])
def test_http_outage(status):
    result = adapter(lambda _: httpx.Response(status)).collect(ShoppingProfile())
    assert {row["status"] for row in result.coverage} == {"source_unavailable"}


def test_timeout_and_exception_credentials_are_redacted(caplog):
    def fail(request):
        raise httpx.ReadTimeout("secret-bearer sensitive-url", request=request)
    result = adapter(fail).collect(ShoppingProfile())
    assert result.coverage[0]["status"] == "source_unavailable"
    assert "secret-bearer" not in repr(result)
    assert "sensitive-url" not in repr(result)
    assert "secret-bearer" not in caplog.text


def test_redirect_is_never_followed():
    visited = []
    def handler(request):
        visited.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
    result = adapter(handler).collect(ShoppingProfile())
    assert len(visited) == 1
    assert result.coverage[0]["status"] == "source_redirect_rejected"


@pytest.mark.parametrize("url", ["http://partner.example/", "https://user:password@partner.example/", "https://partner.example/?token=secret", "https://partner.example/#secret", "https://127.0.0.1/", "https://[::1]/", "https://169.254.169.254/", "https://10.0.0.1/", "https://localhost/", "https://partner.example:8443/"])
def test_unsafe_operator_urls_never_contact_transport(url):
    def fail(_):
        pytest.fail("unsafe configuration contacted transport")
    result = PriceFeedProvider(url, transport=httpx.MockTransport(fail)).collect(ShoppingProfile())
    assert result.coverage[0]["status"] == "source_configuration_invalid"
    assert "password" not in repr(result)
    assert "token=secret" not in repr(result)


def test_private_dns_is_rejected_before_connection():
    result = PriceFeedProvider("https://partner.example/", resolver=lambda _: ["93.184.216.34", "127.0.0.1"]).collect(ShoppingProfile())
    assert result.coverage[0]["status"] == "source_configuration_invalid"


def test_response_size_and_offer_count_bounds():
    result = adapter(lambda _: httpx.Response(200, headers={"content-type": "application/json"}, content=b" " * (MAX_RESPONSE_BYTES + 1))).collect(ShoppingProfile())
    assert result.coverage[0]["status"] == "response_too_large"
    result = adapter(lambda _: httpx.Response(200, json={"offers": [{}] * (MAX_OFFERS + 1)})).collect(ShoppingProfile())
    assert result.coverage[0]["status"] == "offer_limit_exceeded"


@pytest.mark.parametrize("payload", [{}, {"offers": None}, {"offers": [{"price": "NaN"}]}, {"offers": [observation(postal_code="wrong-zone")]}])
def test_invalid_feed_has_explicit_gap(payload):
    result = adapter(lambda _: httpx.Response(200, json=payload)).collect(ShoppingProfile())
    assert result.offers == []
    assert result.coverage[0]["status"] == "invalid_data"


def test_invalid_row_does_not_discard_valid_observation_or_fake_success_elsewhere():
    result = adapter(lambda _: httpx.Response(200, json={"offers": [observation(), {}]})).collect(ShoppingProfile())
    assert len(result.offers) == 1
    assert result.coverage[0]["status"] == "unlocalized"
    assert result.coverage[1]["status"] == "invalid_data"


def test_unexpected_compressed_response_rejected_before_decompression():
    import gzip
    result = adapter(lambda _: httpx.Response(200, headers={"content-type": "application/json", "content-encoding": "gzip"}, content=gzip.compress(b'{"offers":[]}'))).collect(ShoppingProfile())
    assert result.coverage[0]["status"] == "invalid_data"
