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
Não há acesso conectado ao Google Contacts nesta sessão; a lista não foi importada.

Para executar as conversas planejadas faltam: conta Groq ativa, executor de tarefas,
painel privado para revisar perfis e agenda, consentimento/opt-out, templates
aprovados para reabertura fora da janela de atendimento e rastreio de entrega.
Todos os envios proativos permanecem desligados. Não há disparo para toda a agenda.

Fotos: a API aceita imagem via media ID ou URL HTTPS. Criar catálogo de imagens
aprovadas com unidade, tema e legenda; a IA escolhe item do catálogo, nunca inventa
URL ou usa fotos pessoais de outros contatos. Faltam ativos aprovados, catálogo e
integração de envio/teste. Esta mudança não envia fotos.
