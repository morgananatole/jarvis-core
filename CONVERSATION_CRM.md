# Pessoas, vínculos e próximos encontros

O contato tem ID numérico curto para operadores e chave HMAC indexada para
busca pelo telefone. Número de celular brasileiro com/sem nono dígito converge
para o mesmo cadastro. Use `CRM_ID_SECRET` estável antes de começar em produção;
na ausência dele usa META_APP_SECRET. Rotação dessa chave exige migração das
identidades para não dividir históricos. Telefone fica somente no banco privado.

`contacts`: nome de quem fala, forma preferida de tratamento, nome do familiar,
parentesco, idade relatada, cidade, substâncias relatadas, desejo de tratamento,
modalidade solicitada, preocupação principal, estágio, permissão de contato.
Não deduzir Sr./Sra., gênero, diagnóstico ou modalidade de internação. Não querer
tratamento é diferente de uma solicitação de internação involuntária. Cada fato
extraído guarda citação, mensagem de origem e data; correções atualizam o cadastro.
O cadastro não expira automaticamente. As informações não ficam em endpoints públicos.

`contact_events`: entradas e respostas por ID de mensagem, com histórico de
90 dias. `conversation_tasks`: uma próxima conversa por contato, revisada a
cada interação, com objetivo, data, prioridade e motivo. Pós-atendimento: revisão
de vínculo em 30 dias; decisão concreta: sugestão em 6h; dúvida comercial: 24h;
interesse indefinido: 7 dias. Horário explicitamente pedido prevalece. São sugestões,
não promessas de atendimento nem agendamentos clínicos confirmados.

Comprimento da conversa sozinho não qualifica uma oportunidade. Considerar sinais
de disponibilidade, preço, decisão e estágio. Pedido de não contato suprime a
tarefa. Não inferir permissão a partir de estar na agenda Google ou de falar muito.
Na retomada, carregar cadastro compacto e histórico recente em vez de enviar o
arquivo inteiro à IA. A extração acompanha a mesma chamada de resposta, sem uma
segunda chamada paga para cadastro. Funciona automaticamente no modo hybrid.

No modo test, registrar mensagens e organizar tarefas; resposta continua fixa,
sem extração semântica. Mensagens anteriores a esta implantação não são reconstruídas.
Uma aceitação de envio não prova entrega; o vínculo deve usar as respostas recebidas.

Importação: `python import_google_contacts.py contatos.csv` no ambiente privado
com MONGODB_URI e chave de identidade configuradas. Importador suporta CSV exportado
pelo Google com telefones em formato internacional, deduplica e prepara tarefas.
A agenda Google foi consultada, mas a exportação não entregou o CSV ao navegador; a lista não foi importada.

O roteador Groq, o painel privado, o executor e o rastreio de entrega estão implementados.
Para ativar retornos faltam revisão por contato, autorização registrada e templates
aprovados para reabertura fora da janela de atendimento.
Todos os envios proativos permanecem desligados. Não há disparo para toda a agenda.

Fotos: a API aceita imagem via media ID ou URL HTTPS. Criar catálogo de imagens
aprovadas com unidade, tema e legenda; a IA escolhe item do catálogo, nunca inventa
URL ou usa fotos pessoais de outros contatos. O catálogo e envio estão implementados; faltam ativos reais autorizados
e teste de entrega. A seleção automática permanece desligada.

## Painel e execução de conversas

`/painel` oferece histórico privado, contatos paginados, importação Google CSV,
revisão, suspensão e remarcação por propósito, e cadastro de fotos JPEG/PNG até 5 MB.
O acesso exige `CRM_ADMIN_TOKEN` de pelo menos 32 caracteres, fornecido pelo operador
no painel. A credencial permanece apenas na memória da aba. Nenhum dado do cliente
é servido sem autenticação. Consulte a variável no Render; não cole credenciais em chats.

