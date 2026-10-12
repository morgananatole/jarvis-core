# CHECKPOINT — JARVIS / NOVA VIDA PULSE / WHATSAPP — 2026-10-12

## Objetivo prioritário
Fazer o número comercial funcionar simultaneamente no WhatsApp Business do celular e no PULSE pela coexistência oficial da Meta; atendimento automático Sobriedade, caixa humana, qualificação e acompanhamento de contatos. Não perder o número.

## Estado comprovado
- Repositório: morgananatole/jarvis-core, branch main.
- Render: workspace My Workspace (tea-d30pqf3ipnbc73djnueg), serviço jarvis-core (srv-d30stnripnbc73dtirgg), https://jarvis-core-ou8d.onrender.com
- Painel: https://jarvis-core-ou8d.onrender.com/painel
- Deploy do commit 0726947cfa458203dbd98e450cf2c70b867bde6a: LIVE, deploy dep-db6esvmk1f9s73fa4550, concluído 2026-10-12T14:29:23Z.
- Consulta anterior de logs de app no Render não retornou warnings/errors. Isso não comprova entrega de mensagens.

## Implementações já presentes
- Saudação instantânea Sobriedade em instant_greeting.py, protegida por NOVA_VIDA_INSTANT_GREETING (padrão false).
- Indicador de digitação da API em whatsapp_typing.py, protegido por WHATSAPP_TYPING_INDICATOR_ENABLED (padrão false).
- Logs de duração e classificação de respostas, sem expor texto/telefone.
- Diagnóstico proprietário GET /crm/whatsapp/connection em whatsapp_connection.py: consulta somente leitura da Meta, pode retornar coexistence_status not_confirmed.
- Diagnóstico de operação /crm/whatsapp/operations e painel mostrando estados das flags.
- Página whatsapp_signup.html / whatsapp_signup.py: prévia de Embedded Signup v4, com proteção WHATSAPP_SIGNUP_PREVIEW_ENABLED e IDs de app/config. Reconhece eventos FINISH, ERROR, CANCEL; callbacks tardios não sobrescrevem resultado.
- A página de signup NÃO troca código OAuth por token, NÃO vincula ativos e NÃO configura coexistência por si só.
- Caixa humana, pausa da IA e recursos comerciais existem em código; funcionamento completo não comprovado neste checkpoint.

## Bloqueios e cautelas
1. Não foi comprovado que o número está em coexistência oficial entre app móvel e Cloud API. Não desinstalar, remover, registrar ou migrar número pelo fluxo comum.
2. Não há teste real confirmado de mensagem recebida, resposta Sobriedade e entrega ao cliente.
3. Ainda falta fluxo seguro de troca de código OAuth, vínculo de ativos e verificação Meta. Nunca registrar tokens/códigos no log ou no GitHub.
4. Variáveis de ambiente e permissões Meta não foram validadas integralmente nesta sessão. Não afirmar que flags estão ativadas.
5. Não ativar prospecção indiscriminada; observar consentimento, políticas de templates e custos Meta. Não prometer custo zero.
6. Pendentes: testes de caixa humana, classificação de leads, follow-ups, licenças, Pix/webhook e cobranças.

## Próximas ações, por prioridade
1. Inspecionar configurações Meta e possibilidade de fluxo de coexistência; implementar backend OAuth seguro com validação de estado, armazenamento seguro e permissão apropriada, sem tocar registro do número.
2. Executar diagnóstico somente leitura autenticado de /crm/whatsapp/connection e /crm/whatsapp/operations, com acesso autorizado, sem expor segredos.
3. Confirmar webhook e fazer teste real de entrada, resposta e entrega; verificar AI fallback.
4. Ativar recursos opcionais somente após validação de conta/segurança/custos e testar pausa humana.
5. Validar CRM, prospecção com opt-in, licenciamento e pagamentos.

## Diretriz de execução
Fazer autonomamente tarefas técnicas pelo GitHub/Render sem repetir perguntas. Distinguir código publicado de função validada. Se a Meta exigir confirmação pessoal, solicitar somente a ação exata. Registrar checkpoint após etapas importantes. Não incluir credenciais nem dados pessoais.
