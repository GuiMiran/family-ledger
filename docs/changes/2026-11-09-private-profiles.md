# Private family profiles and synthetic examples · authorized contract

The owner requires separation between an individual household case and reusable
application code. No personal name, postcode, preferences, shopping transaction,
receipt/customer/invoice identifier or live case observation belongs in public
README/specs/tests/demo seeds. Private case exported separately, never imported
implicitly. Existing public Git history is not silently rewritten by this change.

1. New households have no postcode, basket or selected stores until explicitly
   configured. GET profile loads the authenticated family's persisted profile;
   absent rows return an empty onboarding state, never another family's example.
2. Validate postcode when a family saves it. Refuse source refresh/agent collection
   until postcode, selected stores and basket exist. GET comparison may be empty.
3. Families can edit name, postcode, stores and basket independently. Identity
   comes from JWT; client-supplied IDs never choose another family's profile.
4. Demo is explicit, separate JSON with documented wholly fictional values.
   It is not automatically applied to ordinary users and not a disguised copy of
   the owner's receipt. No production demo mode or hidden real-data seed.
5. UI supports first-use setup, editing family name, adding/removing products,
   types/quantities/store selection. Source/API uses saved profile, no fixed CP.
6. Public legacy prototype becomes an explicit synthetic demo, loading its sample
   data from JSON and containing no real family greeting or transaction.
7. Redact/remove personal case examples in current public docs, evidence and
   fixtures. Redacted historical reports must be marked as such, not re-certified
   as original byte-exact reports. Keep methodological findings and honest limits.
8. Verify empty defaults, two-family isolation/customization, incomplete setup
   blocked before collection, synthetic examples, and complete regression/build.

This is an intentional authorized privacy correction to the prior Spectra
baseline. Existing instructions to retain evidence do not authorize retaining
personal data contrary to this request. Historical Git removal, if required,
needs a separately reviewed history-rewrite operation; do not imply this patch
removes already published old commits or PR descriptions.
