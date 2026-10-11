# Revisão da primeira etapa de ecos — 11/10/2026

Resultado: três falhas reproduzidas e corrigidas em código local. Suíte completa:
**210 testes aprovados, nenhum skip**, com MongoDB Community 8.0.4 real,
exclusivamente em 127.0.0.1:27039, bancos aleatórios de teste removidos ao final.
Os provedores de IA e envio nos testes são simulados; nenhum pagamento,
mensagem real, Atlas, credencial ou configuração de produção foi usado.

## Base e estado da entrega

- Branch revisada: `fix/coexistence-echoes-20261011`.
- HEAD: `06830315a2ae433a141d063a201de43337444ea4` (PR23 existente).
- Main observada: `9847df20d766872ed757f5b431eaa859b79002f4`.
- Patch incremental local contra o HEAD da branch; sem push, merge ou deploy.
- `WHATSAPP_APP_ECHO_SYNC=false` permanece como padrão. Nenhum ambiente alterado.
- PR22 de Pix/trials não foi modificada. CI anterior da PR23 consta no registro
  privado; este patch não foi submetido ao CI remoto.

## Falhas e correções

| Falha reproduzida | Consequência | Correção |
| --- | --- | --- |
| Falha na fila após atualização do contato; retry incrementa `automation_epoch` novamente | Idempotência incompleta dos efeitos | Salvar `last_app_reply_id` junto da pausa na mesma atualização; retry completa fila/tarefa sem novo incremento |
| Mesmo ID, contato e origem, com texto diferente, aceito como duplicado | Conflito de conteúdo passa despercebido | Verificar também direção e texto antes de aceitar repetição; preservar o evento original |
| Nova entrada após eco reinicia espera; worker após cinco minutos compõe e envia resposta e reabre apoio da IA | Takeover no Business deixa de bloquear IA sem retomada explícita | Marcar `human_takeover_source=whatsapp_business_app`; bloquear apoio, worker e resposta automática de contato direto enquanto essa pausa existir; controle explícito no painel substitui a origem por `panel` |

As três regressões falharam no código original, antes do patch, e passaram
depois. O contador passou de 2 para 1 na repetição após falha; o conflito de
texto passou a levantar erro; a composição e o envio do worker deixaram de ser
chamados. O comportamento existente de espera para pausas do painel permanece.

## Testes mínimos e evidências

O módulo `test_whatsapp_coexistence.py` agora tem **21 casos**, dos quais
**4 usam MongoDB real**. A suíte completa inclui esses casos e as regressões do
produto principal, totalizando 210 execuções.

| Contrato | Evidência |
| --- | --- |
| Assinatura HMAC | Assinatura inválida retorna 403 sem criar contato/evento ou chamar IA/envio; válida aceita eco |
| Feature flag e número | Flag ausente/desligada e `phone_number_id` errado não têm efeitos |
| Origem e destinatário | Sender deve corresponder ao número dos metadados; destinatário inválido é rejeitado; alias brasileiro de 8/9 dígitos aponta para o mesmo contato e deixa outro contato ativo |
| Histórico | Evento outbound, origem Business, operador, data original; sem criar entrada, consentimento, janela de atendimento ou recibo fictício |
| Concorrência e repetição | 16 repetições locais e 32 chamadas concorrentes no Mongo resultam em um evento e um incremento |
| Recuperação parcial | Erros na fila, tarefa e marca final são retomados sem novo incremento; tarefa `suppressed` permanece assim no Mongo |
| Controle humano | Entrada posterior fica `human_waiting`; não chama IA nem envia menu de contato; worker não retoma automaticamente; retomada explícita no painel funciona |
| Ordem e persistência | Eco antigo fica só no histórico; eco anterior ao controle explícito não desfaz retomada; cliente Mongo reconectado preserva estado |
| Campos fora do escopo | `history`, `smb_app_state_sync`, image/audio/edit/revoke/contacts não entram no fluxo de IA nem geram contatos por eco |
| Lote inválido | Rejeitado antes de armazenar qualquer eco do lote |

Verificações adicionais: `git diff --check` e compilação Python dos arquivos
alterados aprovadas. A primeira execução completa expôs apenas uma falha no
teste de injeção: Motor devolve novos objetos Collection ao acessar atributos.
O teste foi corrigido para fixar a instância antes da injeção; a execução final
passou sem falhas ou skips. Não houve alteração da política de IA híbrida.

## Aplicar e repetir

O arquivo `coexistence-review.patch` é incremental contra o SHA0683031.
Na cópia dessa branch:

```bash
git apply --check /caminho/coexistence-review.patch
git apply /caminho/coexistence-review.patch
python -m unittest test_whatsapp_coexistence -v
```

Para executar os quatro casos Mongo, subir servidor de teste dedicado em
loopback (sem Atlas/produção) e executar no mesmo ambiente de rede:

```bash
PULSE_TEST_MONGO_URI=mongodb://127.0.0.1:27039 python -m unittest discover -s . -q
```

Sem essa variável, os quatro casos Mongo são pulados. Nesta revisão ela foi
configurada antes da descoberta dos testes e o processo Mongo foi encerrado
ao final. O workflow existente da branch já fornece Mongo para CI.

## Lacunas e limites preservados

- Não há prova de coexistência real, inscrição Meta, elegibilidade do número,
  entrega de eco real, uso no Android ou tela móvel. Esta revisão valida código.
- A URL de referência Meta foi tentada novamente, mas retornou HTTP429; o
  contrato desta revisão é o documentado na branch/registro, sem revalidação
  independente ao vivo nesta sessão.
- Mídia, áudio, edição, revogação, contatos e sincronização histórica completa
  continuam fora do escopo. Campos não suportados são ignorados.
- Exclusão concorrente entre processos/servidores não é garantida: o projeto
  usa bloqueio por contato na instância única. Não escalar afirmando garantia
  distribuída. O teste de reconnect não prova reinício de servidor Mongo.
- Um eco recebido após envio já aceito pela API não consegue cancelar esse
  envio. Enquanto a geração/envio mantém o bloqueio da conversa, o eco aguarda.
- IDs de eventos têm retenção de 90 dias; não há tombstone eterno contra replay
  após expiração. Eventos antigos não retomam o atendimento humano.
- Metadados de origem são conferidos dentro do payload assinado e o phone ID
  é comparado à configuração; não houve consulta externa à identidade Meta.

Próxima ação autorizável: revisar/aplicar o patch na branch separada e repetir
CI. Feature continua desligada; ativação e publicação exigem uma etapa posterior
com prova real Meta e testes de simultaneidade no celular.
