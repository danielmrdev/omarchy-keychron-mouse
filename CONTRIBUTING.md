# Contributing

## Requirements

- Omarchy shell with the plugin API used by this project. Development has been verified on Omarchy `4.0.4`.
- Python 3.10 or newer. The helper uses only the standard library.

## Local checks

Run these commands from the repository root:

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
find plugin -type f -name '*.qml' -print0 \
  | xargs -0 qmllint -I "${OMARCHY_PATH:-/usr/share/omarchy}/shell"
```

The Python tests use simulated HID reports. They do not access a mouse or send device reports.

## Hardware testing

The helper can send configuration writes. Do not run hardware write tests without approval from the device owner. Close Keychron Launcher and other mouse configurators first. Confirm that the connected device is an M7 8K and record its current settings. Check the device state after every write. If a write or restoration cannot be verified, report the state as uncertain; do not retry blindly.

The plugin's Apply action changes the shared DPI stage through the Ultra-Link receiver. It does not remap buttons or change polling rates, profiles, macros, or firmware.

## Version and release

1. Update `manifest.json` version using semantic versioning.
2. Add the user-visible changes and limitations to `CHANGELOG.md`.
3. Run all local checks and inspect the final diff.
4. Push changes to the public repository at `https://github.com/danielmrdev/omarchy-keychron-mouse`.
5. Keep the repository description concise, such as `Keychron M7 8K status and DPI control for Omarchy Linux`, with topics such as `omarchy`, `keychron`, and `linux`.
6. Before marketplace submission, re-read the current Omarchy publishing guide and issue form. Confirm the required repository fields, category, tags, and checklist.
7. Add an optional `preview.png` only after reviewing a clean, privacy-safe crop.
8. Keep the release tag aligned with the manifest, using `v<version>` (for example, `v0.1.0`).

The repository is public, but no marketplace submission or preview image is prepared. Do not publish releases or submit the plugin without maintainer approval.
