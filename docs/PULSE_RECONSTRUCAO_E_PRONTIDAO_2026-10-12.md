# PULSE — Reconstrução incremental e trilha de prontidão (2026-10-12)

## Decisão
Não reescrever o PULSE inteiro de uma vez. A integração do número é prioridade operacional; uma reconstrução total aumentaria risco e atraso. Refatorar em camadas, preservar endpoints e banco, manter fallback manual, registrar cada etapa com evidência e rollback.

## Evidências verificadas no código atual de main
- main.py define /health e /ready. /health responde status do serviço e **não** confirma a Meta.
- crm_admin.py expõe GET /whatsapp/connection com autorização.
- whatsapp_connection.py consulta Graph API do número, retorna final de telefone, plataforma e estado reportado de coexistência. Isso é diagnóstico de leitura, não confirmação de envio.
- webhook POST e envio estão implementados em main.py; funcionamento real de recebimento, resposta e entrega ainda precisa de teste ponta a ponta.
- Não foi possível consultar Render neste turno: integração solicita seleção explícita do workspace. Nenhuma configuração de produção foi modificada.

## Ordem de resolução do número WhatsApp
1. Verificar /ready (sem divulgar segredos) e verificar que banco e configuração exigida estão prontos.
2. Autenticar no PULSE e executar /whatsapp/connection. Registrar apenas estado e últimos 4 dígitos, nunca token.
3. Se Meta indicar não registrado ou coexistência não confirmada, interromper automação e verificar configuração oficial na conta correta. Não migrar, excluir, desconectar ou recadastrar número às cegas.
4. Confirmar recebimento de webhook com assinatura válida e evento do número correto.
5. Enviar mensagem apenas a destinatário de teste autorizado, observar recibos e status entregue; confirmar resposta no WhatsApp Business.
6. Confirmar pausa humana e retomada sem respostas duplicadas.
7. Só depois habilitar atendimento comercial real; respeitar consentimento e templates da Meta.

## Caixa de instruções e logs
Arquivo toolkit/installation-readiness.html: assistente de etapas offline, com status declarado e notas curtas, cópia de relatório JSON sanitizado, sem backend, armazenamento permanente, senhas ou números. Protótipo para posterior integração no painel autenticado e persistência segura de eventos técnicos, com retenção e acesso por empresa.

## Backlog executável sem acesso a contas
- [x] Inspecionar endpoints de prontidão e diagnóstico no código.
- [x] Criar trilha de instalação e bloqueios, sem dados pessoais.
- [x] Criar interface local de instruções e registro de etapas.
- [ ] Testar JS/HTML no navegador e automatizar validação do schema.
- [ ] Integrar trilha ao fluxo autenticado do PULSE e registrar versão/resultado no servidor com RBAC.
- [ ] Consolidar divergências entre main e PR #32; evitar sobrescrever Work.
- [ ] Testar Meta, Render e WhatsApp com evidência operacional.

## Perguntas estacionadas — somente se o diagnóstico exigir
- Qual workspace Render é o correto para leitura operacional? Não escolher sem confirmação.
- Se a Meta exigir nova vinculação: qual número/WABA e qual modalidade de coexistência foi aprovada? Confirmar no momento do bloqueio, sem alterar dados irreversíveis.
- Destinatário autorizado para teste real e confirmação do recebimento no celular.

## Critério de conclusão
Não usar 'WhatsApp pronto' antes de receber evento assinado, responder a teste autorizado, observar status de entrega e comprovar funcionamento no celular. HTTP 200 isolado não é suficiente.
