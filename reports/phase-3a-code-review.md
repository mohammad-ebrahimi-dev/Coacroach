# Phase 3A MVP code review

Reviewed 2026-11-25. Scope: the requested code, tests, documentation, dependency constraints and existing research records. No live network requests or real data collection were made. Findings are review observations, not a claim that a vulnerability has been exploited.

## Findings

1. **Medium ? output pair can become inconsistent or lose a previous file.** `WorldBankConnector.save` overwrites the JSON file and then JSONL with direct `write_text` calls. A crash, disk-full condition or write failure can leave a truncated file or JSON and JSONL from different runs. Suggested smallest fix: serialize both fully first, write each to a temporary file in the destination directory, and publish using a documented generation/manifest strategy or a single authoritative format. Two independent replacements alone are not an atomic pair.
2. **Medium ? malformed numeric input can be silently coerced.** Pydantic's default non-strict `float | None` accepts values such as a JSON boolean and numeric strings as numbers. This can create false observations from an invalid source response. Suggested fix: explicitly accept finite JSON numbers excluding booleans, or null; test booleans and strings. The live payload format has not been observed, so verify intended numeric types against the official API before changing validation.
3. **Medium ? unapproved connectors can be called outside the guarded entry point.** `Connector.run` and the CLI connection command check permission, but `WorldBankConnector.retrieve` is public and does not. A caller can invoke `retrieve` directly on a connector marked unapproved. The current CLI does not expose that route. Suggested fix: enforce the check within the retrieval boundary as well, or make a single guarded entry point the only public API. This is an application guard, not a security boundary against someone editing code.
4. **Low ? proxy and client initialization errors can escape safe error handling.** `httpx.Client(...)` is created outside the inner transport exception handler. Invalid or unsupported system proxy configuration can raise an exception before request diagnostics. CLI catches `ValueError` but not every potential configuration or HTTPX exception, so a traceback could include configuration details. Output-directory creation and log initialization also occur outside the CLI try block and may produce a traceback. Suggested fix: catch expected setup exceptions without rendering their contents and emit a safe category.
5. **Low ? retries are broader than transient HTTP failures.** The client retries every 5xx, including statuses such as 501 or 505, and retries transport errors other than an SSL exception found through chained causes. Some failures are persistent. Retries are bounded, and 403 and 429 stop immediately. Suggested fix: restrict retryable statuses and transport categories to an explicitly reviewed transient set and test them. The 429 policy intentionally stops rather than waiting and retrying; this respects the existing source policy.
6. **Low ? source metadata is incomplete in persisted observations.** Only a static attribution and the API indicator label are stored; API-provided source/note/observation metadata is discarded. The indicator label is optional, and no unit or population definition is stored. The scope ID is checked but a live response has not been inspected. Suggested fix: after official metadata is verified, preserve appropriate provider, source, definition and observation metadata without inventing them.
7. **Low ? dependency ranges are unpinned and runtime support is not declared by project metadata.** `requirements.txt` allows future versions and transitive dependency changes, and no `pyproject.toml` or equivalent declares a Python minimum. Repeatable installation and compatibility across all allowed versions are not demonstrated. Suggested fix: declare the intended Python version and use a tested lock/constraints file if reproducibility is required.

## Controls reviewed

- CLI suppresses HTTPX and httpcore logging and avoids printing proxy values in its own configuration errors; proxy fields are excluded from Pydantic representation. The added synthetic proxy-error test verifies its exception text is absent from captured output. This does not prove every third-party logging or malformed dotenv path is safe. Local `.env` is ignored by Git.
- Four timeouts are positive and bounded; `verify=True` is passed, redirects are disabled, and a missing configured scheme-specific proxy fails rather than explicitly falling back. Actual OS proxy behavior was not network-tested. The client retries GET only, uses bounded delays, stops on 429, and does not use the Retry-After value to schedule a later request.
- The connector checks row count, page count, country, indicator, year shape and uniqueness; nulls survive JSON and JSONL in offline tests. The review findings above limit the integrity guarantee.

## Indicator metadata

The previously consulted [official World Bank indicator page](https://data.worldbank.org/indicator/SL.TLF.ACTI.FE.ZS?locations=IR) was recorded in the Phase 1 research as **?Labor force participation rate, female (% of female population ages 15?64) (modeled ILO estimate)?**. On that earlier evidence, the population is female ages 15?64 and the displayed unit is percent of the corresponding female population. The Phase 3 brief's 15+ label conflicts with that recorded indicator name. The connector uses the approved ID and stores the returned API label rather than hardcoding 15+; the README notes the mismatch. The registry points to the correct ID but does not explicitly state the age range.

The precise World Bank/ILO measurement methodology and the official mapping of `IRN` to Iran were not independently verified in this offline review; the country code comes from the existing project specification and connector, not a newly checked World Bank metadata response. The page text or its official metadata response was not stored in the project and no live request was allowed. The recorded name is prior research evidence, not a fresh verification. Smallest documentation improvement after an authorized official metadata check: add the exact definition, unit and age range, with a dated source, to the registry; retain the existing indicator ID unless the project explicitly changes scope. Do not substitute a 15+ series without a separate permission decision.

## Python and dependencies

- Offline test interpreter: Python **3.11.9**. `python -m pytest -q`: **17 passed**. All network behavior in the tests uses mocks or is rejected before requests.
- Installed package metadata: HTTPX 0.28.1 requires Python >=3.8; Pydantic 2.14.4 >=3.10; python-dotenv 1.2.4 >=3.10; pytest 9.2.0 >=3.10. These installed versions declare compatibility with Python 3.11 and 3.12, but that alone does not prove all allowed dependency versions or the application work on 3.12.
- Python 3.12 was not found in the checked executable paths and standard installation directories; it was **not runtime-tested**. Re-run the full suite in a Python 3.12 environment before claiming compatibility.

## Tests and limitations

Added offline tests for exhausted 503 retries, no retry on 403, synthetic proxy-error log redaction, invalid JSON without output, and wrong indicator, duplicate year, incomplete total and invalid numeric values. Existing tests cover proxy routing configuration, timeout retry exhaustion, 429, null preservation, output equivalence and permission checking through `run`. Tests use invented fixtures only and do not establish real API availability or behavior.

## Recommended next steps

Prioritize output integrity, strict value validation and permission enforcement at the retrieval boundary; add focused regression tests for each before making changes. Obtain official indicator methodology and country metadata through an authorized read-only route, then run tests under Python 3.12. No additional source should be enabled based on this review.

## Phase 3B follow-up

The first three findings were addressed with staged serialization and rollback, strict finite-number validation, and permission checks at both execution and retrieval entry points. See [Phase 3B hardening](phase-3b-hardening.md) for tests, recovery limitations and remaining findings. The original review text above records the state at review time.
