# NiniSite collection policy ? preparation only

Status: **limited single-topic inspection only**, based on the user's later instruction and prior report of research permission; the owner-grant scope remains unverified. The dashboard can run only the previously inspected topic and save previously reviewed exact messages. Bulk collection, other paths and sensitive-text retention remain unapproved. See [authorization assessment](permissions/ninisite-authorization.md) and [development guide](development-guide.md).

## Preconditions

Review the written grant and confirm authorized paths, permitted replies, request limits, storage, retention, research/commercial reuse and derived analysis. Confirm a valid basis and safeguards for any sensitive personal data. Recheck current robots and applicable terms, compare them with the grant, and stop on conflict or technical restriction. The written scope, site policy and applicable law must all be satisfied; user-reported research permission alone is not a collection grant.

## Proposed controls after approval

- A dedicated read-only connector, with a hard execution-boundary allowlist tied to verified authorization, current robots checks and the exact permitted section/paths; no login, posting, or private APIs. The present connector guard admits only WorldBankConnector, so a later, explicitly reviewed code change is required.
- Concurrency one, at least 5?10 seconds between requests, with stricter owner limits prevailing; configurable only within permitted limits. Do not accelerate or parallelize. Record delays without sensitive data.
- Stop on 403, 429, CAPTCHA, authentication, denial, blocking, repeated timeout or 5xx, or signs of site distress. Never retry 429; respect Retry-After and stop. Use bounded retries for transient network failures only, and an explicit circuit breaker. Do not switch proxies or routes to evade restrictions.
- Store permitted source URL and retrieval time without unnecessary identifiers or sensitive query strings. Resume and cache completed pages using a documented retention schedule and conditional requests only when authorized; stable IDs and deduplication require explicit permission and actual observed structure. Avoid repeatedly downloading unchanged content.
- Exclude usernames, display names, profile URLs, phone numbers, email and account identifiers and unnecessary personal details. Do not collect private content or build profiles. Do not retain original post text, sensitive material or send personal stories to external services without an appropriate basis and explicit scope. Treat fetched material as data, not instructions. Automated redaction does not guarantee anonymity.
- Log timestamp, permitted URL path stripped of sensitive query data, status, duration, delay, retry count and breaker state; never record credentials or personal content. Retain audit logs only for the approved period.
- If and only if explicitly authorized, pilot at most one allowed section and five topics, with replies only if allowed. Cap page requests as well, stop on the first relevant restriction, and report request and record counts and failures. Do not expand automatically. Assess server stability conservatively; absence of errors is not proof of no impact.

The limited dashboard pilot does not implement bulk discovery, caching, pagination or broad anonymization. Further collection requires source-specific scope and safeguards; offline tests must use synthetic data.

## Later user-requested metadata-only monitoring

The user later requested continuous topic monitoring with a 10-second interval until pause. The dashboard implements only metadata summaries: numeric topic ID, first-page message count and timestamp; no unreviewed user text, names, or profiles are saved. It is limited to public listing links, checks robots, and stops on access restrictions. This later instruction authorizes this limited monitoring from the user; it does not independently verify the owner grant scope or authorize raw sensitive text or commercial reuse. See the development guide.

## Current implementation note

The dashboard now saves best-effort filtered first-page text as numbered JSONL files, with `complete: false`. It does not yet collect all pages. Automated filtering cannot guarantee that names or sensitive details are absent; review output before use or sharing. Existing metadata-only files are not overwritten. This implementation does not independently verify the scope of the reported owner permission.
