# Teste do cadastro Meta no domínio do PULSE

`GET /whatsapp/conectar` é uma página independente da caixa CRM. O protótipo
testa o fluxo oficial `FB.login` v4 com `featureType` de Business App,
conforme exemplo do configurador Meta. Não registra/desregistra números,
troca códigos por tokens, altera credenciais ou confirma coexistência.

Desligado por padrão. Habilitar somente depois de aprovar o Login com SDK
JavaScript na Meta e autorizar exclusivamente o domínio do serviço:

- `WHATSAPP_SIGNUP_APP_ID`: ID público do aplicativo.
- `WHATSAPP_SIGNUP_CONFIG_ID`: ID público da configuração existente.
- `WHATSAPP_SIGNUP_PREVIEW_ENABLED=true`: libera apenas o teste.

Não colocar segredos nesses campos. IDs devem conter apenas dígitos. O SDK
não é carregado ao abrir a página: o primeiro toque carrega o SDK e o segundo
abre o login, evitando popups bloqueados pelo carregamento assíncrono.
Sem configuração válida o botão fica desativado e a CSP não permite Meta.

A CSP do painel permanece intacta. A página de teste não recebe credencial
CRM, não consulta banco, não faz solicitações ao backend nem persiste dados
em armazenamento do navegador. Código OAuth recebido não é exibido,
registrado, enviado ou trocado. Eventos de sessão só são aceitos de origens
Meta HTTPS exatas durante uma tentativa iniciada; não constituem prova de
entrega, elegibilidade, registro ou acesso ao número.

Uma conta publicada não equivale a App Review/Access Verification aprovados.
Enquanto isso, testar só com funções autorizadas no aplicativo. Se o fluxo
exigir migração/desconexão, interromper e preservar a API atual. Não cadastrar
callback interno Facebook para tentar resolver o problema.

Reversão: desligar o flag e, se necessário, reverter a alteração de código.
Não exige migration nem mudança da configuração WhatsApp produtiva.

Validação: `python -m unittest test_whatsapp_signup -v`, suíte completa e
teste real de carregamento/login em navegador após autorização de ativação.
Provedores, pagamento e registro não são simulados como concluídos.
