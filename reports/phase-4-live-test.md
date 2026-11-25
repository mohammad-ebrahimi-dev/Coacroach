# Phase 4 ? Live World Bank integration test

Date: 2026-11-25 (Asia/Tehran). The approved World Bank indicator was tested over the application's normal network configuration. No other dataset was fetched. No network settings were changed and TLS verification remained enabled.

## Environment and tests

- Python **3.11.9**; installed: HTTPX **0.28.1**, Pydantic **2.14.4**, python-dotenv **1.2.4**, pytest **9.2.0**. Python 3.12+ remains untested in this environment.
- `python -m pytest -v`: **51 passed, 0 failed**; the automated tests use mocked HTTP.
- Uppercase and lowercase HTTP_PROXY, HTTPS_PROXY, NO_PROXY and ALL_PROXY variables were unset; `.env` was absent. The application selected no explicit proxy and allowed HTTPX's environment/system discovery. This does not establish the actual network route or exclude a VPN or transparent intermediary. No proxy values or credentials were recorded.

## Connection and metadata

`python main.py test-connection` returned **HTTP 200** without saving its response body. Its first attempt logged `ReadTimeout` after 15.328 s; the bounded automatic retry succeeded with HTTP 200 in 4.344 s. The cause of the first timeout was not determined. The subsequent fetch returned HTTP 200 in 0.640 s on its first attempt.

The [official World Bank indicator page](https://data.worldbank.org/indicator/SL.TLF.ACTI.FE.ZS?locations=IR) identifies the indicator as **Labor force participation rate, female (% of female population ages 15?64) (modeled ILO estimate)**, sourced from the ILO modeled estimates database and labeled CC BY 4.0. This is the 15?64 series, not the 15+ description in the earlier MVP request. The API response label in the saved records matches that name. Unit: percentage of the female population aged 15?64. Detailed methodology was not separately verified in this test. Attribution: World Bank World Development Indicators; ILO modeled estimates. License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); [World Bank licensing terms](https://datacatalog.worldbank.org/public-licenses).

## Fetch and verification

`python main.py fetch world-bank-female-labor-force` returned success and saved **66** observations. Source: `https://api.worldbank.org/v2/country/IRN/indicator/SL.TLF.ACTI.FE.ZS?format=json&per_page=1000`; retrieval timestamp in output: **2026-11-25 08:11:11.219260 UTC** (11:41:11.219260 Tehran). Files:

- [JSON](../data/processed/world-bank-female-labor-force.json)
- [JSONL](../data/processed/world-bank-female-labor-force.jsonl)

Both files parsed successfully and contained identical records. Every record carried indicator ID `SL.TLF.ACTI.FE.ZS`, country code `IRN`, a numeric or null value, and a unique year. The full year range is **1960?2025**; **36** values are non-null (1990?2025) and **30** are null. The connector validated response structure, indicator and country before saving. The two files are sequentially replaced, not an atomic pair; see the development guide for recovery limitations.

## Conclusion

The first real, validated aggregate dataset for the approved indicator was received and saved. This establishes that the endpoint responded during this test, not that it is always available or that labor-force participation demonstrates market demand. Python 3.12 compatibility and detailed metadata methodology remain to be verified.
