# Price sources and coverage

`app.infrastructure.prices.PriceFeedProvider.collect(ShoppingProfile)` returns
`CollectionResult(offers: list[PriceOffer], coverage: list[dict], source_name: str)`.
The default profile selects Mercadona, Makro, Lidl, DIA, Carrefour and Condis.
The registry's official public website URLs are navigation references, **not API
endpoints**, data permissions, connected providers or proof of local prices.

An operator must supply an approved licensed/partner source and independently
verify its rights, product equivalence, tax metadata, observation timestamps and
location claims. No retailer credentials, source agreement or official six-chain
API is assumed. Without configuration all selected stores explicitly report
`source_not_configured`; the adapter makes no network requests.

Configure server environment `SHOPPING_PRICE_FEED_URL` to an HTTPS endpoint on
port 443 and optionally `SHOPPING_PRICE_FEED_TOKEN` for its Bearer credential.
Neither is accepted from household request input. Do not put credentials in the
URL: user information, query strings and fragments are rejected. The endpoint
path must also contain no secret. Keep operator secrets outside the repository.
Authorization values and exception strings are never returned in coverage.

The adapter sends a JSON POST with `postal_code`, selected `stores` and `basket`
containing the profile's basket models encoded as JSON. It requests JSON with
identity encoding. The response contract is an object with `offers` (required
array of `PriceOffer` fields) and optionally `coverage` (array of store/status
objects). Every offer is validated against the domain model, including HTTPS
chain provenance links, finite nonnegative amounts and timezone-aware timestamps.
A malformed row is discarded; valid rows remain observations and expose
`invalid_rows: true` alongside coverage. Offers for unrequested stores are invalid.

Optional upstream coverage can report `no_offers`, `source_unavailable`,
`source_not_configured` or `invalid_data` for a store without observations. It
cannot manufacture local verification or override validated observations. Empty
successful feeds report `no_offers`. Unknown upstream statuses are ignored.

Coverage errors distinguish `source_configuration_invalid`, `source_unavailable`,
`source_redirect_rejected`, `response_too_large`, `offer_limit_exceeded` and
`invalid_data`. `unlocalized` means observations do not assert the requested
postcode with `location_verified=true`. `observations_received` only means at
least one observation asserts that context; it does **not** prove freshness,
availability, tax completeness or eligibility. The comparison domain applies
those gates separately. Contacting a source never changes an offer's postal code,
verification flag, source timestamp or availability. A generic public catalogue
remains an unlocalized reference; another postcode never becomes verified 08038.

## Bounds and operational limits

There are at most 1,000 offers and 2,000,000 response bytes per collection.
Redirects and compressed responses are rejected. HTTP connect timeout is three
seconds, other HTTP operations eight seconds, and streaming checks a twenty-second
elapsed budget between bounded 64 KiB chunks. These are synchronous transport
bounds, not a hard wall-clock deadline for OS DNS. The adapter disables environment
proxies. Literal nonpublic addresses, localhost and DNS results containing any
nonpublic address are rejected before connecting. Operator-controlled DNS can
change between validation and connection: deploy network egress restrictions to
prevent DNS rebinding; DNS checks alone are not an egress firewall.

Only the test adapter's explicit `httpx.MockTransport` injection bypasses hostname
DNS resolution. It still rejects unsafe literal URLs. Tests exercise outages,
redirection, size limits, credential redaction and preservation of wrong/unknown
zones; they do not establish live prices or retailer access. No actual provider
is connected by this implementation.

## SYNTHETIC ONLY contract example

This is a fabricated response to explain the schema. It is not a current price,
retailer quotation or evidence that a product is sold in 08038. In particular,
absence of location fields deliberately leaves it unlocalized.

```json
{
  "offers": [{
    "id": "synthetic-example",
    "store": "mercadona",
    "product_name": "SYNTHETIC ONLY whole milk",
    "comparison_group": "milk_whole_uht",
    "pack_quantity": "1",
    "pack_unit": "l",
    "packs_required": 1,
    "price": "1.20",
    "price_includes_vat": true,
    "source_name": "SYNTHETIC ONLY",
    "source_url": "https://www.mercadona.es/",
    "observed_at": "2026-11-08T10:00:00Z"
  }],
  "coverage": [{"store": "lidl", "status": "source_not_configured"}]
}
```

`price` is the gross cost of the entire minimum bundle when
`price_includes_vat=true`; for an explicitly net price the feed must supply
`vat_rate` as a fraction (e.g. `0.10`). `packs_required` counts packs in that bundle;
`pack_quantity` describes one pack. Promotion dates, club/coupon conditions and
cashback use the domain fields. Cashback is separate from checkout payment.
