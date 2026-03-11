# CryptDesk

CryptDesk is a Python + PySide6 desktop application for direct peer-to-peer screen sharing with optional remote control and end-to-end encrypted transport.

## What this build includes

- Direct host/viewer connection over TCP without a central relay
- Ephemeral X25519 key exchange per session
- AES-256-GCM encrypted message transport
- Optional shared secret to harden session authentication
- Live screen streaming from the host's primary display
- Remote mouse and keyboard control gated by explicit host consent
- Session safety code shown on both ends for manual verification

## Security model

- Media and control packets are encrypted end-to-end after the initial public-key exchange.
- If you set the same shared secret on both peers, it is mixed into key derivation.
- The safety code should match on both peers. If it does not, terminate the session.
- This build is a direct desktop-to-desktop MVP. It does not include relay servers, TURN/STUN, or unattended access workflows.

## Prerequisites

- Python 3.11+
- Windows, macOS, or Linux desktop environment
- The host and viewer must be able to open a direct TCP connection. On LAN this usually works immediately. Across the internet you will usually need port forwarding or a VPN.

## Run locally

```powershell
python -m pip install -e .
python -m cryptdesk
```

You can also use the console entry point:

```powershell
cryptdesk
```

## Basic usage

1. Start CryptDesk on the host machine.
2. In `Share this device`, choose a port and optionally a shared secret, then click `Start sharing`.
3. Share one of the listed host IP addresses and the port with the viewer.
4. On the viewer machine, open `Control a device`, enter the host IP, port, and the same shared secret if used, then click `Connect`.
5. Verify that the safety code matches on both machines.
6. If remote control is needed, the host enables `Allow remote control` and the viewer enables `Enable remote input`.

## Build a desktop executable

Install the dev dependencies and run the packaged build script:

```powershell
python -m pip install -e .[dev]
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

PyInstaller output will be generated in `dist\CryptDesk`.

## GitHub Actions

Two workflows are included under `.github/workflows`:

- `python-package.yml` runs compile checks, `pytest`, and package builds on pushes, pull requests, and manual dispatch.
- `python-publish.yml` builds `sdist` and `wheel` distributions and publishes them to PyPI when a GitHub release is published or when manually triggered.

The publish workflow is configured for PyPI Trusted Publishing. In PyPI, register `cryptdesk` with this repository and the workflow file `python-publish.yml`, and use the GitHub environment name `pypi`.

## Tests

```powershell
python -m pytest
```

## Limitations

- The current build streams the primary display only.
- The current transport is direct TCP; NAT traversal and relay infrastructure are not included.
- Input injection depends on OS permissions and may require accessibility permissions on some systems.
- Keyboard layout translation is best-effort and may vary across platforms.
