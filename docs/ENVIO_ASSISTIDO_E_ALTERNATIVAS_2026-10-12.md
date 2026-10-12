# Contato assistido no WhatsApp — estudo, implementação e limites

## Objetivo desta etapa

Reutilizar CRM e fila do PULSE para organizar, programar e acompanhar contato
comercial sem usar a rota de mensagens paga da Cloud API. Abertura individual por
link oficial, envio humano e IA pausada. Não prometer bot gratuito integral ou
confundir clique com entrega. Preservar API e número atuais; não fazer migração
por tentativa. AGENTS/CENTRAL_NORMAS e read_before_work foram lidos/executados.

Base: 0e1eed80ec9504ba775a389b88795b54d4dd3a39, depois da PR33. A política de
templates de custo não verificado permanece. Nenhuma alteração ai_router,
provedor, segredo, cartão, variável Meta ou registro do número.

## Fontes oficiais consultadas

- Clique para conversa: https://faq.whatsapp.com/5913398998672934
- Listas de transmissão Business: https://faq.whatsapp.com/653415899610349/
- Uso responsável: https://faq.whatsapp.com/361005896189245/
- Política empresarial: https://whatsappbusiness.com/policy/

O link oficial abre conversa e pode preencher texto. Não confirma envio ou entrega.
A lista de transmissão exige número salvo pelo destinatário; é inadequada para
uma base em que isso não está confirmado. Uso manual individual não equivale a
autorização ilimitada para abordagem nem a uma API gratuita de envio automático.

## Caminhos estudados

| Caminho | O que permite | Limite |
|---|---|---|
| Cloud API atual | Respostas e automação já existentes, com registro de eventos | Iniciar conversa segue opt-in/modelo/custo; gratuidade de todo o diálogo precisa de confirmação vigente |
| Link individual no aplicativo | Rascunho revisado e abertura pelo operador | Envio manual; exige app/conta ativa; não lê resposta automaticamente |
| Lista de transmissão | Distribuição nativa conforme regra do aplicativo | Destinatário precisa salvar número; não resolve a base atual |
| Bot WhatsApp Web não oficial | Não implementado nem validado nesta etapa | Não oferece prova de estabilidade, gratuidade total ou proteção contra bloqueio |
| Chat no site/canais próprios | Possível evolução para aquisição e conversa fora do transporte WhatsApp | Não entrega mensagens por WhatsApp; depende de implantação, quotas e tráfego |

## Implementação

PULSE → Prospecção → Preparar contato assistido.

1. Selecionar cadastro existente, revisar mensagem e horário em Recife.
2. Guardar rascunho. Nenhuma mensagem ou chamada de IA é gerada.
3. Registrar referência da autorização **já obtida**, quando necessária; não
   adivinhar permissão por nome, antiguidade ou quantidade de contatos.
4. Quando chegar o horário, preparar abertura. Servidor revalida recusa/contato e
   grava pausa humana antes de fornecer link. Qualquer mensagem da IA para esse
   contato permanece bloqueada até devolução explícita pelo operador.
5. Clicar no link e confirmar o envio no WhatsApp. Aplicativo/navegador decide
   qual conta abrir; não garantir seleção automática do Business ou do número.
6. Registrar resultado informado: enviei, respondeu, recusou ou cancelar.
   Resultado manual não vira recibo Meta nem evento de outbound comprovado.
7. Recusa registrada bloqueia novos rascunhos/aberturas. Não retomar IA por timer.

`assisted_outreach` guarda rascunhos privados por ambiente. Preparação idempotente
rejeita reutilização de chave com outro conteúdo. Lista paginada, 100 por página;
consulta contatos de cada página em lote. Rotas exigem credencial proprietária;
não amplia acesso de dispositivos. Uma implantação/banco exclusivo por empresa
continua necessário. Não afirmar isolamento total de CRM legado.

Não há worker de disparo ou notificações deste modo. Horário é fila de trabalho,
não envio agendado. Não há captura automática de respostas do app nem IA lendo a
conversa neste modo. Atendimento automático existente pela API continua separado;
encaminhar uma conversa para ele exige conexão/eventos reais e devolução explícita.

## Estimativa operacional

Tarifa de mensagens da **Cloud API desta rota: R$0**, porque não chama o envio API.
Isso não torna internet, aparelho, operação humana, hospedagem ou IA ilimitados
gratuitos. Não inclui produtos pagos opcionais do aplicativo.

Hipótese de tempo para medir em piloto, não desempenho comprovado: 15–30 segundos
para revisar, abrir e enviar cada mensagem, excluindo espera e conversa.
- 100 contatos: 25–50 minutos.
- 500 contatos: 2h05–4h10.
- 2.000 contatos: 8h20–16h40.

Não é recomendação de quantidade diária nem limite anti-bloqueio. Só incluir
contatos com autorização e finalidade adequadas; interrupções e recusas prevalecem.
Preparação não consome tokens. Conversa com IA gratuita existente segue quotas;
custos futuros precisam ser medidos, não assumidos como zero.

## Teste e prova

13 testes específicos com dados fictícios: idempotência/conflito, empresa, dono,
data/fuso, pausa persistida, recusa antes e durante abertura, autorização com
evidência, URL/encoding, programação futura, lista e relatório manual. Nenhum
teste envia mensagens. JS verificado por Node; teste visual e celular são provas
distintas. Resultado completo da suíte/CI consta da PR.

Piloto real pendente: aparelho com conta WhatsApp ativa, contato próprio autorizado,
mensagem revisada, abrir link, conferir conta correta, envio humano, recebimento e
registro do resultado. Medir 10 operações autorizadas e revisar estimativa antes
de escalar. Em outubro, o diagnóstico anterior da conta atual informou app não
conectado e API acessível: não declarar este modo funcional no aparelho sem piloto.

## Checkpoint e reversão

Registrar antes de publicação e após CI/deploy na Memória do projeto. Código
reversível por revert; não apagar a coleção de rascunhos. Rascunhos não foram
criados com contatos reais nesta etapa. Não houve disparo, reupload de agenda ou
configuração externa. Retomar verificando SHA/deploy e elegibilidade do aparelho.

Próxima ação: homologar interface e piloto em telefone autorizado; confirmar a
conta WhatsApp disponível sem destruir a API. Automação gratuita integral permanece
objetivo não comprovado, e não é renomeada como envio assistido.
