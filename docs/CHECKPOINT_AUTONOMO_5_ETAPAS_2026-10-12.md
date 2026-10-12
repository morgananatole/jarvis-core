# CHECKPOINT JARVIS/PULSE — 12/10/2026 — lote autônomo de cinco etapas

## Contexto
Solicitação: executar cinco etapas sem depender do proprietário, registrar próximo passo e preservar continuidade. Prioridade operacional: WhatsApp no celular e PULSE; não refazer o app do zero.

## Cinco entregas realizadas nesta branch
1. toolkit/readiness-schema.v1.json — contrato versionado de oito estágios e critérios de evidência.
2. tests/test_readiness_contract.py — testes offline do contrato, catálogo, Espelho, painel manual e instalador. **Criados, não executados** nesta sessão.
3. docs/WHATSAPP_CHECKLIST_SEM_SEGREDOS.md — roteiro de verificação do número e coexistência sem copiar tokens.
4. docs/UX_ESPELHO_MANUAL_CRITERIOS.md — critérios da experiência conversacional e árvore de botões manual.
5. Este checkpoint — próximo passo, bloqueios, perguntas estacionadas e regras de segurança.

## Próxima ação ao retomar (sem repetir investigação)
1. Verificar versão mais recente do main e branch PR #32, reconciliar mudanças do Work.
2. Rodar: python -m unittest tests.test_readiness_contract (ou discovery com -s tests -p test_readiness_contract.py); corrigir qualquer falha antes de mesclar.
3. Executar lint/sintaxe de scripts e teste real de navegador Android para o Espelho e a navegação manual.
4. Integrar o schema e a caixa de logs ao fluxo de instalação autenticado com acesso por empresa, mascaramento, retenção e evidência por etapa.
5. Na conta Render correta, consultar /ready e /whatsapp/connection autenticado; depois testar webhook, entrega e coexistência com destinatário autorizado.

## Perguntas estacionadas, apenas quando estritamente necessárias
- Confirmar qual workspace Render deve ser utilizado; a ferramenta exige seleção explícita e não autoriza adivinhar.
- Confirmar destinatário de teste do WhatsApp e aprovação para envio real.
- Se Meta exigir intervenção, identificar tela e operação específica antes de solicitar ação; **não** migrar/desvincular número por tentativa.

## Status comprovado
- Cinco arquivos criados/registrados em branch isolada, sem merge/deploy.
- Não houve mudança em Render, Meta, banco de dados ou mensagens reais.
- Os testes foram escritos mas não executados; nenhuma conexão real foi validada.
- O usuário não precisa agir para preservar esse checkpoint.

## Riscos e salvaguardas
- Main pode ter mudanças concorrentes; nunca sobrescrever cegamente.
- HTTP 200 não confirma WhatsApp operacional.
- Não registrar segredos, números completos, conteúdo de conversas nem dados clínicos em GitHub.
- Manter fallback manual, pausa humana e rotas críticas.
