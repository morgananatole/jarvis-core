# PULSE — REBASE OPERACIONAL: CUSTO ZERO, COEXISTÊNCIA E INSTALL & USE
Data: 2026-10-12

## Objetivo não negociável
- JARVIS/PULSE gerencia CRM, classifica leads, sugere respostas, registra contatos, atende e agenda retornos.
- Meta é o transporte oficial, não o motor de IA.
- Usuário exige nenhuma cobrança por mensagens Meta. **Isso restringe o que pode ser automatizado pela API.**
- Preservar WhatsApp Business App no celular e, quando elegível, coexistência oficial Cloud API.
- Não usar automação não oficial do WhatsApp Web, simulação de cliques ou rotação para contornar limites/bloqueios.

## Regra econômica verificada em outubro de 2026
> Atualização: consultar `PROSPECCAO_ZERO_GASTO_2026-10-12.md`. A página oficial
> lida nesta etapa informa serviços gratuitos na janela de atendimento; a tarifa
> secundária e franquia abaixo são histórico, não regra vigente de implementação.
- A Cloud API pode cobrar mensagens de marketing, utilidade, autenticação e serviço.
- Fontes secundárias reportam, no Brasil, desde 01/10/2026, R$ 0,3217 por marketing e R$ 0,035 por serviço/utilidade/autenticação; serviço tem franquia de 1.000 por mês. Confirmar sempre na tabela oficial Meta antes de configurar cobrança.
- Mensagens enviadas diretamente pelo WhatsApp Business App não têm a tarifa de envio da Cloud API; **isso não oferece interface oficial irrestrita para o JARVIS enviá-las automaticamente**.
- O JARVIS não pode eliminar cobrança de transporte da Meta. Um modo zero gasto deve bloquear qualquer envio API sem gratuidade verificável, ou preparar rascunho para envio humano pelo app.

## Arquitetura recomendada
1. Núcleo JARVIS: regras determinísticas, armazenamento compacto, filas, cache, IA opcional sob orçamento.
2. PULSE: CRM, grau de interesse, opt-in, pausas humanas, templates de resposta e retorno.
3. Adaptador de canal: somente Cloud API oficial; aplicativo Business para envio manual quando custo zero obrigatório.
4. Gate de custo: fail-closed. zero_cost_policy.py foi criado como módulo isolado e tests/test_zero_cost_policy.py como testes. **Ainda não conectado ao caminho de envio real; não há proteção de produção até essa integração ser feita e testada.**
5. Instalador: passos e logs sem credenciais, verificação de coexistência e capacidade de recuperação.

## Recomeço controlado — sem apagar tudo
- Fase A: inventário, backup e evidência do estado atual; preservar número e credenciais.
- Fase B: auditar elegibilidade de coexistência oficial; não desregistrar número para tentar resolver erro.
- Fase C: separar envio manual gratuito do envio automatizado pela API, com gate de custo.
- Fase D: validar webhook, leitura da API, pausa humana, recibos, controle de gastos.
- Fase E: converter erros, telas e soluções confirmadas em playbook versionado do instalador.
- Fase F: somente depois, reconciliar com main, testar e publicar.

## Trilha de evidência por passo
ID | tela/endpoint | pré-requisitos | ação | resultado esperado | resultado observado | erro | correção | reversão | status
Preencher apenas com observações reais. Nunca escrever segredo, telefone completo, mensagens privadas ou dados de pacientes.

## Status comprovado nesta sessão
- Criado zero_cost_policy.py: regra isolada que bloqueia categorias desconhecidas, transporte não oficial, ausência de consentimento e qualquer envio sem confirmação de gratuidade.
- Criado tests/test_zero_cost_policy.py: cinco testes unitários ainda não executados.
- Nenhuma mudança no envio de produção, na Meta, no Render ou no cadastro do número.
- A política isolada **não é garantia de custo zero** até ser conectada e validada no envio.
- O fluxo atual de coexistência ainda não foi comprovado ponta a ponta.

## Próxima ação técnica
1. Inspecionar todas as rotas de envio do main.py, crm_admin.py e tarefas; mapear os pontos que podem disparar cobrança.
2. Integrar gate no caminho único de envio, sem interromper recebimento ou atendimento humano.
3. Executar testes offline e testar cenários de mensagens cobradas/zero custo.
4. Inspecionar estado Meta/Render apenas no workspace confirmado.
5. Validar coexistência oficial e registrar cada resultado no playbook.
6. Produzir instalador guiado a partir dos passos reais, não de suposições.

## Pergunta essencial estacionada
A política desejada é **zero cobrança absoluta**, portanto envio automático pago bloqueado mesmo se isso limitar prospecção e retornos pelo WhatsApp. Este documento toma esse requisito como padrão até o usuário mudar a decisão.
