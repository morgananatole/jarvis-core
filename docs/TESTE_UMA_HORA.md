# Teste de uma hora — integração para homologação

`kind=trial_hour` em `/crm/licenses` cria uma chave sem prazo iniciado, com
um dispositivo. Não substitui assinatura nem os acessos internos/permanentes.
Não cria empresa/banco isolado: acesso é ao ambiente atual. Para outra empresa,
provisionar implantação e banco exclusivos antes de emitir.

1. Proprietário emite licença e código de instalação associado.
2. Usuário inscreve o navegador usando código e chave; chave privada WebCrypto
   permanece não extraível. Apenas status/início estão liberados antes do teste.
3. Proprietário verifica funcionamento real no dispositivo. Registra evidência
   privada sem segredos em `POST /crm/licenses/{id}/validate-trial`, com
   `functioning_verified=true`, `device_id`, `evidence` e `version` obtida de
   `/crm/trial-version`. Validação é uma declaração do proprietário, não um
   teste automático de WhatsApp, IA, banco ou pagamento.
4. Dispositivo consulta `GET /device/trial` com requisição assinada. Quando
   validado, usuário inicia por `POST /device/trial/start` assinado contendo
   `activate=true` e `version`. A única atualização condicional fixa
   `started_at` e `expires_at=started_at+3600s`, UTC.
5. CRM autoriza apenas após início e antes do prazo; status permanece disponível
   depois da expiração. Repetição autenticada devolve o mesmo prazo. Repetição
   da mesma assinatura/nonce é recusada. Proprietário pode revogar licença.

MongoDB grava o estado na coleção existente `commercial_licenses`. Não é usado
TTL para apagar licença ou mudar validade. Nenhuma migration destrutiva. Novos
campos existem apenas para `trial_hour`. Liberação de assento invalida evidência;
teste iniciado nunca admite reinscrição ou reinício. A versão usa
`RENDER_GIT_COMMIT`, com fallback local `pulse-hour-trial-v1`. Nova versão exige
nova validação antes do início; não reinicia teste já iniciado.

Painel: modalidade separada, prova/checkbox do proprietário, botão de início no
dispositivo. Um clique no login não inicia o relógio. Licenças de teste não são
assinaturas renováveis e não recebem preço Pix. Não há conversão automática.

Verificação local: 11 novos testes de contrato e segurança; suíte completa de
203 execuções aprovada. JavaScript do painel passa análise de sintaxe. Banco
simulado não prova concorrência real MongoDB. Layout/interação do painel novo
ainda exigem teste no navegador e celular; não publicados nesta etapa.

Homologação antes de produção: banco isolado, inscrição real em navegador,
status preparado, CRM negado, validação pelo proprietário, início explícito,
concorrência de dois requests, replay, reinício do serviço, vencimento no limite,
revogação e negação em outra empresa. Confirmar acesso interno e institucional
intactos. Reversão: reverter commit em caso de falha; não apagar registros nem
reativar testes já iniciados. Não confundir uma hora de uso com QR Pix PT1H.
