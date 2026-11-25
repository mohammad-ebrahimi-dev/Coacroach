# MVP aggregate observation schema

Each JSON array entry and JSONL line contains `source`, `source_url`, `indicator_id`, `indicator_label`, `country_code`, `year`, `value`, `retrieved_at`, `attribution`, `license_reference`, and `license_terms`. The value is numeric or null; year is numeric; retrieval time is UTC ISO 8601. The source label is taken from the API. Country and indicator are checked against the approved source scope, and incomplete or multipage responses are rejected.

This schema represents aggregate statistics, not user complaints. No identifiers or sensitive personal content are intentionally collected. Future source types need their own reviewed schema and provenance controls.
