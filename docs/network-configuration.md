# Network configuration

Copy `.env.example` to `.env`, which is ignored by Git. Empty proxy values allow HTTPX's normal environment and operating-system proxy discovery and network route. A VPN activated through the operating system can change that route without changes to the application; this tool neither controls nor configures a VPN.

For an authorized explicit proxy, set `HTTPS_PROXY` to an HTTP or HTTPS proxy URL with host and port; set `HTTP_PROXY` if HTTP destinations are used. Credentials, if required, belong only in the local `.env` or environment and must be URL-encoded. Process environment variables take precedence over `.env`. Explicit configuration disables HTTPX environment discovery; if a proxy is configured for one scheme but missing for the requested scheme, the request fails instead of falling back to a direct route. `NO_PROXY` is therefore not applied to explicit application proxy configuration. Never commit `.env` or share logs and configuration without review.

`HTTP_TIMEOUT` sets the default for connect, read, write and pool timeouts in seconds; the corresponding `CONNECT_TIMEOUT`, `READ_TIMEOUT`, `WRITE_TIMEOUT` and `POOL_TIMEOUT` override it. `MAX_RETRIES` is 0–5 retries after the first attempt. Retries use bounded exponential delays; HTTP 429 stops immediately, including when Retry-After is provided. TLS verification is not disabled. Network failures report an exception category, not full exception text that might contain credentials.

Prior World Bank connectivity checks timed out, and the authorized route was not established. Confirm network policy and proxy configuration before running live commands. The last diagnostic does not prove the API is unavailable.
