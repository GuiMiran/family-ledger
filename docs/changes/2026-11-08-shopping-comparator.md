# Comparator and shopping agent · contract before implementation

Objective: FAMILY LEDGER helps each household compare equivalent offers using
its own explicitly configured location, stores and basket. New households start
empty; no owner case or demo profile is applied automatically. The later
[privacy contract](2026-11-09-private-profiles.md) governs onboarding and public
examples. Quantities are editable comparison references, not inferred consumption
or purchase orders. Public documentation contains no initial household basket.

## Invariants

1. Compare gross payable euros per kg/litre/item, accounting for packs and minimum
   purchase quantities. Net Makro prices require explicit source VAT metadata;
   unknown tax is not silently guessed. Cashback is separate from checkout cost.
2. Match a declared comparison group and optional brand/EAN; different milk,
   meat cuts, egg sizes and fresh/frozen formats must not be silently mixed.
   A special branded formulation never competes against an ordinary group. Unknown equivalence is a gap.
3. Return up to three eligible offers per store/group and three across stores;
   never invent missing candidates. Include full pack outlay, normalized unit
   price, source URL, source timestamp, zone/store and promotion conditions.
4. A price for another postcode or a generic public catalogue cannot be called
   verified for the requested household location. Old, future-dated, expired, conditional-ineligible or
   unavailable offers are excluded from the eligible ranking with explicit reason.
   Generic catalogue references can be shown separately, clearly unlocalized.
5. Profiles, personalized offers and advisor audit records are family-scoped.
   Sources are configured by the operator, not arbitrary URLs supplied by a user.
   Source outages or missing configuration return coverage gaps, not fake prices.
6. An operator-configured HTTP price-feed adapter may refresh observations using
   a documented contract. It is not an official supermarket API or a guarantee
   that six chains are connected. No credentials or source agreement exist by
   implication. Existing public JSON endpoints must not be called official APIs.
7. Shopping agent is bounded and read-only with respect to purchasing: loads
   household profile, obtains observations, validates, compares, explains and
   records a plan. It cannot buy, pay, change membership, invent stock or turn
   potential savings into achieved annual savings. It reports whether a language
   model was actually used; the initial policy advisor is deterministic.
8. Report potential basket savings only against equivalent source-backed options
   for the same requested quantities; show minimum outlay/overbuy separately.
   Full delivery/travel cost and waste prediction remain unknown without inputs.

## Delivery boundary

Implement editable profile, comparison and bounded advisor APIs, persisted
observations, a source/coverage contract and a responsive comparator screen.
The screen distinguishes verified-local options, unlocalized references and
coverage gaps. No retailer is represented as connected until an actual adapter
and source context are configured and verified. No deployment or actual purchase.

Acceptance: unit/pack/VAT arithmetic; same-group checks; freshness, postcode and
promotion gates; per-store/global top-three without padding; profile isolation;
provider outage/unconfigured behavior; server-computed advisor explanations;
mobile build; receipt/auth regression with wholly synthetic fixtures. Evidence is recorded against
the resulting revision; mocked feed tests qualify adapter behavior, not live prices.
