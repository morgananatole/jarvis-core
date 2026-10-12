# Verificação de integração WhatsApp — checklist operacional

## Etapa 1: Serviço
- Consultar GET /ready, sem copiar configurações sensíveis.
- Verificar se o MongoDB está acessível e se faltam variáveis exigidas.
- Não considerar GET /health prova de conexão Meta.

## Etapa 2: Conta e API
- No painel autenticado, consultar GET /whatsapp/connection.
- Registrar somente api_read_access, coexistence_status e final de quatro dígitos.
- Se o resultado for 502/503 ou not_confirmed, não migrar, remover nem recadastrar o número sem validação da conta oficial.

## Etapa 3: Webhook
- Verificar assinatura e recebimento de evento no número esperado.
- Registrar ID de evento mascarado, horário, status e eventual falha, sem conteúdo de mensagem.

## Etapa 4: Entrega e coexistência
- Somente com destinatário de teste autorizado, enviar mensagem e conferir os estados aceito, enviado e entregue.
- Verificar recebimento no WhatsApp Business App, se a modalidade oficial permitir coexistência.
- Não inferir coexistência de HTTP 200.

## Etapa 5: PULSE
- Conferir inbox, pausa humana, retomada, ausência de duplicação e registro de recibos.
- Marcar pronto apenas com evidência ponta a ponta.

## Não fazer sem confirmação
- Alterar WABA, desvincular número, excluir app Meta, publicar mensagens para contatos reais, trocar credenciais ou efetuar cobrança.
