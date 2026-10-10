# Licenças comerciais JARVIS PULSE

Autorização de Morgan em 10/10/2026: ativar evidência externa e executor de retornos aprovados; criar validade para assinatura e opção permanente para venda especial. O projeto continua sendo informação → organização → contato → retorno, com revisão de dados incertos, memória institucional, consentimento e atendimento humano.

## Operação no painel

Entre como proprietário em `/painel`, abra **Dispositivos**, preencha nome da venda, modalidade e quantidade de dispositivos. Para assinatura informe uma data futura; para venda permanente não há vencimento nem cobrança recorrente. Guarde a chave exibida uma vez. Selecione essa licença e gere o código para cada navegador. O cliente informa código e chave comercial na ativação; depois entra com o dispositivo autorizado.

Cada navegador gera sua própria chave criptográfica P-256, não exportável pelo WebCrypto. O servidor guarda apenas a chave pública e hashes dos segredos de instalação/licença. Código: dez minutos, uso único. Assinatura por requisição: corpo, método, caminho, data e nonce; janela de 90 segundos e bloqueio de repetição. Licença vencida/revogada bloqueia o acesso privado mesmo após a instalação. Limite de dispositivos é reservado por operação atômica MongoDB. Revogar o dispositivo libera a vaga. Não limpe dados do navegador sem prever nova ativação.

Somente proprietário emite, renova e revoga licenças. A opção “Uso interno do proprietário” preserva os acessos atuais e exige o proprietário para liberar novos dispositivos. Clientes não podem gerar códigos, administrar licenças nem tornar seu acesso permanente.

## Endpoints

Todos abaixo exigem o bearer `CRM_ADMIN_TOKEN` do proprietário; essa credencial não deve ser entregue aos clientes.

| Método e endpoint | Entrada | Resultado ou interrupção |
|---|---|---|
| POST `/crm/licenses` | `label`, `kind`: `subscription` ou `permanent`, `max_devices`: 1–100; assinatura: `expires_at` ISO com fuso | ID e chave em texto claro uma única vez; 400 para validade/limite inválidos |
| GET `/crm/licenses` | — | Lista sem hash da chave, datas, dispositivos e renovações |
| POST `/crm/licenses/{id}/renew` | `expires_at` maior que anterior, `payment_reference` | Renovação auditada; não remove revogação; permanente retorna 409 |
| POST `/crm/licenses/{id}/revoke` | — | Bloqueia todos os dispositivos vinculados; registro permanece |
| POST `/crm/devices/code` | `label`, `license_id` | Código de instalação vinculado à licença ativa |
| POST `/crm/devices/{id}/revoke` | — | Bloqueia dispositivo e libera vaga da licença |

`POST /device/enroll` é público e recebe `code`, `public_key` JWK P-256 e `license_key` para instalação comercial. Não recebe chave privada. Código consumido não pode ser reutilizado, inclusive se a ativação falhar; proprietário gera outro código. Falta de chave correta ou vaga bloqueia antes do cadastro do dispositivo.

A cada requisição `/crm/*` assinada, o ponto de bloqueio é `DeviceAccess.verify`: autentica assinatura e nonce, verifica empresa, revogação, validade e pertencimento do dispositivo à licença. Vencimento retorna 403 `license_expired`; licença ausente/revogada retorna 403 `license_revoked_or_missing`. Falha criptográfica/repetição retorna 401. Owner bearer é a recuperação administrativa e não expira com licenças de clientes.

## CLI executável

Python padrão, sem dependências extras. Configure `JARVIS_BASE_URL=https://jarvis-core-ou8d.onrender.com` e `CRM_ADMIN_TOKEN` em ambiente seguro, sem publicar o token. O CLI recusa redirecionamentos e não repete automaticamente emissões.

```bash
python3 scripts/license_admin.py issue --label 'Assinatura Cliente A' --kind subscription --expires-at '2026-11-10T18:00:00-03:00' --devices 2
python3 scripts/license_admin.py issue --label 'Venda especial Cliente B' --kind permanent --devices 3
python3 scripts/license_admin.py device-code --license-id ID_RECEBIDO --label 'Celular do cliente'
python3 scripts/license_admin.py renew --license-id ID_RECEBIDO --expires-at '2026-12-10T18:00:00-03:00' --payment-reference 'Pagamento confirmado 123'
python3 scripts/license_admin.py revoke --license-id ID_RECEBIDO
python3 scripts/license_admin.py list
```

## Limites e pagamentos

Esta versão controla acesso ao app privado no serviço hospedado, não é DRM nem impede copiar um repositório público, alterar o código e hospedar uma cópia independente. Não converte o CRM atual em plataforma multitenant: cada empresa vendida precisa de implantação e banco isolados, com `BUSINESS_ID` próprio. Não ofereça a mesma base da Nova Vida a outra empresa.

Não há gateway de pagamento conectado: renovar exige referência de pagamento confirmado pelo proprietário. Sem renovação, a validade encerra o acesso. A modalidade permanente não solicita renovação nem dispara cobrança; continua revogável em caso de abuso. A chave comercial pode instalar até o limite autorizado, sempre com códigos individuais do proprietário. Chave perdida exige nova licença e revogação da anterior. Não armazene chaves em Git, logs, prints públicos ou documentos compartilhados.

Vencimento de licença do operador não desliga o WhatsApp institucional da Nova Vida nem tarefas já aprovadas. São controles distintos: o executor continua respeitando consentimento, pausa humana, janela/template e restrição ao destinatário de teste. Para futura cobrança do serviço WhatsApp por empresa, é necessário um contrato de serviço e um controle de assinatura no worker/webhook, além do pagamento autenticado. Não confundir essa etapa com a licença de acesso entregue aqui.
