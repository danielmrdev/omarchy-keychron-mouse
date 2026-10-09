# Changelog

Notable changes to this project are recorded here. The manifest version is authoritative.

## [0.1.0] - Unreleased

### Added

- Omarchy bar widget with M7 glyph, optional battery percentage, and charging indicator.
- Startup status read and one-minute status refresh.
- Settings panel with connection route, battery, DPI stages, polling rates, profile, and read-only button mappings.
- Explicit shared-DPI-stage apply through the Ultra-Link 2.4 GHz receiver, with status verification.
- Python helper and offline parser/protocol tests for the M7 8K.

### Safety and limitations

- Status polling sends HID queries but does not change mouse settings.
- DPI apply is the only configuration write exposed by the plugin. Button mappings remain read-only.
- Wired USB and the Ultra-Link receiver are supported. Bluetooth active-connection detection and other M7 variants are not supported.
