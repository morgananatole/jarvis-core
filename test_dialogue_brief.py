import unittest
from dialogue_brief import prepare, context


class BriefTests(unittest.TestCase):
    def test_typo_is_alias_and_original_evidence_is_preserved(self):
        text = 'quero  informacoes do tratameto para meu filho'
        data = prepare(text)
        self.assertEqual(data['original'], text)
        self.assertIn('tratamento', data['search_text'])
        self.assertEqual(data['intent'], 'information')

    def test_knowledge_needs_business_source_and_approval(self):
        card = {'id': 'a', 'business': 'nova_vida', 'status': 'approved',
                'source': 'owner-v1', 'text': 'Ambiente protegido', 'tags': ['tratamento']}
        self.assertEqual(len(prepare('tratamento', cards=[card])['knowledge']), 1)
        for bad in ({**card, 'status': 'proposed'}, {**card, 'source': ''},
                    {**card, 'business': 'other'}):
            self.assertEqual(prepare('tratamento', cards=[bad])['knowledge'], [])

    def test_previous_card_is_not_repeated_and_context_is_bounded(self):
        cards = [{'id': str(i), 'business': 'nova_vida', 'status': 'approved',
                  'source': 'owner-v1', 'text': 'x' * 5000, 'tags': ['tratamento']}
                 for i in range(6)]
        brief = prepare('tratamento', cards=cards, previous=['0'])
        self.assertEqual(len(brief['knowledge']), 2)
        self.assertNotIn('0', [row['id'] for row in brief['knowledge']])
        self.assertLess(len(context('tratamento', cards=cards)), 4300)

    def test_stop_and_human_have_priority_over_sales(self):
        self.assertEqual(prepare('valor, mas nao me mande mensagens')['intent'], 'stop')
        self.assertEqual(prepare('quero tratamento e um atendente')['intent'], 'human')
