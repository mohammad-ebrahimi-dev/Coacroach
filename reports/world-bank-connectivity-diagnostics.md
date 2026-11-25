# World Bank connectivity diagnostics

Diagnostic session: 2026-11-25, approximately 11:21 +03:30 (Asia/Tehran). Target for any future HTTP check: `https://api.worldbank.org/v2/country/IRN/indicator/SL.TLF.ACTI.FE.ZS?format=json`. No HTTP or TLS connection to that endpoint was attempted in this session, because no currently enabled proxy was selected and authorization for a direct route was not established. No proxy settings were changed or secrets recorded.

## Configuration and DNS checks

- All uppercase and lowercase `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, and `ALL_PROXY` environment variables were unset in the process examined.
- Windows current-user Internet Settings had `ProxyEnable` disabled. A proxy-server value and bypass-list value existed but were not printed; existing values do not establish an enabled or authorized route. `AutoConfigURL` and `AutoDetect` registry values were not present in the examined key. This does not rule out other policy-managed discovery mechanisms.
- `netsh winhttp show proxy` succeeded and reported direct access. Its raw output was not retained, and this says nothing conclusive about organizational authorization for direct traffic.
- Python `requests` had `trust_env=True`, certificate verification enabled, and no HTTPS proxy selected by `get_environ_proxies` for the target. The observed setting differs from earlier NiniSite and World Bank checks where system proxy selection was reported. The reason for the difference was not established.
- Local DNS lookup of `api.worldbank.org` succeeded and returned 11 unique IPv4 addresses. IP addresses were not recorded. This does not establish a proxy's DNS behavior, TCP reachability, TLS or HTTP availability.
- No Python diagnostic scripts were found in the workspace file search; previous reports describe transient inspection commands rather than retained scripts.

## Controlled tests and limits

| Time | Client and proxy mode | DNS | Connection, TLS and HTTP | Elapsed / result |
| --- | --- | --- | --- | --- |
| Approximately 11:21 +03:30 | Local Python DNS lookup; no HTTP proxy | Success, 11 IPv4 addresses | Not applicable | Completed; exact elapsed time not recorded |
| Approximately 11:21 +03:30 | Python `requests`, current defaults | Local DNS success as above | Not attempted: no proxy selected; direct-route policy not established | Not measured; no exception or HTTP status |
| Approximately 11:21 +03:30 | curl with current defaults | Local DNS success as above | Not attempted: effective route not confirmed and no direct-route authorization established | Not measured; no exit status or HTTP status |
| Approximately 11:21 +03:30 | Python `requests`, explicit system proxy | Local DNS success as above | Not attempted: system proxy is disabled and none resolved for target | Not measured; no exception or HTTP status |
| Approximately 11:21 +03:30 | Direct client | Local DNS success as above | Not attempted: policy permission not established | Not measured |

Prior test: at 11:19:24 +03:30, Python requests to the approved indicator with `per_page=100` returned `ReadTimeout`, without an HTTP response; that prior test did not isolate DNS, TCP, TLS or HTTP phase and did not record elapsed time. The earlier NiniSite curl success was for another host and different configuration/time, and cannot prove current World Bank reachability. Requests ordinarily uses its configured CA bundle while this Windows curl build reports Schannel, but no TLS handshake occurred here, so no TLS difference or certificate failure is established.

## Conclusions and next action

DNS resolution succeeded. Current process-level proxy discovery selects no proxy, unlike the previous reported observation. It is not known why the configuration changed, whether a policy-managed proxy exists elsewhere, why the earlier timeout occurred, or whether the World Bank API is reachable. The timeout is not evidence that the API is generally unavailable. Available years, JSON format and values remain unverified; no sample was saved.

Ask the network administrator to confirm the authorized route for `api.worldbank.org`, whether direct access is permitted, and whether proxy settings are user/session or policy managed. Once the route is confirmed, rerun a single measured curl and requests comparison with certificate verification enabled, then validate and save the single approved indicator only if a successful response is obtained. Do not enable a dormant proxy or bypass network controls on an assumption.
