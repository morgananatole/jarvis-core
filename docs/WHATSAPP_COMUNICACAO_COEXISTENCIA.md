# Comunicação no PULSE e no WhatsApp Business

Requisito: mesmo número no aplicativo nativo e na caixa privada do PULSE.
Esta primeira etapa implementa somente ecos de mensagens de texto enviadas
pelo WhatsApp Business, com atribuição de origem no histórico existente.

`WHATSAPP_APP_ECHO_SYNC=false` por padrão. Não muda credenciais, registro,
assinaturas de webhook, permissões Meta, IA ou cobrança. O número deve estar
habilitado oficialmente para coexistência antes de ativar o recurso.

O webhook existente verifica HMAC e phone_number_id. A origem do eco deve
corresponder ao número exibido nos metadados. Um eco de texto é armazenado como
saída humana, nunca como entrada para a IA. Não abre janela de atendimento,
concede consentimento de contato ou cria prova de entrega/leitura.

Após processar um envio recente no Business, pausa automação naquele contato,
marca atendimento humano e suspende o próximo retorno planejado. O proprietário
pode retomar JARVIS no painel. A marca temporal desse controle impede que um
evento atrasado anterior à retomada desfaça a decisão. Duplicados não reiniciam
o atendimento; falhas intermediárias são retomadas antes de marcar conclusão.
Eventos antigos são apenas arquivados. A coordenação usa o bloqueio por conversa
da arquitetura atual de instância única, sem garantir exclusão entre servidores.

Há atraso entre envio no celular e chegada do webhook: não é possível cancelar
uma resposta que a API já enviou antes de receber o eco. Homologar esse limite
com respostas simultâneas antes de oferecer a funcionalidade comercialmente.

Pendências: elegibilidade/onboarding preservador do número API-only; assinatura
Meta smb_message_echoes; prova real de eco; mídia/áudio, download autenticado,
edições/revogações, histórico e contatos smb_app_state_sync. Esses eventos ainda
não estão sincronizados. Não habilitar este primeiro estágio como sincronização
completa quando houver necessidade de editar/apagar conteúdo no Business.
Não importar histórico como mensagem nova nem disparar respostas para ele.

Homologação: confirmar mesmo número is_on_biz_app=true/platform_type=CLOUD_API,
testar texto enviado no celular, histórico no PULSE, pausa e retomada humana,
duplicados e entrega atrasada; texto enviado pelo PULSE continua usando a API.
Flag só deve ser habilitada depois dessas provas, sem desregistrar o número.
Reversão: desligar a flag e reverter o commit, preservando os eventos privados.

Contrato oficial consultado em 11/10/2026:
https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/smb_message_echoes
