# JARVIS Core

Servidor FastAPI: webhook autenticado → OpenAI Responses → resposta ao remetente.
Não faz campanhas ou envios para listas. Usa apenas a mensagem atual, sem histórico.

Build: `pip install -r requirements.txt`

Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Health check: `/health`. Configuração e conexão ao banco: `/ready`.
Callback: `https://jarvis-core-ou8d.onrender.com/webhook`.

Configure em Render Environment, nunca no GitHub:

| Variável | Conteúdo |
| --- | --- |
| WHATSAPP_VERIFY_TOKEN | Segredo para verificar o callback na Meta |
| META_APP_SECRET | Segredo do app Jarvis nova vida |
| WHATSAPP_ACCESS_TOKEN | Token novo com acesso à conta e ao número |
| WHATSAPP_PHONE_NUMBER_ID | ID do número registrado na API, não o telefone |
| META_GRAPH_VERSION | Versão suportada da Graph API, incluindo prefixo v |
| OPENAI_API_KEY | Chave privada de um projeto OpenAI com saldo |
| OPENAI_MODEL | Modelo disponível ao projeto e compatível com Responses |
| MONGODB_URI | Banco MongoDB persistente acessível pelo serviço |
| MONGODB_DATABASE | Opcional; padrão jarvis |
| JARVIS_INSTRUCTIONS | Informações aprovadas da empresa e contato humano |
| JARVIS_REPLY_MODE | `openai` (padrão) ou `test` (resposta fixa sem chamada de IA) |
| WHATSAPP_TEST_RECIPIENT | No modo `test`, telefone autorizado com país e DDD, somente dígitos |

No modo `test`, o servidor responde somente ao remetente autorizado em
`WHATSAPP_TEST_RECIPIENT`, sem construir cliente OpenAI. Não exige
`OPENAI_API_KEY`, `OPENAI_MODEL` ou `JARVIS_INSTRUCTIONS`; ainda exige
credenciais Meta válidas, registro do número, assinatura de webhooks e MongoDB.
Uma configuração inválida falha fechada. `/ready` informa `reply_mode`.
Este modo não é atendimento inteligente, não envia campanhas e não comprova
isenção de cobrança da Meta. Use o número gratuito de teste da Meta para
verificar transporte antes de migrar um número comercial.

O servidor inicia sem credenciais, mas `/ready` retorna 503 e não recebe
mensagens até a configuração estar completa. `/ready` não confirma validade
das credenciais, publicação do app nem registro do telefone.
Uma URI inválida também mantém `/health` disponível. `/ready` informa uma
categoria de erro sem expor credenciais. `DB_NAME` é aceito como alternativa
legada para `MONGODB_DATABASE`; não é necessário renomeá-lo.

Na Meta: verificar callback, assinar `messages`, vincular app à conta WhatsApp
e concluir requisitos de publicação do painel. O número ativo no WhatsApp
Business precisa de fluxo compatível. A migração tradicional pode exigir
liberar o registro no aplicativo; não excluir a conta sem esclarecer perda
de histórico e grupos e obter confirmação específica do responsável.

## Limitações e operação

MongoDB guarda IDs e estados para impedir duplicatas, inclusive após reinício.
Falhas são marcadas `review_required`; estados `processing` ou `sending` após
reinício também exigem revisão humana. Não há retentativa automática, porque
um envio pode ter sido aceito pela Meta antes de uma falha de conexão.
Mensagens com mais de 23 horas são ignoradas; mídia e status não geram respostas.
A resposta é processada dentro da requisição: pode haver retentativas da Meta
durante uma geração lenta, protegidas pelo ID persistente. Para alto volume,
substituir por uma fila durável com worker separado antes de escalar.
Não armazena texto nem telefone no banco; logs não incluem conteúdo ou segredo.

Render Free pode dormir; escolher serviço sempre ativo para atendimento contínuo.
Testar primeiro com conversa autorizada. Testes locais simulam os provedores e
não comprovam envio real. Nenhuma chave ou credencial está incluída no repositório.
