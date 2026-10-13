import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginMetadataTests(unittest.TestCase):
    def test_panel_metadata_matches_manifest(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        panel = (ROOT / "plugin" / "Panel.qml").read_text()
        fields = {
            "pluginName": "name",
            "pluginVersion": "version",
            "pluginAuthor": "author",
        }

        for property_name, manifest_key in fields.items():
            with self.subTest(property=property_name):
                match = re.search(
                    rf'property string {property_name}:\s*"([^"]+)"', panel
                )
                self.assertIsNotNone(match, f"Panel.qml must declare {property_name}")
                self.assertEqual(match.group(1), manifest[manifest_key])

    def test_language_setting_defaults_to_system(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        widget = manifest["barWidget"]
        self.assertEqual(widget["defaults"]["uiLanguage"], "system")
        language_schema = next(
            item for item in widget["schema"] if item["key"] == "uiLanguage"
        )
        self.assertEqual(language_schema["type"], "string")


if __name__ == "__main__":
    unittest.main()
