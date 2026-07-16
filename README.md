# Mediabox

A Home Assistant integration representing an HTPC Control Suite mediabox as a real HA device — entities, services, and live pointer control, replacing raw `rest_command`/`secrets.yaml` setups.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

## Requirements

- A mediabox running the HTPC Control Suite backend, reachable on your LAN
- Home Assistant 2026.2.0 or newer

## What this adds

- **`select` entity** — the currently running app, updated live via a server-sent-events stream, not polling
- **`text` entity** — search/type forwarding to the mediabox
- **`send_key` / `send_action` services** — device-targeted key and action dispatch, replacing `rest_command`
- **Pointer control** — a registered WebSocket command that powers the companion [Grid Remote Card](https://github.com/TheBugForge/grid-remote-card) fork's `trackpad` item type (relative cursor movement, click)

Multiple mediaboxes are supported natively — add the integration again per device, each gets its own address, key, and entities.

## Installation

### HACS (recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots in the top right corner and select **Custom repositories**
3. Enter `https://github.com/TheBugForge/Ha-Integration-Project-Codebase` and select **Integration** as the category
4. Click **Add**, then search for "Mediabox" and download it
5. Restart Home Assistant

### Manual

1. Copy `custom_components/mediabox/` into your Home Assistant config's `custom_components/` folder
2. Restart Home Assistant

## Setup

**Settings → Devices & Services → Add Integration → Mediabox.**

Enter your mediabox's address (`host:port`) and its API key. Generate a key from the mediabox's own config web UI (its bare IP address in a browser) if you don't have one yet.

Each mediabox is a separate config entry — repeat this step for a second device.

## Notes

- The API key is stored entirely in Home Assistant's own config entry storage — never in YAML, never exposed to any card or automation.
- `send_key`/`send_action` intentionally replace `remote.send_command` — there is no `remote` entity in this integration.
- Pairs with the [Grid Remote Card](https://github.com/TheBugForge/grid-remote-card) fork for a full dashboard remote, including the `trackpad` item type this integration's pointer command powers. The card works without this integration for its other item types; the `trackpad` item type specifically requires it.

## License

MIT — see [LICENSE](LICENSE).
