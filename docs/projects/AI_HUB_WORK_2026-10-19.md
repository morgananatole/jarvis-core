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
