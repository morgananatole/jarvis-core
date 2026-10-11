# Decisões aprovadas — JARVIS PULSE — 2026-10-11

## Autorizações e limites
- Autonomia: implementar, testar e publicar automaticamente apenas mudanças de baixo risco, reversíveis e verificadas; ações sensíveis seguem AGENTS.md.
- Prioridade: Nova Vida ponta a ponta antes de expansão multiempresa.
- Atendimento humano: ao assumir, IA de atendimento interrompe integralmente mensagens e retornos para o contato, incluindo tarefas em processamento; evitar chamadas de modelo desnecessárias.
- Banco: IA organiza automaticamente; humano aprova informações críticas antes de ativar.
- Pagamentos: pode apresentar opções, jamais ativar serviços pagos sem autorização.
- Interface: caixa conversacional central, com botões contextuais e explicativos.
- Retornos: executar somente quando previamente autorizados, respeitando consentimento, opt-out, janelas da Meta, limites, deduplicação e pausa humana.

## Assistência durante atendimento humano — ideia, não recurso ativo
- Padrão aprovado: IA desligada para o contato sob atendimento humano.
- Mensagens-modelo com campos como (nome) podem ser renderizadas no servidor por interpolação determinística, sem chamada ao modelo: obter apenas dados autorizados do contato/empresa, escapar conteúdo, validar campos e reter envio se campo faltar ou houver ambiguidade.
- Exemplo ilustrativo: "Olá, senhora (nome)!" não deve enviar literalmente "(nome)" nem substituir com nome de outro contato.
- Assistência generativa ao operador é **opcional**, em interface privada e modo pago explícito; nunca acionar por padrão nem sem autorização de custo. IA não deve falar com cliente enquanto operador assumiu.
- A ideia de comandos/códigos via WhatsApp precisa de autenticação, autorização e desenho antifraude antes de implementar; não tratar código em mensagem como credencial suficiente.

## Integração Meta — meta de produto, não promessa
- Meta de UX: percurso guiado de até 10 minutos em contas elegíveis com pré-requisitos aprovados.
- Fluxo futuro: diagnóstico automático de configuração -> detecção de número/WABA/permissões/webhook -> reutilizar configuração autorizada -> apresentar só pendências -> teste de recebimento/resposta/recibo -> relatório.
- Separar caminhos: número novo Cloud API, número já conectado e coexistência oficialmente elegível. Não presumir que todo número aceita coexistência.
- Templates de configuração e checklists são úteis, mas não contornam exigências Meta, verificação, autorização e aprovação.
- Não desregistrar número, trocar tokens, reconfigurar produção ou contratar serviço sem autorização específica e rollback.

## Testes de aceite
1. Operador assume: nenhuma resposta automática, nenhum retorno atrasado ou em processamento enviado depois da pausa.
2. Substituição (nome): contato correto; ausência de campo impede envio; sem chamada IA; auditoria sem expor dados.
3. Isolamento: duas empresas com mesmo número lógico e contatos distintos não compartilham dados.
4. Integração: entrada real, resposta e recibo de entrega; falhas diagnosticadas.
5. Economia: medir chamadas ao modelo evitadas e latência, não inventar percentual.

## Próxima ação
Inspecionar implementação existente antes de codificar; executar testes sem credenciais reais quando possível; reservar operação Meta e testes telefônicos ao ambiente autorizado. Registrar commit, deploy e resultados separadamente.
