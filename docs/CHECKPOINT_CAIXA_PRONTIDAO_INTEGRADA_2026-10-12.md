# CHECKPOINT — caixa de prontidão integrada ao PULSE — 12/10/2026

## Alterações efetuadas
- panel.html: adicionada caixa expansível "Instruções e log de prontidão do WhatsApp" dentro do workspace autenticado, após descrição da jornada.
- O guia mostra oito etapas (Serviço, Conta Meta, API Meta, Webhook, Entrega, Coexistência, PULSE e Prontidão), registra estado e nota técnica curta, avança e copia relatório JSON.
- Estado é somente em memória da página, sem persistência automática. Não inserir segredos, telefone completo ou dados de clientes.
- tests/test_readiness_contract.py: adicionado teste de contrato que exige guia no workspace e botões de registro/exportação.
- Diagnóstico WhatsApp somente leitura no painel manual permanece disponível na mesma branch.

## Evidências e limitações
- Commits do guia e teste foram criados, mas testes Python/JS e Android ainda não foram executados.
- Não houve merge, deploy, alteração de Meta/Render ou teste real de entrega.
- As etapas são declaradas manualmente, não verificadas automaticamente. Não usar o registro como prova de funcionamento.

## Próximas ações
1. Executar suíte de testes offline em ambiente de execução do repositório; validar JS no navegador Android e desktop.
2. Corrigir falhas encontradas; verificar que alternância Espelho/manual preserva ações e login.
3. Conectar estados verificáveis da caixa aos endpoints autenticados e salvar logs técnicos sanitizados com política de retenção.
4. Conciliar branch com main/Work e revisar PR #32 antes de deploy.
5. Confirmar workspace Render; consultar /ready e /crm/whatsapp/connection com autenticação.
6. Testar webhook e entrega com destinatário autorizado; confirmar recebimento no WhatsApp Business App e pausa humana.

## Perguntas estacionadas
- Workspace Render correto?
- Destinatário autorizado para teste?

## Critério de pronto
Só declarar WhatsApp funcional após evidência de webhook assinado, envio, recibo entregue, funcionamento no celular e operação do PULSE.
