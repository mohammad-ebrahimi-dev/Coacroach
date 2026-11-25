# Source registry

Assessed 25 November 2026 from linked publisher pages. Accessibility means the cited public description was visible during web research, not that an API or download was tested. Automation, commercial use and status apply only to each described scope. **No research datasets or user posts were collected.** Recheck terms and privacy before collection. Domain key: M = motherhood/childcare; H = health/wellness; B = beauty; R = relationships/family; E = women's employment/income; D = daily life/shopping/household services.

## 1. World Bank WDI ? Iran female labor-force participation

- **Source / type / domains:** [Iran indicator SL.TLF.ACTI.FE.ZS](https://data.worldbank.org/indicator/SL.TLF.ACTI.FE.ZS?locations=IR); aggregate modeled statistical series; E. It provides labor-market context, not individual complaints.
- **Access / automation / export:** Indicator page was accessible and provides CSV, XML and Excel downloads. The [Indicators API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures) documents programmatic JSON and download calls. Use the documented API at conservative rates; endpoint was not tested here.
- **Commercial use / evidence:** The indicator page labels this series CC BY 4.0. The [World Bank licensing page](https://datacatalog.worldbank.org/public-licenses?fragment=research) explicitly permits commercial use under that license with attribution and change indication and describes additional terms. Verify current series-level metadata, upstream attribution and terms at retrieval.
- **Personal or sensitive data:** This is an aggregate indicator, not person-level text; small-cell and contextual disclosure concerns must still be checked for any other tables.
- **Limitations:** Modeled, historical, and not a measure of unmet demand or causation; broader datasets and microdata can carry other licenses.
- **Status: Approved** for the specific published Iran aggregate series, via its documented API/download, for attributed commercial research under its listed terms. No other indicator, data source or collection channel is approved by this entry.

## 2. Iran Open Data

- **Source / type / domains:** [Iran Open Data](https://iranopendata.org/en/about/), an independent repository of structured Iran data and reports; potentially M, H, E, D depending on dataset. Exact datasets and domain fit not assessed.
- **Access / automation / export:** [About page](https://iranopendata.org/en/about/) describes free downloads and CSV/API options. [Terms](https://iranopendata.org/en/terms/) prohibit unauthorized automated scraping/bulk extraction and require an express separate written agreement for automated API access.
- **Commercial use / evidence:** The terms permit research, academic or journalistic data use with specified attribution, but applicability to this commercial research project and particular third-party materials is not established. [Copyright](https://iranopendata.org/en/copyright/) requires attribution where use is expressly permitted.
- **Personal or sensitive data:** Varies by dataset; assessment pending. Do not ingest personal or sensitive records without a valid basis and safeguards.
- **Limitations:** Terms distinguish public material from institutional feeds; individual dataset rights, recency and provenance require review. No automated collection without written authorization.
- **Status: Requires Review.** Obtain written commercial-use and access-method confirmation for identified datasets before collection.

## 3. Self-care survey article in Tehran

- **Source / type / domains:** [Simbar et al., BMC Women's Health (2023)](https://link.springer.com/article/10.1186/s12905-023-02763-9), published survey article; H, R. Public full-text page was accessible.
- **Access / automation / export:** Publisher article and PDF are offered for reading. Automated extraction, publisher API and bulk terms were not assessed; no automated collection approved.
- **Commercial use / evidence:** The publisher labels the article [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and identifies exceptions for some third-party material. Article license does not automatically authorize underlying respondent data. Attribution and indication of changes required.
- **Personal or sensitive data:** The subject can be highly sensitive. Scope limited to published non-identifying aggregate findings; exclude participant-level data, direct quotations, and sensitive individual information unless a separate legal basis and safeguards exist.
- **Limitations:** Local survey population, time, sampling and methodology limit generalization; reported results do not establish willingness to pay. No inference of rights to unpublished data.
- **Status: Approved** solely for manual research use of published, non-identifying aggregate findings under the article license and applicable terms; no automated text or respondent-data collection is approved.

## 4. GitHub Persian Digikala reviews dataset

- **Source / type / domains:** [ruhollah82/digikala_dataset](https://github.com/ruhollah82/digikala_dataset), repository describes Persian product-review data, primarily electronics and household appliances; D, possibly other domains if verified. Repository description is publicly accessible; file integrity and current contents were not checked.
- **Access / automation / export:** Repository describes CSV and Parquet files and a collection pipeline; repository download availability does not authorize running the crawler or bulk extracting the original platform.
- **Commercial use / evidence:** Its README states CC BY 4.0 for the dataset and MIT for code but also says the dataset is intended for research and educational use. Its authority to sublicense the original user reviews and the meaning of that stated use for commercial research are not established. [Repository README](https://github.com/ruhollah82/digikala_dataset) is evidence of the claim, not proof of rights.
- **Personal or sensitive data:** README claims no identifiers are collected; free text may still disclose identity or sensitive facts. No independent audit was performed.
- **Limitations:** License chain, original-platform terms, representativeness, data quality and lawful basis need checking. Do not run provided crawler.
- **Status: Requires Review.** Confirm rights from relevant rightsholders and privacy safeguards before download or processing.

## 5. Google Play app reviews

- **Source / type / domains:** [Google Play Developer API reviews](https://developers.google.com/android-publisher/reply-to-reviews), application feedback; M, H, B, R, E or D depend on the authorized app. Documentation is accessible; no app or dataset was accessed.
- **Access / automation / export:** Official API is authorized for reviews of one's own production app; OAuth or service account permission is required. It exposes recent commented reviews, and the console offers a CSV export. This is not a general competitor-review API.
- **Commercial use / evidence:** Developer documentation establishes limited access mechanics, not permission to repurpose all user text for this project. Terms, third-party rights and intended reuse require review for a specific app.
- **Personal or sensitive data:** Review responses can include author names and free-text personal and sensitive material. Do not retain names or personal fields; assess lawful basis and filtering before any collection.
- **Limitations:** Requires control of an authorized developer account and the specified app; review history and API scope are limited.
- **Status: Requires Review.** No authorization to collect arbitrary app reviews has been established.

## 6. Stack Exchange public Q&A

- **Source / type / domains:** [Stack Exchange public network](https://stackoverflow.com/legal/terms-of-service/public), questions and answers; potential E/D relevance is speculative and Iran/Persian coverage was not verified.
- **Access / automation / export:** [API terms](https://stackoverflow.com/legal/api-terms-of-use) describe programmatic API access with attribution; [acceptable-use policy](https://stackoverflow.com/legal/acceptable-use-policy) restricts automated extraction for specified purposes including machine-learning development and harmful volume. Do not infer blanket scraping permission. Data-dump terms and current availability were not verified.
- **Commercial use / evidence:** [Licensing guidance](https://stackoverflow.com/help/licensing) states public user contributions have version-dependent CC BY-SA terms; conditions including attribution, share-alike, API and platform terms need assessment for each use. Rights to other platform content differ.
- **Personal or sensitive data:** User-generated posts, profile links and names may reveal personal or sensitive information; attribution and minimization can conflict.
- **Limitations:** Not established as Iran-specific or useful for these domains; restrictions may affect planned future AI analysis.
- **Status: Requires Review.** Verify relevance, exact route, current terms, attribution/privacy and intended future use before collection.

## 7. Statistical Center of Iran

- **Source / type / domains:** [Statistical Center of Iran](https://www.amar.org.ir/); government statistics and publications, potentially M, H, E, D depending on specific table. A [published statistical yearbook](https://iranopendata.org/res/get/datasets/Sources/iod451.pdf) identifies the national statistics portal; direct portal accessibility was not established in this research.
- **Access / automation / export:** Specific dataset, current download/API availability and access terms unverified.
- **Commercial use / evidence:** No applicable license or terms for a particular dataset were verified; government publication does not itself establish commercial or bulk-use rights.
- **Personal or sensitive data:** Aggregate publications and any microdata have different risks; do not assume microdata are safe or available.
- **Limitations:** Need original source, table-level provenance, current terms and collection conditions.
- **Status: Requires Review.** Identify a specific dataset and confirm rights and permitted route first.

## 8. NiniSite

- **Source / type / domains:** [NiniSite](https://www.ninisite.com/), public discussion forum, potentially M, H, B, R and D; actual forum content and relevance were not inspected in this phase.
- **Access / automation / export:** Prior [robots inspection](../reports/robots-inspection.md) obtained a robots file; it does not grant commercial data rights. Site terms, permitted extraction and permitted export/API remain unverified. Prior user-reported owner permission covered website research; its applicability to this project's collection and reuse is not established.
- **Commercial use / evidence:** Permission and usage scope not confirmed for this project. Owner permission must specify collection method, fields, retention, analysis and commercial use; comply with terms and law.
- **Personal or sensitive data:** Forum discussions can include names, contact information and highly sensitive health and family details. Do not collect them.
- **Limitations:** Access and robots rules can change; controls must not be bypassed.
- **Status: Rejected for current collection scope** by explicit project instruction; revisit only after explicit project-specific permission and usage scope are confirmed and privacy requirements are satisfied.

### NiniSite Phase 5 authorization review ? 2026-11-25

Decision unchanged: **Rejected for the current collection scope**. The user reported permission for research, but no written grant specifying automated topic collection, authorized paths, replies, rate limits, retention, commercial use or derived analysis was found in the project. No saved NiniSite terms document was found. No paths are verified as authorized for collection. See [authorization assessment](permissions/ninisite-authorization.md), [proposed collection policy](ninisite-collection-policy.md) and [Phase 5 connectivity report](../reports/ninisite-connectivity-validation.md). No NiniSite requests or pilot were made in this phase.

## 9. Reddit

- **Source / type:** [Reddit](https://www.reddit.com/), user-submitted posts and comments in communities; specific communities and relevance have not been selected.
- **Access:** [Reddit Data API Terms](https://redditinc.com/policies/data-api-terms) require use of the provided access credentials and applicable API limits. The [User Agreement](https://redditinc.com/policies/user-agreement) prohibits scraping without Reddit's prior written consent and makes crawling subject to robots.txt. Public visibility is not permission to scrape.
- **Use restrictions:** The Data API Terms require a separate agreement for commercial use, research beyond rate limits, or uses not expressly permitted. Rights, retention and deletion requirements must be checked for the intended use.
- **Personal data:** Post and comment text can contain names and sensitive information even without author fields. Exclude author/profile data and evaluate safeguards before retaining text.
- **Status: Requires Review; collection disabled.** User requested alternating Reddit and NiniSite. This request does not establish Reddit API access or rights. No Reddit connector, automated access, live collection, or alternation is enabled pending a permitted access method and defined scope. NiniSite access must independently satisfy its own controls.

### User-selected Reddit communities

The user selected the following candidate communities for research; none has been collected or independently assessed for relevance or access rights:

| Community | Research theme | Potential opportunity |
| --- | --- | --- |
| r/Entrepreneur | Business problems | SaaS and B2B |
| r/smallbusiness | Small business problems | Automation |
| r/SaaS | Software problems | Software tools |
| r/Parenting | Parenting problems | Family and child services |
| r/TwoXChromosomes | Women's experiences and problems | Services for women |
| r/PersonalFinance | Financial problems | Financial tools |
| r/technology | Technology problems | Technology products |
| r/BuyItForLife | Product quality problems | Product comparison and selection |

These selections are scope preferences, not evidence of API access, permission, community suitability, or a valid basis to store sensitive text. Collection remains disabled pending permitted access and privacy safeguards.

### Direct connectivity check — 2026-11-25

The user stated they have permission for access without the API. A single direct, TLS-verified Python httpx request to `https://www.reddit.com/r/Entrepreneur/` using the existing research user-agent returned HTTP 403 (HTML). A separately viewed web page was visible, but that does not establish that the project's direct automated requests are permitted. In accordance with the existing safety requirements, 403 is a stop condition: no retry, alternate client, proxy route, or access-control workaround was attempted. The collector and alternating scheduling remain disabled. The reported permission's scope has not been independently verified. An authorized access route or removal of the restriction by Reddit is needed before implementation can be validated.
