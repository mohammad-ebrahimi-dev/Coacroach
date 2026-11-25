# Source discovery report

Reviewed: 2026-11-25T12:57:33.350356+00:00. This is source research, not a collection run. Sources marked RequiresPermission or Blocked are not cleared for collection. Existing user data and sample files were not moved or deleted.

The earlier `public_homepage_heading` outputs under `data/processed/<source>/` are source metadata, not a market-pain dataset. They are retained unchanged. No automatic ingestion into a primary dataset was created. The offline `market_tool.market_signals` gate rejects non-signal types, blank content, unreviewed evidence and duplicates; a reviewed label is not a substitute for permission or privacy assessment. No automated classifier can reliably prove a request or remove all identifying information.

## Source assessment

| Source | Valuable content | Access | Value | Strategy |
| --- | --- | --- | --- | --- |
| ParsCoders | Project listing, genuine client brief, skills and stated budget | RequiresPermission | Very high | [parscoders](source-strategies/parscoders.md) |
| Ponisha | Public project requests and budgets, if available | RequiresPermission | High | [ponisha](source-strategies/ponisha.md) |
| Karlancer | Potential client projects and service offers | RequiresPermission | High | [karlancer](source-strategies/karlancer.md) |
| Tebyan | Editorial articles for context, not user requests | RequiresPermission | Low | [tebyan](source-strategies/tebyan.md) |
| Goftino | Customer support platform, not public customer messages | Blocked | None | [goftino](source-strategies/goftino.md) |
| AnjamMidam | Offered services and displayed asking prices | RequiresPermission | Medium | [anjammidam](source-strategies/anjammidam.md) |
| TypeIran | Typing and translation service information | RequiresPermission | Low | [typeiran](source-strategies/typeiran.md) |
| Suntype | Published typing, translation and research service offerings | RequiresPermission | Low | [suntype](source-strategies/suntype.md) |
| NiniSite | Public topic questions and replies | RequiresPermission | High | [ninisite](source-strategies/ninisite.md) |
| Reddit | Public posts, questions and comments | Blocked | High | [reddit](source-strategies/reddit.md) |
| World Bank WDI | Aggregate context: Iran female labor participation, not a user request | ApprovedLimited | Context only | [world_bank](source-strategies/world_bank.md) |
| Iran Open Data | Potential aggregate datasets, not individual complaints | RequiresPermission | Context only | [iran_open_data](source-strategies/iran_open_data.md) |
| BMC self-care survey | Published aggregate survey findings | ApprovedManualOnly | Context only | [self_care_survey](source-strategies/self_care_survey.md) |
| Persian Digikala reviews dataset | Product reviews and recurring product-quality complaints | RequiresPermission | High | [digikala_dataset](source-strategies/digikala_dataset.md) |
| Google Play Developer reviews | Reviews of authorized own production apps | RequiresPermission | High | [google_play](source-strategies/google_play.md) |
| Stack Exchange | Developer questions and answers about technical problems | RequiresPermission | Medium | [stack_exchange](source-strategies/stack_exchange.md) |
| Statistical Center of Iran | Official aggregate statistics for context | RequiresPermission | Context only | [iran_statistics](source-strategies/iran_statistics.md) |

## ParsCoders: actual sections

The [public project listing](https://parscoders.com/project) contains visible client request excerpts, stated budgets, skills and some private-project placeholders. One [public project detail](https://parscoders.com/project/623984/%D8%B7%D8%B1%D8%A7%D8%AD%DB%8C-%D9%BE%D9%88%D8%B3%D8%AA%D8%B1-%D8%A7%D8%B3%D8%AA%D8%B1%DB%8C%D9%84-%D8%AF%D8%B3%D8%AA%DA%AF%D8%A7%D9%87-%D9%BE%D8%B2%D8%B4%DA%A9%DB%8C) was observed through navigation; its path illustrates a numeric ID and title but is not a proven universal pattern. Do not retrieve private projects. Active/completed status, pagination, exact reusable fields, usage rights and API access remain unverified. An advertised budget is a stated willingness to pay, not proof of a completed payment.

## Data separation and limitations

Keep original text and analysis separate if and when a source and record are approved. Do not retain personal identifiers, sensitive material or private content. The requested unchanged original text can conflict with minimization; do not store it until an appropriate policy and safeguards are established. Do not treat request frequency as proven recurrence without a validated deduplicated sample. Do not infer pain points, workarounds or opportunities without evidence.

The discovery JSON contains no user records. No new bulk collection, source-specific collection connector, or scheduler was run or enabled. The existing NiniSite collector was not altered; it still needs independent policy review and must remain stopped for this discovery phase.
