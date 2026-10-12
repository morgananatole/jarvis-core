"""Canonical, ordered project documents. Reads files; never invents comprehension."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORE = ['CENTRAL_NORMAS.md', 'AGENTS.md', 'docs/MISSAO_ATENDIMENTO.md',
        'docs/CONTRATO_EXPERIENCIA.md', 'docs/IA_EMPRESA_E_ATENDIMENTO.md',
        'docs/DECISOES_PRODUTO_2026-10-11.md']
SUMMARY = ('Aplicar decisões expressas e atuais do proprietário, distinguindo ideia de diretriz. '
           'Respeitar obrigações legais, regras da plataforma e permissões efetivas. '
           'Conversa é o centro; fatos aprovados, dados separados por empresa, pausa humana integral. '
           'Nenhuma afirmação de instalação, entrega ou venda pronta sem prova. '
           'Prospecção requer opt-in, janela/modelo aprovado, opt-out, deduplicação e revisão de falhas. '
           'Criação do produto não transfere dados de clientes; compartilhamento exige autorização e finalidade.')


def category(path):
    if path in CORE: return 'Visão, hierarquia e diretrizes atuais'
    if 'INSTAL' in path or 'ONBOARDING' in path or 'LICENC' in path: return 'Instalação e acessos'
    if 'RETOMADA' in path or 'CONTINUIDADE' in path or 'REVISAO' in path or 'PIX_E_' in path: return 'Histórico e evidências: conferir datas'
    return 'Referências operacionais'


def read_bundle(contents=False):
    paths = CORE + sorted({str(p.relative_to(ROOT)) for p in (ROOT / 'docs').glob('*.md')} - set(CORE))
    documents = []
    digest = hashlib.sha256()
    for path in paths:
        raw = (ROOT / path).read_text(encoding='utf-8')
        sha = hashlib.sha256(raw.encode()).hexdigest()
        digest.update((path + ':' + sha + '\n').encode())
        row = {'path': path, 'title': next((line.lstrip('# ').strip() for line in raw.splitlines() if line.startswith('# ')), path),
               'category': category(path), 'sha256': sha}
        if contents: row['content'] = raw
        documents.append(row)
    return {'version': digest.hexdigest(), 'documents': documents, 'summary': SUMMARY,
            'reading_verified': True, 'semantic_comprehension_automatically_verified': False,
            'private_journal_location': 'Memória do projeto; checkpoint externo do proprietário'}


def work_context():
    bundle = read_bundle()
    return 'Base normativa lida, versão ' + bundle['version'][:12] + '. ' + bundle['summary']
