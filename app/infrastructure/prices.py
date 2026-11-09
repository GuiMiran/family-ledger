"""Bounded adapter for an operator-approved price feed, never a retailer scraper."""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import os
import socket
import time
from typing import Callable
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from app.domain.shopping import PriceOffer, ShoppingProfile


STORE_CATALOGUES = {
    "mercadona": "https://www.mercadona.es/",
    "makro": "https://www.makro.es/",
    "lidl": "https://www.lidl.es/",
    "dia": "https://www.dia.es/",
    "carrefour": "https://www.carrefour.es/",
    "condis": "https://www.condis.es/",
}
DEFAULT_STORES = tuple(STORE_CATALOGUES)
MAX_RESPONSE_BYTES = 2_000_000
MAX_OFFERS = 1000
SOURCE_NAME = "operator_price_feed"


@dataclass
class CollectionResult:
    offers: list[PriceOffer]
    coverage: list[dict]
    source_name: str = SOURCE_NAME


def _resolve(host: str) -> list[str]:
    return list({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})


def _public_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        return ip.is_global and not (isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped and not ip.ipv4_mapped.is_global)
    except ValueError:
        return False


class PriceFeedProvider:
    """Only operator configuration selects the source. Errors contain no source secrets.

    An injected MockTransport is an explicit synthetic adapter and bypasses DNS;
    literal-address restrictions still apply. Production DNS is checked before each
    call; network egress policy remains required to prevent DNS rebinding.
    """

    def __init__(self, url: str | None = None, token: str | None = None, *,
                 transport: httpx.BaseTransport | None = None,
                 resolver: Callable[[str], list[str]] = _resolve):
        self.url = os.environ.get("SHOPPING_PRICE_FEED_URL", "") if url is None else url
        self._token = os.environ.get("SHOPPING_PRICE_FEED_TOKEN", "") if token is None else token
        self._transport = transport
        self._resolver = resolver

    def _safe_endpoint(self) -> bool:
        try:
            parsed = urlsplit(self.url)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
                    or parsed.password is not None or parsed.query or parsed.fragment
                    or parsed.port not in (None, 443)):
                return False
            host = parsed.hostname
            if host.lower() == "localhost" or host.lower().endswith(".localhost"):
                return False
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                if isinstance(self._transport, httpx.MockTransport):
                    return True
                addresses = self._resolver(host)
                return bool(addresses) and all(_public_address(address) for address in addresses)
            return _public_address(str(address))
        except (ValueError, OSError, UnicodeError):
            return False

    def collect(self, profile: ShoppingProfile) -> CollectionResult:
        stores = [store.value for store in dict.fromkeys(profile.preferred_stores)]

        def result(status: str) -> CollectionResult:
            return CollectionResult([], [{"store": store, "status": status,
                "catalogue_url": STORE_CATALOGUES.get(store)} for store in stores])

        if not self.url:
            return result("source_not_configured")
        if not self._safe_endpoint():
            return result("source_configuration_invalid")
        headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        payload = {"postal_code": profile.postal_code, "stores": stores,
                   "basket": [item.model_dump(mode="json") for item in profile.basket]}
        started = time.monotonic()
        try:
            with httpx.Client(transport=self._transport, follow_redirects=False,
                              timeout=httpx.Timeout(8.0, connect=3.0), trust_env=False) as client:
                with client.stream("POST", self.url, json=payload, headers=headers) as response:
                    if 300 <= response.status_code < 400:
                        return result("source_redirect_rejected")
                    if response.status_code != 200:
                        return result("source_unavailable")
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        return result("invalid_data")
                    if "application/json" not in response.headers.get("content-type", "").lower():
                        return result("invalid_data")
                    body = bytearray()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        if time.monotonic() - started > 20:
                            return result("source_unavailable")
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            return result("response_too_large")
            data = json.loads(body)
        except (httpx.HTTPError, OSError):
            return result("source_unavailable")
        except (ValueError, UnicodeError, RecursionError):
            return result("invalid_data")
        if not isinstance(data, dict) or not isinstance(data.get("offers"), list):
            return result("invalid_data")
        if len(data["offers"]) > MAX_OFFERS:
            return result("offer_limit_exceeded")
        offers: list[PriceOffer] = []
        invalid = False
        for row in data["offers"]:
            try:
                offer = PriceOffer.model_validate(row)
                if offer.store not in stores:
                    invalid = True
                    continue
                offers.append(offer)
            except (ValidationError, TypeError, ValueError):
                invalid = True
        # Coverage is derived from validated observations; upstream assertions cannot
        # manufacture local verification or override missing/invalid observations.
        upstream = {}
        for entry in data.get("coverage", []) if isinstance(data.get("coverage", []), list) else []:
            if (isinstance(entry, dict) and entry.get("store") in stores
                    and entry.get("status") in {"no_offers", "source_unavailable", "source_not_configured", "invalid_data"}):
                upstream[entry["store"]] = entry["status"]
        coverage = []
        for store in stores:
            found = [offer for offer in offers if offer.store == store]
            if found:
                status = ("observations_received" if any(offer.location_verified and offer.postal_code == profile.postal_code for offer in found)
                          else "unlocalized")
            else:
                status = "invalid_data" if invalid else upstream.get(store, "no_offers")
            coverage.append({"store": store, "status": status,
                             "catalogue_url": STORE_CATALOGUES.get(store),
                             "invalid_rows": invalid})
        return CollectionResult(offers, coverage)
