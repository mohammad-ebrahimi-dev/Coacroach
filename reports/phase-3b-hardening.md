# Phase 3B hardening

Date: 2026-11-25. Scope: three Phase 3A findings; no live HTTP requests or real data were used.

## Output consistency

Previously JSON and JSONL were overwritten independently, allowing a failed second write to leave mismatched outputs. The connector now serializes both formats before touching final files; writes and fsyncs same-directory temporary files; stages labeled copies of prior outputs; and replaces the two destinations sequentially. On a replacement failure it restores replaced destinations or removes newly created destinations. Temporary files are removed after successful publication or successful rollback. If rollback itself fails, the connector raises a dedicated error and retains labeled prior-output backups; the CLI explicitly warns that outputs may differ. The backups are `.world-bank-backup-json-*.tmp` and `.world-bank-backup-jsonl-*.tmp` in the processed directory. Review and restore the relevant backups before further writes.

This is not true multi-file atomicity. Concurrent readers can observe an intermediate mixed state, and concurrent writers are unsupported. Process termination, power loss, filesystem or rollback failure can leave mixed files or temporary files; directory metadata is not fsynced and cleanup can fail on filesystem errors. Backups offer manual recovery but cannot guarantee it under disk or hardware failure. No crash-safe automatic recovery or lock is implemented.

## Numeric validation

Previously Pydantic's non-strict float coercion accepted strings and booleans. A pre-validation check now permits only actual finite integers, floats or null. It rejects strings, booleans, arrays, objects, NaN and infinities. Invalid field errors name the zero-based record index and field without echoing the value. Accepted numbers retain the existing float output behavior; null remains null. The actual live response remains unverified.

## Permission boundary

Previously only `run` and the CLI connection path checked approval; direct `retrieve` bypassed the check. Both `run` and `retrieve` now check permission. The guard requires an approved status, the exact built-in World Bank connector type, and its fixed source identifier and endpoint. Missing, unknown and unapproved statuses, changed scope and an unapproved subclass fail closed. Approval is coded, not accepted from configuration or other untrusted runtime input. Python code and objects are not a security boundary against someone able to modify or monkey-patch them; additional connectors require a deliberate code and policy change.

## Verification

Python **3.11.9**: `python -m pytest -q` completed with **51 passed, 0 failed**. The suite uses synthetic fixtures and mocked HTTP. Regression tests cover JSON and JSONL serialization failures, temporary-write failure, first and second replacement failures, rollback with pre-existing files and with no previous files, successful pair publication, rollback failure with retained backups, valid and invalid numeric values, null, status and scope checks, direct retrieval, and normal execution. Existing offline HTTP, proxy, retry and credential-redaction tests also pass. Python 3.12 and real API connectivity were not tested.

## Remaining risks

The Phase 3A findings on HTTP client initialization and diagnostic handling, broad retry categories, incomplete source metadata, and unpinned dependency ranges remain outside this change. The official indicator methodology and live response remain unverified. Confirm the authorized network route and metadata before live collection. Review the source policy before adding any future connector.

## Verbose regression run

The complete offline suite was rerun with `python -m pytest -v` on Python 3.11.9 and pytest 9.2.0: **51 passed, 0 failed**. No live HTTP requests or data collection were performed.
