"""Testes offline e sem rede do contrato de prontidão JARVIS."""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "toolkit" / "readiness-schema.v1.json"
CATALOG = ROOT / "toolkit" / "catalog.v1.json"
PANEL = ROOT / "panel.html"
INSTALLER = ROOT / "toolkit" / "installation-readiness.html"


class ReadinessContract(unittest.TestCase):
    def test_schema_has_eight_unique_stages(self):
        doc = json.loads(SCHEMA.read_text(encoding="utf-8"))
        stages = doc["stages"]
        self.assertEqual(len(stages), 8)
        self.assertEqual(len({s["id"] for s in stages}), len(stages))
        self.assertEqual(set(doc["states"]), {"pending", "passed", "blocked", "skipped"})

    def test_catalog_does_not_embed_secrets(self):
        doc = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertTrue(doc["principles"])
        self.assertTrue(doc["components"])
        for component in doc["components"]:
            if component.get("type") == "password":
                self.assertIs(component.get("persist"), False)
                self.assertIs(component.get("log"), False)

    def test_mirror_manual_and_navigation_present(self):
        page = PANEL.read_text(encoding="utf-8")
        for marker in ('id="jarvisMirror"', 'id="mirrorManual"', 'id="manualHub"', 'id="manualBackMirror"', 'data-manual-view="human"', 'data-manual-view="tasks"'):
            self.assertIn(marker, page)
        self.assertIn("mirror-first", page)

    def test_whatsapp_readonly_diagnostic_in_manual_panel(self):
        page = PANEL.read_text(encoding="utf-8")
        self.assertIn('id="checkWhatsAppReadiness"', page)
        self.assertIn("api('whatsapp/connection')", page)
        self.assertIn("api_read_access", page)
        self.assertIn("coexistence_status", page)

    def test_installer_has_no_external_dependencies(self):
        page = INSTALLER.read_text(encoding="utf-8")
        self.assertNotIn("<script src=", page)
        self.assertNotIn("localStorage", page)
        self.assertNotIn("sessionStorage", page)
        self.assertIn('id="export"', page)
        self.assertIn('id="clear"', page)


if __name__ == "__main__":
    unittest.main()
