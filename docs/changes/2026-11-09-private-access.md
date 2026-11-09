# Private access recovery 0.4.1

Owner cannot enter through the general URL and requests a working private link.
Introduce an operator-provisioned, high-entropy invitation exchange. The server
receives only a configured SHA-256 digest, expiry and existing family ID; the
link fragment contains the secret and is removed before requests. Exchange
uses POST JSON, no-store, constant-time comparison, process-local failure
throttling and eight-hour JWTs using the existing signing secret. No client
family selector, public registration, database writes, key rotation or demo import.
Expiry limits the invitation exchange window. JWT expiry is separate.
This is pilot access recovery, not account/password login or single-use links.
Secrets and family IDs stay outside Git. Existing JWT invitations keep working.

Configuration: FAMILY_INVITE_SHA256 (64 lowercase hex), FAMILY_INVITE_EXPIRES_AT (finite Unix timestamp) and FAMILY_BOOTSTRAP_ID (existing provisioned non-quarantine family). The URL uses #invite= and the browser POSTs the code once, before private API requests. A shared per-process sliding window rejects after 20 failed exchanges/minute; it is not a distributed anti-abuse guarantee. Rotating the invitation hash revokes that link, not already issued JWT sessions.
