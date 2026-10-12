# AUDITORIA E LIMPEZA SEGURA — GitHub Actions — 12/10/2026

## Evidência real
Run 38254091320, workflow Functional tests, job 114827528896: 237 testes em 2,106 s, **1 falha**. Erro: test_company_box.py, teste test_generated_button_navigates_and_moves_same_conversation_without_execution. O adaptador DOM simulado não implementava appendChild, chamado pelo novo guia de prontidão do panel.html. Não é evidência de falha real do WhatsApp ou do MongoDB.

Run 38254091328, workflow PULSE readiness checks: sucesso.

## Correção aplicada
Commit 83c490e1fac36bc0d5a5c5c808d43e1e2459f638: acrescentado appendChild(item) ao adaptador DOM de teste, delegando a append(item). Mantém teste do comportamento da caixa sem alterar lógica de produção.

## Faxina e retenção
- **Não apagar histórico de CI, código antigo, backups, contatos, WABA, número ou credenciais sem inventário e confirmação de que não são usados.**
- Duplicações de notificações no Gmail são resultado de execuções falhas repetidas; corrigir a causa antes de arquivar mensagens.
- Logs de execução, falhas e correções são fonte de treinamento do instalador e devem ser catalogados em formato compacto, sem dados pessoais.
- Não foi realizada exclusão destrutiva neste turno. A remoção seletiva de arquivos precisa de inventário de referências e testes.

## Próximas etapas
1. Verificar se o commit 83c490e foi testado pelo GitHub Actions e revisar logs.
2. Se permanecer falha, investigar causas subsequentes e corrigir sem ocultar testes.
3. Verificar interfaces do PULSE e criar inbox real a partir de rotas CRM existentes.
4. Verificar coexistência oficial Meta mantendo o número no WhatsApp Business App.
5. Atualizar cartilha de instalação com o incidente: falha de mock DOM, não falha de produção.
6. Reconciliar PR #32 com main antes de deploy.

## Status
Correção commitada, execução pós-correção ainda não confirmada. Sem deploy, migração de número ou envio de mensagens.