Retornos aprovados podem ser executados pelo painel ou pelo worker interno de 60 segundos
quando `CONVERSATION_EXECUTOR_ENABLED=true`. O worker depende do servidor estar acordado;
não garante execução pontual em hospedagem gratuita. Estado `checking/sending` impede
repetição após reinício; aceitação incerta exige revisão. Mensagens novas invalidam
aprovação anterior; opt-out `PARAR` também funciona sem IA. O CRM não interpreta
importação de agenda como consentimento de prospecção.

Dentro de 23 horas da última mensagem, o retorno gera uma abertura com contexto, nome
conhecido e propósito usando o mesmo roteador gratuito/pago. O próximo diálogo responde
ao que a pessoa disser. Fora dessa janela, `WHATSAPP_TEMPLATE_SEND_ENABLED=true`,
`WHATSAPP_TEMPLATE_MAX_PER_DAY>0` e `WHATSAPP_WABA_ID` são necessários. A API verifica
aprovação real na Meta antes de usar `WHATSAPP_FOLLOWUP_TEMPLATE` (padrão
`nova_vida_retomada_conversa`, `pt_BR`). O teto diário reserva cada tentativa e nunca
é reposto após erro. Envio de modelo pode ter cobrança Meta, separada da IA.
O modelo foi submetido em 09/10/2026; o último estado observado foi **em análise**.
Por isso envio de modelos e execução automática permanecem desativados.

Fotos do catálogo só podem ser enviadas com `approved=true`, ID de mídia Meta e
janela de atendimento ativa. A IA pode escolher uma foto pertinente ao pedido do cliente
quando `MEDIA_AI_ENABLED=true`; só escolhe chaves do catálogo, nunca URLs inventadas.
Ative após cadastrar e testar fotos reais autorizadas. IDs Meta podem expirar; recadastre
as fotos quando necessário. Não há fotos da unidade carregadas ainda.

Webhooks autenticados registram separadamente horários `sent`, `delivered`, `read` e
`failed`. Aceitação pela API continua diferente de confirmação de entrega. Uma falha
incerta de texto ou foto exige revisão, sem reenvio automático.

## Pendências de ativação

- Groq e modo hybrid ativados; três respostas gratuitas foram observadas em 09/10/2026.
  O proprietário confirmou o recebimento. Verificar com um segundo celular após
  desativar a restrição de remetente de teste.
- Importar CSV pelo painel; exportação Google não forneceu arquivo ao navegador automatizado.
  Números sem DDI explícito são ignorados para evitar associação errada.
- Aguardar aprovação do modelo e definir limite de custo Meta antes de permitir retornos
  fora da janela de atendimento. Cada contato precisa de autorização registrada.
- Cadastrar fotos reais autorizadas; depois habilitar e testar seleção pela IA.
- O monitor gratuito de disponibilidade não garante servidor acordado nem horário dos jobs.

## Atendimento humano

Pedidos explícitos de atendente e palavras de urgência/resgate pausam a IA por
contato, registram fila privada e enviam uma única confirmação. Novas mensagens
continuam no histórico e atualizam a fila. Indisponibilidade de IA ou envio incerto
também encaminham para revisão humana. A detecção por palavras pode exigir ajustes.

No painel, abrir conversa, assumir atendimento, enviar resposta e devolver ao
JARVIS são ações separadas. Respostas do operador ficam no histórico utilizado
pela IA. A retomada da IA ocorre na próxima mensagem recebida. A fila atualiza a
cada dez segundos enquanto a aba está conectada; não há notificação externa para
Morgan nem garantia de atendimento imediato.

O operador só envia após assumir e dentro de 23 horas da última mensagem do
cliente. Cada envio possui chave de idempotência; resultado incerto exige revisão,
sem reenvio automático. Um bloqueio por contato serializa IA, operador e executor
na instância única atual. Múltiplas instâncias exigem bloqueio distribuído.

O aplicativo Meta está publicado. A análise de permissões avançadas como provedor
e a coexistência com o WhatsApp Business do celular são processos distintos;
não desconectar nem reinstalar o número oficial antes de concluir esse fluxo.
