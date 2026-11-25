# World Bank API validation ? failed

Test started: 2026-11-25 11:19:24 +03:30 (Asia/Tehran).

- **Official API URL:** https://api.worldbank.org/v2/country/IRN/indicator/SL.TLF.ACTI.FE.ZS?format=json&per_page=100
- **Indicator:** `SL.TLF.ACTI.FE.ZS`, female labor-force participation, ages 15?64, modeled ILO estimate.
- **Country:** `IRN` (Iran, Islamic Rep.).
- **Method:** one Python `requests.get` using normal system proxy configuration, 8-second connect and 10-second read timeouts, with redirects disabled.
- **Result:** `requests.exceptions.ReadTimeout`. The exception was classified as a timeout, not a `ProxyError` or `SSLError`; the exact timeout phase and cause were not established. No HTTP response, status, content type or response body was obtained. No API sample was saved.
- **Earlier preparatory attempt:** a proposed curl request was not sent because the system proxy value failed the script's conservative configuration-encoding check. Proxy details were not printed. No proxy settings were changed.
- **License evidence:** the [indicator page](https://data.worldbank.org/indicator/SL.TLF.ACTI.FE.ZS?locations=IR) labels the series CC BY 4.0; [World Bank data licensing](https://datacatalog.worldbank.org/public-licenses?fragment=research) describes attribution, commercial reuse and additional terms. This is prior source evidence, not a license retrieved from the failed API response.
- **API documentation:** [World Bank basic call structures](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures).

The response format, available years and current values could not be verified. The failure does not show that the World Bank API is unavailable generally. No unrelated indicators or replacement sources were queried. As instructed, Phase 2 stopped at this failure; source discovery, taxonomy, scoring and pilot work were not started.

Next step: have the network or proxy administrator investigate access to the official API with the existing approved network configuration, then rerun the validation after connectivity is restored. Do not bypass the system proxy or other network controls.

## Follow-up diagnostic ? 2026-11-25

A later configuration check found that the current Windows user proxy was disabled and Python selected no HTTPS proxy for the API, although local DNS resolution succeeded. No new API request was made because direct access was not confirmed as permitted and no enabled proxy was resolved. Consequently the original validation remains failed: no status, JSON, years, values or sample were obtained. The change from the earlier reported proxy selection and the timeout cause are unexplained. See [the connectivity diagnostics](world-bank-connectivity-diagnostics.md).
