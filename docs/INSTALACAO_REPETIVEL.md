# PULSE — instalação repetível e diário técnico

## Decisão para reduzir tempo

Não reconstruir app, token, WABA e webhook a cada aparelho. Separar três casos:

| Caso | Caminho | Meta novamente? |
| --- | --- | --- |
| Outro celular/notebook da mesma empresa | Mesmo endereço, licença com vaga, código individual, autorização do navegador | Não |
| Nova empresa | Serviço/banco exclusivos, perfil revisado, número e conexão próprios | Sim, conectar os ativos dela; não copiar os da empresa anterior |
| Número atual já Cloud API, querendo Business nativo | Plano de migração e recuperação específico antes de qualquer remoção | Não repetir um signup que já retorna 2655122 |

A rota comercial de coexistência deve começar com uma conta Business App
existente e elegível, seguindo os requisitos Meta. Um número novo ou reinstalado
não é presumido elegível. Remover Cloud API não comprova que Business+API será
aceito depois. Até haver sequência comprovada, atendimento no celular pela
Comunicação do PULSE usa a API existente.

## Preparação do produto versus instalação do comprador

**Preparar uma vez e manter:** app da plataforma, configuração de login,
políticas reais de privacidade/exclusão, aprovação de provedor/permissões e
integração backend. Novos domínios de implantação precisam de autorização do SDK.

**Por empresa:** ativos autorizados, ambiente/banco exclusivo, número, perfil,
licença e teste real. **Por aparelho:** apenas acesso individual e teste de uso.
Essas etapas têm diários separados. Não imputar dias de desenvolvimento do
produto à duração de cada instalação futura.

O protótipo `/whatsapp/conectar` abre v4, mas descarta código OAuth. Ainda falta
o caminho produtivo de troca segura no backend, vinculação/inscrição verificada
e aceite real. Publicar uma página ou habilitar SDK não conclui onboarding.
App Review/Access Verification pendentes não têm prazo garantido por este kit.

## Mapa de atalhos

| Onde | Caminho/atalho | O que verificar |
| --- | --- | --- |
| Serviço PULSE | `/ready` | Configuração, banco e memória; não comprova Meta |
| Atendimento | `/painel` → Comunicação / Atender | Entrada, resposta, recibo, assumir/devolver |
| Preparar WhatsApp | `/painel` → Mais recursos → Acessos e conexão | Conexão atual e atendimento/pendências |
| Cadastro Meta | `/whatsapp/conectar` | SDK carregado, v4 e resultado; protótipo |
| Dispositivo | `/painel` → Acessos e conexão | Licença/vagas → código individual de 10 minutos |
| Meta | Meus apps → app → Casos de uso → WhatsApp → Personalizar → Torne-se um parceiro → Configurador de cadastro incorporado | Login/configuração, SDK e fluxo |
| SDK Meta | Configurador → Gerencie domínios → Gerenciar lista de permissão | Somente origem HTTPS autorizada |
| Login Meta | Login do Facebook para Empresas → Configurações | SDK ligado, HTTPS e modo estrito ligados |
| Aprovação Meta | Analisar → Análise do app; Verificação de acesso | Aprovado versus rascunho/publicado |
| Render | Serviço da empresa → Deploys / Environment / Logs | SHA Live, variáveis por nome e falhas |

URLs de painel Meta usam o ID do app/portfólio correto. Guardar IDs técnicos e
links privados no registro privado; nunca tokens ou URL OAuth com parâmetros de
sessão. Não colar URL de popup como atalho persistente.

## Comandos que não alteram produção

Na raiz do repositório, com Python e dependências instalados:

```bash
python scripts/installation_check.py plan --case new_device --number-state cloud_api --goal pulse
python scripts/installation_check.py plan --case new_company --number-state business_app --goal coexistence
python scripts/installation_check.py plan --case current_number --number-state cloud_api --goal coexistence
```

Diagnóstico de um ambiente: trocar `https://EMPRESA.onrender.com` pelo endereço
público correto. Criar a pasta privada primeiro. Não colocar o diário no Git.

```bash
mkdir -p installation-runs
python scripts/installation_check.py check --case current_number --number-state cloud_api --goal coexistence --base-url https://EMPRESA.onrender.com --out installation-runs/piloto.jsonl > installation-runs/piloto-resumo.json
python scripts/new_customer_plan.py --empresa 'Empresa Exemplo'
python -m unittest test_installation_journal test_whatsapp_signup test_device_installation -v
```

O check faz somente cinco GETs públicos, sem credenciais, redirecionamento ou
repetição automática. Mede tempo de cada requisição e produz `run_id`. O plano
do novo cliente não cria Render, banco, permissão ou licença automaticamente.

Anotar uma etapa feita pelo operador, usando o `run_id` do resumo:

