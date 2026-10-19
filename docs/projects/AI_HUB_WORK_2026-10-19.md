# WORK / Projetos — JARVIS AI Hub
ID: JARVIS-AIHUB-20261019
Estado: PLANEJADO; DESABILITADO; NÃO IMPLANTADO.
Origem: análise visual de vídeo Inner AI e pedido do proprietário.
Acesso futuro: JARVIS > Projetos > Work > Central de IAs; JARVIS > Integrações > Central de IAs; JARVIS > Atualizações > Recursos disponíveis.
Objetivo: botão que abre interface de orquestração de modelos, sem ativar execução ou cobrança.
Integrações propostas: adaptadores OpenAI/Groq/outros, catálogo de capacidades, roteador de tarefas, avaliador, logs, orçamento e checkpoints. Nenhuma integração externa está conectada por este registro.
Política: default OFF; nenhum token em logs; sem chamadas de rede quando desabilitado; opt-in por sessão; cotas por tarefa/dia/mês; previsão de custo e custo real; aprovação antes de exceder orçamento; preferir custo baixo sujeito a teste de qualidade; fallback com teto e prevenção de loops; idempotência; segregação por projeto/empresa.
Logs mínimos: correlation_id, project_id, device_id pseudônimo, modelo/provedor, decisão de roteamento e motivo, início/fim, tokens, custo estimado/real, verificação de qualidade, tentativas, falha, fallback, aprovação e resultado. Sem prompts sensíveis por padrão.
Escada: validar pedido > escolher capacidade > estimar custo > executar > verificar qualidade > corrigir com limite > fallback > revisão humana > checkpoint.
Multi-dispositivo: servidor sincroniza estado, autenticação e permissões por dispositivo, revogação e operação offline apenas para tarefas locais autorizadas.
Aceite: OFF sem consumo; botão apenas abre interface; ativação explícita; logs verificáveis; teste de custo/qualidade; teste em Android/Linux; acessibilidade; backup e restauração; rollback.
Impacto: não alterar WhatsApp/PULSE, cobrança ou deploy em produção sem testes e autorização.
Próximas ações: inventariar front-end Work e serviços; implementar UI + APIs sob feature flag; testes automatizados; homologação sem produção; publicar somente com autorização.

## Diretriz adicional — custo mínimo contínuo e pontes preparadas (19/10/2026)
Objetivo permanente: procurar e avaliar soluções gratuitas, open source, execução local, cotas gratuitas, cache, batching e provedores econômicos antes de consumir serviços pagos. Gratuidade é alvo de otimização, não promessa de disponibilidade ou qualidade idêntica.
Roteamento: estimar qualidade mínima e custo; testar alternativas gratuitas; escolher a menor despesa entre candidatas que atinjam os critérios; medir qualidade observada, latência e custo real; reavaliar periodicamente. Se nenhuma atingir o mínimo, oferecer opção paga com custo previsto e aprovação explícita; não degradar silenciosamente o resultado.
Preferências: modelos locais quando hardware e tarefa comportarem; soluções gratuitas remotas dentro de limites e termos; cache com privacidade e expiração; reduzir tokens sem perda de requisitos; processamento assíncrono; fallback sem repetição infinita.
Instalação/configuração: apresentar um assistente único que inventarie TODOS os conectores e permissões disponíveis por plataforma (arquivos, rede, microfone, notificações, calendário, e-mail, navegador, APIs, dispositivos, armazenamento). Permitir configuração antecipada e testes de conexão; solicitar permissões por escopo com finalidade clara e consentimento do sistema/usuário; jamais contornar recusas, conceder acesso irrestrito oculto ou guardar segredos em claro. Permissões não disponíveis ficam listadas como pendentes com botão para conectar depois. Pontes desabilitadas permanecem instaláveis/descobertas, sem atividade de rede nem custo até habilitação.
Observabilidade: registrar inventário de capacidades, permissão concedida/negada/expirada, teste de ponte, motivo de seleção do provedor, economia estimada/real e motivos de fallback; não registrar credenciais.
Critérios de aceite adicionais: tarefa gratuita válida quando houver alternativa com qualidade suficiente; comparativo de custo por tarefa; relatório de economia; onboarding de permissões completo e revogável; nenhuma ponte silenciosamente ativa.
