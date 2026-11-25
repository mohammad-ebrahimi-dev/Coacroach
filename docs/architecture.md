# MVP architecture

The CLI loads validated settings and constructs a shared HTTPX client. An approved-source connector checks its permission before retrieval, validates the response, normalizes aggregate observations and writes JSON and JSONL. The only implemented connector is the approved World Bank Iran `SL.TLF.ACTI.FE.ZS` series. See [development guide](development-guide.md) and [network configuration](network-configuration.md).

The client uses optional explicit scheme-specific proxies, bounded GET retries, TLS verification, safe diagnostics and no direct fallback from an explicit proxy. HTTP 429 stops immediately in accordance with the [source policy](source-policy.md). No crawler or user-content collection is implemented. Extension requires a source-specific decision and connector; the base abstraction is not authorization to collect other sources.
