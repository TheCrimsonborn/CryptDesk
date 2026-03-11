# Security Policy

## Supported Versions

CryptDesk is currently pre-1.0. Security fixes are provided for the latest published release line only.

| Version | Supported |
| --- | --- |
| `0.1.x` | Yes |
| `< 0.1.0` | No |

If you are running an older build, upgrade to the newest release before reporting a bug unless the issue blocks upgrading.

## Reporting a Vulnerability

Please do not open public GitHub issues for exploitable security problems.

Use one of these channels instead:

1. Preferred: GitHub Private Vulnerability Reporting / a private GitHub Security Advisory for this repository.
2. If private reporting is not available, contact the maintainer privately through GitHub and include `[security]` in the subject or opening line.

When reporting an issue, include:

- the affected version and platform
- whether the issue affects host, viewer, or both
- clear reproduction steps or a proof of concept
- impact assessment
- whether user interaction, local access, or prior compromise is required
- logs, screenshots, or packet captures only if they do not expose secrets or safety codes

## Response Targets

Best-effort targets for confirmed reports:

- initial acknowledgement within 5 business days
- triage/update within 10 business days
- fix timing based on severity, exploitability, and release risk

If a report is accepted, please allow time for a fix before public disclosure.

## Scope

Examples of issues that are in scope:

- remote code execution
- authentication or session-binding flaws
- encryption, key derivation, or identity-verification weaknesses
- bypass of host consent for remote control
- arbitrary input injection without intended authorization
- packaging or release-pipeline compromise affecting shipped artifacts

Examples that are usually out of scope unless chained with a product flaw:

- social engineering
- vulnerabilities that require prior full compromise of the host or viewer machine
- local firewall, NAT, router, or VPN misconfiguration
- denial of service from users who already control one side of the session
- insecure use of the software contrary to documented trust checks

## Security Notes

CryptDesk is a direct peer-to-peer desktop support tool. It does not rely on a central relay in the current design. Operators should still:

- verify the safety code on both ends before enabling remote control
- keep the optional shared secret out of public chat logs
- grant remote input only when the connected peer has been verified
- install new releases promptly when security updates are published
