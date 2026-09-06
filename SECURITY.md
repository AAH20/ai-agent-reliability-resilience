# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Send a private report through the security contact published at [a2zsoc.com](https://a2zsoc.com) with the affected version, reproduction steps, impact and any proposed mitigation. Avoid including live credentials, personal data or customer records.

## Safe deployment

- Use only systems you own or are authorized to test.
- Begin in an isolated synthetic environment.
- Use least-privilege, short-lived identities and non-production destinations.
- Cap transaction value, retry count, concurrency and fault duration.
- Establish abort criteria, an accountable operator and rollback procedure.
- Treat experiment files, tool results and telemetry as untrusted input.
- Review generated evidence before sharing it; it may reveal transaction metadata.

The examples do not provide a production security boundary.
