# JARVIS — Vistoria fundacional e arquitetura de expansão (2026-10-12)

Status: diagnóstico e especificação, não implementação em produção.

## Fontes e limites
- Memorando original 'Jarvis meu IA' (Drive, 2025-08-13): identidade Segundo Eu, autonomia contínua, integração, memória, execução e supervisão do proprietário.
- Registro permanente 'JARVIS PULSE — Continuidade de Desenvolvimento' (Drive, atualizado 2026-10-12): estados comprovados, decisões, pendências, memória relacional e método 1-3-0.
- PULSE_Diagnostico_Instalacao_2026-10-12.md e INSTALACAO_REPETIVEL.md: coexistência, OAuth pendente, isolamento por empresa e diário de instalação.
- Diretriz expressa do proprietário nesta conversa: uma biblioteca/caixa de ferramentas do criador com links, tags, códigos, componentes, etapas e processos; instalação 'instale e use'; o JARVIS deve poder criar futuros produtos, sendo PULSE um produto, não seu limite.
- Revisão não exaustiva: outros manifestos e arquivos históricos ainda podem acrescentar ou alterar detalhes.

## Tese arquitetural
JARVIS é a plataforma executora e criadora; PULSE é uma aplicação construída sobre capacidades reutilizáveis do JARVIS. Evitar que decisões específicas de um segmento contaminem o núcleo. Crescimento orgânico significa ampliar capacidades coerentes e compostas, não proliferar menus, scripts ou integrações isoladas.

## Lacunas prioritárias
1. Governança de identidade: índice versionado dos manifestos e razões, com leitura obrigatória antes de alterações estruturais.
2. Memória de decisões: decisões, hipótese, justificativa, origem, validade, revisão e substituição, sem apagar histórico.
3. Catálogo de ferramentas: inventário tipado e pesquisável de conectores, ações, modelos, fluxos, UI, verificações e instaladores.
4. Motor de composição: converter objetivos em planos com pré-condições, permissões, custo, dependências, execução e rollback.
5. Instalação orientada: descoberta do ambiente, configuração por empresa e aparelho, verificação, diagnóstico e recuperação sem navegação manual dispersa.
6. Camada de execução: jobs assíncronos, fila, recibos, idempotência, reintentos limitados, auditoria e pausa humana.
7. Produto independente: SDK/API e contratos que permitam criar novas soluções sem copiar PULSE.
8. Evidência de produção: separar código, teste, deploy, execução real e homologação.

## Caixa de ferramentas do criador — contrato inicial
Cada ferramenta terá id estável, versão, categoria, finalidade, entradas/saídas tipadas, pré-requisitos, capacidades e permissões, custo estimado, restrições, documentação, teste de saúde, reversibilidade, referência de segredo (nunca segredo embutido), responsável e estado de homologação. Categorias iniciais: conectores, componentes de UI, templates, fluxos, validadores, instaladores, rotinas de dados e comunicação.

O catálogo não executa por si só: o planejador escolhe ferramentas; o executor verifica permissões e registra eventos; o verificador confirma o efeito; a memória grava decisões e evidências. Usar presets locais e cache para reduzir custo de IA, com atualização controlada.

## Estrutura proposta
- foundation/: manifestos, princípios, decisões, proveniência e políticas.
- toolkit/: catálogo, esquemas, templates, conectores e testes.
- planner/: objetivo -> plano de ações explicável.
- executor/: execução com autorização, idempotência, auditoria e recuperação.
- installer/: assistente 'instale e use' com planos repetíveis.
- memory/: conhecimento, decisões e contexto por empresa.
- products/pulse/: funcionalidades específicas de atendimento e CRM.
Esses nomes são sugestão de organização, não diretórios existentes confirmados.

## Regras de evolução
- Antes de implementar, vincular demanda ao manifesto, necessidade, componentes existentes e justificativa.
- Reutilizar antes de criar; evitar abstração prematura e acoplamento entre clientes.
- Preservar logs/eventos existentes: alterações apenas aditivas ou migradas com plano de recuperação.
- Não modificar Render, Meta, MongoDB ou produção enquanto o Work puder estar realizando alterações concorrentes sem verificar estado, commit e propriedade da operação.
- Fazer mudanças isoladas e reversíveis; nunca confundir simulação com validação real.

## Próxima implementação segura
1. Inventariar código e manifestos restantes.
2. Criar schema do catálogo de ferramentas e 3 exemplos não operacionais: verificador de instalação, modelo de formulário de cadastro e botão contextual.
3. Testar validação de schema, versionamento, permissões e referências de segredos.
4. Integrar planejador inicialmente em modo de pré-visualização, sem executar ações externas.
5. Só depois conectar executores reais, um por vez, com evidências e aprovação.

## Checkpoint
2026-10-12: diretriz de criador universal e caixa de ferramentas registrada. Nenhum log, evento, banco, webhook, número, token ou deploy alterado. PAF-01 em branch isolada; trabalho futuro deve confrontar os demais manifestos e o estado atualizado do Work antes de merge.
