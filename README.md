# Iran market research collector

An MVP for the one approved World Bank aggregate indicator, Iran `SL.TLF.ACTI.FE.ZS`. It does not collect forum content or personal data. The live API response has not yet been verified in this environment; the unit tests use synthetic responses.

Use Python 3.12 or newer:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest -q
python main.py list-sources
python main.py test-connection
python main.py fetch world-bank-female-labor-force
```

Configure an optional authorized proxy in `.env`; see [network configuration](docs/network-configuration.md). The network commands contact the World Bank and should be run only over an authorized route. `test-connection` does not save the response body. A successful fetch writes aggregate JSON and JSONL under `data/processed/`; logs go to `logs/collector.log`. No raw response is stored. See the [development guide](docs/development-guide.md) and [source policy](docs/source-policy.md).

Run the local single-page monitoring dashboard with `python dashboard.py`, then visit `http://127.0.0.1:8765/`. The start button monitors public discussion topics until paused or stopped; it saves filtered first-page text in numbered JSONL files; pagination is not yet implemented, and automated filtering cannot guarantee anonymity. It accesses the site only when clicked. Use `python dashboard.py --demo` for clearly labeled synthetic activity with no NiniSite requests. See the development guide for limitations and controls.

The requested ID `SL.TLF.ACTI.FE.ZS` is the approved 15–64 series in the source registry, despite the MVP brief describing ages 15+. The API-provided label is preserved; no 15+ indicator is substituted. These values are labor statistics, not market-demand measurements.
