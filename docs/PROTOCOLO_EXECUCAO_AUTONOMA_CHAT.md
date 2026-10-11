# Protocolo de execução contínua — Chat e Work

## Objetivo
Maximizar trabalho concluído por sessão e minimizar intervenções do proprietário. A sessão não continua em segundo plano depois de encerrada.

## Ciclo
1. Ler AGENTS.md, contratos e checkpoint privado autorizado.
2. Inspecionar branch, SHA, CI, deploy e ferramentas disponíveis.
3. Selecionar uma mudança pequena, reversível e verificável.
4. Implementar em branch quando houver risco; executar testes adequados.
5. Não confundir commit, deploy Live, simulação e entrega real.
6. Registrar o que foi feito, evidências, riscos, pendências e próxima ação.
7. Avançar à próxima tarefa sem exigir confirmações triviais.

## Limites de autonomia
Sem aprovação explícita não alterar credenciais, desregistrar número WhatsApp, contratar serviços, ativar cobranças, disparar campanhas, excluir dados reais ou mudar políticas do roteador gratuito-primeiro. Nunca pedir segredos pelo chat nem registrá-los em repositório público.

## Visão arquitetural
Separar organização/IA privada da empresa, atendimento/IA do cliente, memória por tenant e contato, fila durável, executor de tarefas idempotente, consentimento/opt-out, pausa humana atômica, auditoria, conectores por canal e isolamento verificável. Uma licença não substitui isolamento de dados.

## Ordem sugerida
1. Verificação de atendimento real e pausa humana.
2. Isolamento de empresa/contato e testes de não vazamento.
3. Correção/exclusão abrangente e memória longitudinal.
4. UX móvel da caixa e botões contextuais leves.
5. Integração real e recibos Meta; monitoramento e recuperação.

## Relatório de conclusão
Separar: verificado em produção, testado localmente, somente implementado, bloqueado, decisões necessárias e retomada exata. Preservar custos e credenciais existentes.
