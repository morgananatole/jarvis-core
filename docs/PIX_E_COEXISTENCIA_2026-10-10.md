# Pix, acesso comercial e WhatsApp no celular

Pedido de Morgan em 10/10/2026: otimizar a integração, manter WhatsApp comercial no telefone, evoluir uma caixa própria no PULSE e oferecer QR Pix que confirme pagamento e evite bloquear ou desbloqueie automaticamente a assinatura.

## O que foi implementado

O painel ganhou **Minha assinatura · pagar ou renovar**, disponível na tela de entrada mesmo após a validade da licença. Um dispositivo com licença vencida pode autenticar somente as operações de cobrança; CRM, cadastros e conversas continuam bloqueados até renovar. Dispositivo ou licença revogados continuam bloqueados também no pagamento. Acesso interno e licença permanente não têm cobrança.

Proprietário → Acessos e conexão → Licenças → definir preço e dias por pagamento. O cliente não escolhe preço, empresa ou quantidade de dias. Cobrança Pix gera QR e copia e cola, consulta o pagamento e renova a validade. Pagamento antecipado soma dias à validade existente; vencida, soma a partir da confirmação. Preço fica preservado no pedido, mesmo se a tabela mudar depois.

A implementação usa Checkout Transparente / Payments API do Mercado Pago, com `X-Idempotency-Key` persistente por pedido. CPF/e-mail do pagador seguem ao provedor; o app guarda apenas hash para repetição segura. Não há débito automático: cada período exige um Pix pago pelo cliente. Pix Automático/assinatura bancária é outro fluxo, ainda não implementado. Valores de venda são definidos pelo proprietário, não inventados pelo sistema.

Webhook é validado por HMAC e tempo; o servidor busca o pagamento diretamente no provedor e confere ID, vendedor recebedor, referência do pedido, valor, BRL, método Pix e ambiente real/teste. JSON dizendo “approved”, print ou clique do cliente não liberam acesso. A extensão é uma operação atômica na licença com registro dos pedidos aplicados; repetição do evento não soma dias duas vezes. Uma confirmação perdida pode ser recuperada por consulta no painel ou worker independente. Revogação administrativa não é removida por um pagamento. Estorno/disputa posterior aparece como revisão, sem reversão automática da validade já concedida; o proprietário deve tratar reembolso e acesso.

## Endpoints

| Endpoint | Acesso | Resultado / parada |
|---|---|---|
| POST `/crm/licenses/{id}/billing` | proprietário | Define `amount_cents` e `period_days`; permanente não cobra |
| GET `/billing/account` | dispositivo associado, inclusive vencido; proprietário com `?license_id=...` | Mostra licença, preço, pedido e conexão do provedor |
| POST `/billing/checkout` | mesmo acesso | `email`, `cpf`; cria/reutiliza pedido. 503 sem conta conectada; 409 sem preço, revogação ou criação ocupada |
| POST `/billing/check` | mesmo acesso | Consulta pagamento na API; aprovado com dados corretos → validade renovada |
| POST `/billing/webhook/mercadopago` | assinatura do provedor | Consulta estado real; assinatura inválida 401; divergência do pagamento 409; indisponibilidade 502 |
| GET `/crm/whatsapp/connection` | proprietário | Diagnóstico de leitura; não registra, remove ou migra o número |

## Configuração pendente para pagamentos reais

Variáveis privadas no serviço:

- `MP_ACCESS_TOKEN`: credencial do vendedor recebedor no Mercado Pago.
- `MP_WEBHOOK_SECRET`: assinatura secreta da aplicação no Mercado Pago.
- `MP_COLLECTOR_ID`: ID da conta recebedora; deve corresponder ao retorno da API.
- `BILLING_PUBLIC_BASE_URL=https://jarvis-core-ou8d.onrender.com`.
- `BILLING_MP_LIVE_MODE=true` em produção; `false` em teste. Pagamento de teste nunca libera licença quando o servidor espera produção.

No painel do Mercado Pago, configure evento `payment` e webhook `https://jarvis-core-ou8d.onrender.com/billing/webhook/mercadopago`. O app também envia essa URL na criação do pedido. Credenciais devem ser configuradas diretamente no ambiente seguro do serviço, nunca coladas em documentação/Git ou entregues ao cliente.

Não foi conectada conta recebedora nem realizado Pix real nesta etapa. Sem credenciais, a tela explica a pendência e não gera um QR fictício. Para um piloto, use uma licença separada, um dispositivo de teste, valor explicitamente aprovado pelo proprietário e teste confirmado na conta recebedora. Depois confira validade, repetição de webhook e acesso após expiração. Não reutilize as credenciais fictícias dos testes.

Worker consulta até cinco pedidos pendentes por passagem, com intervalo de cinco minutos por pedido e separado do processamento de WhatsApp. Cada processo verifica a fila a cada minuto. Render gratuito pode suspender o processo; webhook pode despertar o serviço e consultas no painel recuperam confirmação. Continuidade 24h requer infraestrutura que não suspenda, ainda não contratada.

## WhatsApp no celular: existência do recurso x situação deste número

A Meta anunciou oficialmente uso simultâneo de WhatsApp Business App e Business Platform com o mesmo número. É o caminho de coexistência. A documentação técnica de onboarding não pôde ser lida integralmente nesta verificação (Meta retornou 429); não foi comprovada elegibilidade ou migração do número atualmente registrado só na API. Não se realizou desregistro, exclusão ou reinstalação automática.

O diagnóstico tenta ler `display_phone_number`, `platform_type` e `is_on_biz_app`. Se campos ampliados não forem aceitos, recua para leitura básica e informa coexistência não confirmada. Acessibilidade da API não comprova entrega, histórico sincronizado ou compatibilidade do aparelho. A conta precisa completar um fluxo Meta compatível; não presumir que reinstalar e registrar o número fará a coexistência funcionar.

O PULSE já oferece uma caixa própria: **Conversas e contatos**, histórico, recibos, assumir atendimento e devolver à IA. Pode ser instalado como PWA no celular. Isso mantém atendimento pela API dentro do nosso app, mas não implementa todos os recursos do WhatsApp: grupos, chamadas, Status e sincronização completa não estão presentes. Recebimento WhatsApp automatizado atual processa texto; entrada privada de fotos/áudio/documentos para o banco é um fluxo separado.

## Valor comercial concreto

Produto prioritário: atender → organizar dados → preparar retorno → confirmar pagamento → manter acesso. Mostrar trabalho concluído e estados reais; não inventar economia de horas, vendas fechadas ou SLA. Explicar um benefício relevante e conduzir ao próximo passo em conversa curta. Manter Morgan no controle de urgências e decisões que exigem humano.

Fontes primárias consultadas em 10/10/2026:

- Meta: https://about.fb.com/news/2025/09/bringing-new-tools-to-help-businesses-boost-engagement-customer-support-and-discoverability/
- Fluxo Meta: https://developers.facebook.com/docs/whatsapp/embedded-signup/custom-flows/onboarding-business-app-users/
- Pix: https://www.mercadopago.com.br/developers/pt/docs/checkout-api-payments/integration-configuration/integrate-pix?scope=prod
- Webhooks: https://www.mercadopago.com.br/developers/pt/docs/checkout-api-payments/additional-content/your-integrations/notifications/webhooks