```bash
python scripts/installation_check.py record --out installation-runs/piloto.jsonl --run-id RUN_ID_DO_RESUMO --step meta_signup --result blocked --evidence '{"meta_error_code":2655122}'
python scripts/installation_check.py record --out installation-runs/piloto.jsonl --run-id RUN_ID_DO_RESUMO --step delivery --result passed --evidence '{"verified":true}' --duration-seconds 20
```

`RUN_ID_DO_RESUMO` é substituído pelo identificador real; o exemplo não é uma
evidência. Não registrar `passed` antes de obter a prova. Fonte `operator_report`
permanece relato do operador, distinta de `public_http_probe`. HTTP 200 no
cadastro não prova SDK, entrega ou coexistência. O check nunca anuncia venda
homologada apenas porque as páginas responderam.

## Configuração padronizada por nome

| Grupo | Nomes | Regra |
| --- | --- | --- |
| Banco/empresa | `BUSINESS_ID`, `MONGODB_DATABASE`, `MONGODB_URI` | Ambiente exclusivo; `DB_NAME` é fallback legado |
| Proprietário | `CRM_ADMIN_TOKEN`, `CRM_ID_SECRET` / `META_APP_SECRET` | Segredos privados; não entregar ao comprador |
| Canal | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_WABA_ID`, `META_GRAPH_VERSION` | Ativos da empresa correta; sem troca às cegas |
| Protótipo SDK | `WHATSAPP_SIGNUP_APP_ID`, `WHATSAPP_SIGNUP_CONFIG_ID`, `WHATSAPP_SIGNUP_PREVIEW_ENABLED` | IDs públicos; flag somente após liberação de domínio |
| Ecos Business | `WHATSAPP_APP_ECHO_SYNC` | Desligado até coexistência e sincronização reais |

Aplicar alteração de variáveis por mesclagem, nunca substituindo toda a lista.
Não mudar roteador gratuito/pago, Pix ou tokens durante diagnóstico de aparelho.

Exemplo oficial do lançamento já usado em `whatsapp_signup.html`:

```javascript
FB.login(callback, {
  config_id: configId,
  response_type: 'code',
  override_default_response_type: true,
  extras: {version: 'v4', featureType: 'whatsapp_business_app_onboarding', sessionInfoVersion: '3'}
});
```

Não imprimir `response`, código OAuth ou token no console/diário. O caminho
produtivo de troca exige servidor e controles de acesso, não copiar código
sensível para o chat ou para comandos registrados.

## Erros conhecidos: uma tentativa útil, depois mudança de etapa

| Sinal | Interpretar | Próxima ação |
| --- | --- | --- |
| Domínio não incluído | SDK/domínio/origem de login incorretos | Conferir lista específica SDK; preservar HTTPS/estrito |
| Callback interno Facebook rejeitado | Atalho inadequado | Usar domínio próprio e SDK oficial; não insistir no callback interno |
| Link hospedado v4 abre popup v3 | Versão de diálogo não comprovada pelo link | Testar pelo SDK próprio e registrar versão real |
| 2655122 no número API-only | Este fluxo exige migração/desconexão | Interromper; plano de migração/recuperação antes de remover |
| App publicado, review pendente | Publicação não é aprovação de integração | Completar revisão/acesso do produto |
| HTTP 200 sem mensagem entregue | Disponibilidade não equivale a entrega | Conferir entrada, resposta aceita e recibo real |
| Render Free dormindo | Serviço indisponível/atrasado naquele instante | Medir disponibilidade; contratação só autorizada |
| Código de aparelho consumido/acesso existente | Instalação local, não Meta | Recuperar aparelho existente ou emitir novo código privado |

## Checklist de aceite e recuperação

Antes da venda: banco exclusivo, perfil aprovado, licença/aparelho, mensagem
recebida, resposta e recibo real, pausa humana integral e retomada, retorno
autorizado, condições de cobrança validadas. Se vender Business+API, acrescentar
uso nativo, eco/sincronização reais e limites de mídia/histórico informados.

Antes de migrar o número atual: comprovar elegibilidade e sequência oficial;
inventariar IDs, estado, inscrições, última entrega e meios de OTP/PIN em local
privado; confirmar backup aplicável, janela de interrupção e recuperação.
Excluir número, conta/WABA e desregistrar são operações diferentes. Não escolher
uma por semelhança do nome. Não executar reset sem aceite dessa sequência.

Por marco: `step`, resultado, origem, duração e evidência técnica permitida.
Não há campo livre de conversa. Guardar data, SHA, deploy e passo seguinte no
registro privado. O JSONL é 0600 e não permite symlink; fsync após cada registro.
Copiar/salvar o diário em armazenamento durável autorizado ao fechar a sessão.
Tempos de check HTTP são só rede/servidor, não tempo de instalação completa.

## Fontes

- https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started
- https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users
- https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/implementation
- https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/hosted-es

Requisitos encontrados em fontes Meta e percurso observado no configurador.
Nenhuma fonte nesta etapa comprovou migração preservadora de API-only para
Business App. As páginas completas de documentação devolveram 429 na leitura
externa; não tratar snippets como contrato completo de migração.
