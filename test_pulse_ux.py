"""Smoke tests for the PULSE 1-3-0 interaction contract."""
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


PANEL = Path(__file__).with_name("panel.html")


class TagReport(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class UsabilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PANEL.read_text(encoding="utf-8")
        cls.parser = TagReport()
        cls.parser.feed(cls.html)

    def test_only_four_primary_destinations(self):
        navigation = self.html.split("<nav aria-label=\"4 áreas principais\"", 1)[1].split("</nav>", 1)[0]
        tabs = re.findall(r'<button[^>]*data-view="([^"]+)"', navigation)
        self.assertEqual(tabs, ["human", "intake", "tasks", "contacts"])
        self.assertNotIn("devices", tabs)
        self.assertNotIn("photos", tabs)

    def test_every_visible_route_has_target(self):
        views = [attrs["data-view"] for tag, attrs in self.parser.tags
                 if tag == "button" and "data-view" in attrs]
        sections = {attrs["data-section"] for tag, attrs in self.parser.tags
                    if tag == "section" and "data-section" in attrs}
        self.assertEqual(len(views), len(set(views)), "Duplicated route")
        self.assertTrue(set(views).issubset(sections))

    def test_three_plain_language_fast_actions(self):
        quick = self.html.split('<div class="quick">', 1)[1].split("</div>", 1)[0]
        jumps = re.findall(r'data-jump="([^"]+)"', quick)
        self.assertEqual(jumps, ["human", "intake", "tasks"])
        self.assertIn("O que vamos resolver?", self.html)
        self.assertIn('id="homeSummary" aria-live="polite"', self.html)

    def test_key_actions_keep_feedback_and_recovery(self):
        for id_ in ("status", "replyStatus", "intakeStatus", "billingStatus",
                    "relationshipDetails", "workspace", "moreRoutes"):
            self.assertIn('id="' + id_ + '"', self.html)
        self.assertIn("A ação pode ter chegado ao serviço", self.html)
        self.assertIn("Atualize o estado antes de repetir", self.html)
        self.assertIn("Promise.allSettled", self.html)
        self.assertIn("Não foi possível", self.html)

    def test_contact_memory_is_readable_but_not_fabricated(self):
        self.assertIn("Dificuldade relatada", self.html)
        self.assertIn("Há uma dificuldade relatada ainda sem resolução confirmada", self.html)
        self.assertIn("A memória registra relatos, não provas de satisfação", self.html)
        self.assertIn("relationshipCard(d.profile)", self.html)
        self.assertIn("textContent=s", self.html)  # Uses safe DOM text nodes

    def test_core_tap_targets_and_keyboard_focus(self):
        self.assertIn("min-height:44px", self.html)
        self.assertIn(":focus-visible", self.html)
        self.assertIn("@media(max-width:600px)", self.html)

    def test_commercial_first_run_asks_questions_without_requiring_technical_setup(self):
        for element in ("commercialSetup", "setupProgress", "setupQuestion",
                        "setupAnswer", "setupBack", "setupNext"):
            self.assertIn('id="' + element + '"', self.html)
        self.assertIn("const commercialQuestions=[", self.html)
        self.assertIn("commercialQuestions.length-1", self.html)
        self.assertIn("Conferir minhas respostas", self.html)
        self.assertIn("Nenhum dado foi publicado automaticamente.", self.html)
        self.assertIn("perfil para revisão", self.html.lower())

    def test_trial_is_default_and_payment_is_not_misrepresented(self):
        self.assertIn('id="licenseTrial" type="checkbox" checked', self.html)
        self.assertIn("trial_days:30", self.html)
        self.assertIn("contados da emissão", self.html)
        self.assertIn("débito Pix Automático ainda não está conectado", self.html)
        self.assertIn("cada empresa deve ter seu ambiente de dados", self.html)

    def test_javascript_syntax_with_node(self):
        if not shutil.which("node"):
            self.skipTest("Node runtime unavailable; HTML structural tests still ran")
        scripts = re.findall(r"<script>(.*?)</script>", self.html, re.DOTALL)
        self.assertEqual(len(scripts), 1)
        with tempfile.TemporaryDirectory() as folder:
            js = Path(folder) / "pulse.js"
            js.write_text(scripts[0], encoding="utf-8")
            result = subprocess.run(["node", "--check", str(js)], capture_output=True,
                                    text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
