# Keychron M7 8K for Omarchy

Omarchy bar widget and settings panel for the Keychron M7 8K. Current version: **0.1.0 (pre-release)**.

## Features

- Show the mouse glyph, optional battery percentage, and charging indicator in the bar.
- Read battery, connection route, DPI stages, polling rates, profile, and button mappings.
- Refresh status at startup and once per minute.
- Apply a reported DPI stage through the Ultra-Link 2.4 GHz receiver.
- Display button mappings as read-only; button remapping is not implemented.

## Supported hardware

| Connection | Device ID | Support |
| --- | --- | --- |
| Wired USB | `3434:d056` | Status and battery reads; DPI apply is disabled |
| Ultra-Link 2.4 GHz | Receiver `3434:d028`, linked M7 `3434:d056` | Status and battery reads; DPI apply supported |
| Bluetooth | — | Active Bluetooth connection detection is not supported |

The plugin targets the M7 8K only. Do not assume compatibility with the M7 1K, other Keychron mice, or other firmware versions. Battery values are decoded from the M7 status report; they have not been independently cross-checked against Keychron Launcher.

## Install

Add the public repository with:

```bash
omarchy plugin add https://github.com/danielmrdev/omarchy-keychron-mouse.git
```

If Omarchy asks whether to enable it, choose **no** until you have reviewed the source under `~/.config/omarchy/plugins/daniel.keychron-m7/`. Then enable it in the right bar:

```bash
omarchy plugin enable daniel.keychron-m7 --section right
```

The manifest also sets `right` as the default bar section.

## HID permissions and data access

The plugin runs inside the Omarchy shell as the current user. The Python helper uses only Python 3.10+ standard-library modules. It sends HID query reports and reads the matching `/dev/hidraw` interface; it does not use the network, collect telemetry, invoke `sudo`, or change system permissions.

The current user needs read/write access to the matching HID interface because the device protocol uses output reports for queries. Permission setup depends on the Linux distribution. If access is denied, configure a narrowly scoped per-user device ACL for the supported IDs (`3434:d056` and `3434:d028`). Do not run Omarchy as root or make all `/dev/hidraw*` nodes world-writable.

Status polling does not change mouse configuration. **Apply DPI** is an explicit configuration write: it sends the shared DPI-stage setting through the receiver, then checks the reported state. Close Keychron Launcher and other mouse configurators before applying a setting. The plugin does not write button mappings, polling rates, profiles, macros, or firmware.

## Remove

```bash
omarchy plugin remove daniel.keychron-m7
```

This removes the installed plugin. It does not change the mouse's onboard settings.

## Development checks

Run from the repository root:

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
find plugin -type f -name '*.qml' -print0 \
  | xargs -0 qmllint -I "${OMARCHY_PATH:-/usr/share/omarchy}/shell"
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for hardware-test precautions and versioning. See [CHANGELOG.md](CHANGELOG.md) for changes.

## Versioning and publication

`manifest.json` is the version source of truth. Keep its version and the changelog aligned. Release tags should use `v<version>` (for example, `v0.1.0`). This repository has not been submitted to the Omarchy plugin marketplace. Recheck the current [development guide](https://plugins.omarchy.org/develop.html) and [publishing guide](https://plugins.omarchy.org/publish.html) before release.

## License

MIT. See [LICENSE](LICENSE).
