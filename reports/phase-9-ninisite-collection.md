# Phase 9 NiniSite collection report

Completed at 2026-11-25T13:29:57.295374+00:00. The user previously reported owner permission for website research and requested this bounded inspection. Requests used the configured route, TLS verification and one shared safety monitor with a minimum 10-second interval. robots.txt returned 200 and allowed the candidate paths. No 403, CAPTCHA, 429, timeout or 5xx was observed during this run.

## Outcome

- Candidate URLs: 20, each checked once after robots.
- HTTP 200: 10; HTTP 301: 10. Redirect destinations were not followed or verified.
- New verified topics saved: 0; duplicates confirmed: 0; extraction failures: 0; inaccessible: 0; requires manual review: 20 (10 privacy reviews and 10 redirects). A 301 is not treated as a failed or unavailable site.
- First-page replies observed on HTTP 200 pages: 74 in total; replies saved: 0. No pagination was performed and no claim of complete discussions is made.
- The 10 HTTP 200 pages had title and first-page post compared against local topic IDs, source URL hashes, normalized title hashes and old text hashes. No exact match was found by this method. Older records lack complete provenance and can include redactions, so apparent uniqueness remains provisional.
- The existing regex cleaner cannot reliably remove all personal names or sensitive disclosures. The user required personal identifiers be excluded. Consequently the 10 provisional topics were not saved as analysis-ready records before individual privacy review. Fetched text was held only in memory and discarded; a future review would require an authorized new retrieval.
- No new JSONL file was written to P1. Existing data were not overwritten. The requested content collection and save outcome is incomplete.

## Per-URL status

The complete URL mapping and per-URL statuses are stored locally in `data/processed/phase-9/ninisite-statuses-v2.json`; topic ID identifies each URL below. HTTP status alone is not authorization for reuse.

| Topic ID | HTTP | First-page replies observed | Outcome |
| --- | ---: | ---: | --- |
| 19140745 | 200 | 4 | Privacy review required; content not retained |
| 19140743 | 200 | 9 | Privacy review required; content not retained |
| 19140742 | 200 | 5 | Privacy review required; content not retained |
| 19140654 | 200 | 15 | Privacy review required; content not retained |
| 19140725 | 200 | 15 | Privacy review required; content not retained |
| 19140674 | 301 | ? | Redirect; target not followed |
| 4418940 | 301 | ? | Redirect; target not followed |
| 19120116 | 301 | ? | Redirect; target not followed |
| 19139452 | 301 | ? | Redirect; target not followed |
| 19137387 | 301 | ? | Redirect; target not followed |
| 19137391 | 301 | ? | Redirect; target not followed |
| 19138195 | 301 | ? | Redirect; target not followed |
| 19140617 | 200 | 6 | Privacy review required; content not retained |
| 19140706 | 200 | 3 | Privacy review required; content not retained |
| 19140600 | 200 | 6 | Privacy review required; content not retained |
| 19139203 | 301 | ? | Redirect; target not followed |
| 19140666 | 200 | 4 | Privacy review required; content not retained |
| 19140713 | 200 | 7 | Privacy review required; content not retained |
| 19140399 | 301 | ? | Redirect; target not followed |
| 19140632 | 301 | ? | Redirect; target not followed |

## Implementation and limits

`market_tool/dedup_index.py` now indexes normalized titles in addition to IDs, URL hashes and content hashes. A title or legacy content match is flagged for manual review rather than automatically declared identical; corrupt or unreadable legacy data prevents a confident new decision. `market_tool/ninisite_phase9.py` performs one-pass inspection and stops on safety restrictions. These components do not store extracted topic text and do not supply a privacy-review interface. Hashes do not provide guaranteed anonymity.

No personally identifying data, source HTML, extracted post text or actual topic URLs are included in this report. The local status file contains source URLs and should be handled accordingly.
