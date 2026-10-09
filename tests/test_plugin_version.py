import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginVersionTests(unittest.TestCase):
    def test_panel_version_matches_manifest(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        panel = (ROOT / "plugin" / "Panel.qml").read_text()
        match = re.search(r'property string pluginVersion:\s*"([^"]+)"', panel)

        self.assertIsNotNone(match, "Panel.qml must declare pluginVersion")
        self.assertEqual(match.group(1), manifest["version"])


if __name__ == "__main__":
    unittest.main()
