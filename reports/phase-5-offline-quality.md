# Phase 5 offline quality report

This report was generated using explicitly synthetic fixtures and a separate, pre-existing local metadata record. No websites or external APIs were accessed.

## Synthetic fixture run

- Total: 7
- Accepted candidates: 1
- Rejected: 5
- Manual review: 1

Rejection reasons:
- `non_signal_content_type`: 3
- `empty_content`: 1
- `duplicate`: 1

Synthetic accepted candidate (not a validated pain point):

```json
{
  "record_id": "request",
  "synthetic": true,
  "source": "parscoders-synthetic",
  "source_url": "https://fixture.example/project/synthetic-1",
  "content_type": "ProjectDescription",
  "text": "Synthetic request: build a scheduling tool for a small workshop; budget 100 units."
}
```

## Existing local metadata check

- Total: 1; accepted: 0; rejected: 1; manual review: 0.
- The existing homepage-heading record was rejected as `non_signal_content_type`. Its text is not reproduced here.

Reviews in this demonstration were explicitly provided in a separate synthetic review file. No actual records were approved. Outputs retain their original input record, including any sensitive data already present; safeguard access and do not publish them without review.

## Reproduction and validation

The current pipeline was also run with provenance enabled into `data/processed/market-signal-runs/synthetic-phase5-v2` and `data/processed/market-signal-runs/existing-metadata-phase5-v2`; results match the counts above. Full offline suite: Python 3.11.9, `python -m pytest -q`, 105 passed, 0 failed. The input fixture and existing data file were read only; tests verify the fixture bytes remain unchanged. The record outputs include the complete original input and provenance and should not be treated as anonymized.
