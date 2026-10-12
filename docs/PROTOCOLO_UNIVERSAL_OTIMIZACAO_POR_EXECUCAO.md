# PROTOCOLO UNIVERSAL — registrar para acelerar qualquer projeto

## Regra
Toda construção, reconstrução, instalação, configuração, correção, teste e publicação de qualquer projeto JARVIS deve produzir registro estruturado de execução. A documentação não é tarefa posterior: nasce com cada ação.

## Ciclo obrigatório
1. Buscar receita pré-existente no registro versionado antes de criar código ou solicitar cliques.
2. Selecionar a receita compatível com contexto, restrições e versão do serviço.
3. Executar somente ação autorizada, pequena e reversível; registrar evidência observada.
4. Em falha, identificar causa, solução e recuperação; catalogar antipadrão para evitar repetição.
5. Quando houver teste reproduzível, promover receita de rascunho para validada.
6. Atualizar instalador guiado para mostrar somente passos necessários e botões contextuais.
7. Medir cliques, duração, intervenções humanas, custo, falhas, reutilização e taxa de instalação concluída.

## Modelo de eficiência
- Objetivo: menos cliques, menos perguntas, menor tempo e menor custo **sem** sacrificar funções.
- Pré-preencher apenas dados não sensíveis e confirmados; nunca adivinhar credenciais.
- Detectar contexto antes de exibir opções; usar defaults reversíveis.
- Agrupar permissões de forma transparente, conforme regras da plataforma.
- Manter o Espelho conversacional e painel manual hierárquico.
- Evitar chamadas de IA quando uma receita determinística for suficiente.
- Guardar registro técnico sanitizado, com política de retenção e acesso por empresa.

## Estados de receita
draft_unverified -> validated_in_test -> validated_in_production -> deprecated.
Não promover por documentação apenas. Requer evidência, teste de recuperação, compatibilidade e aprovação da política de custo.

## Fontes de verdade
- toolkit/playbooks/registry.v1.json — índice de receitas e estado de validação.
- toolkit/playbooks/*.json — sequências executáveis/interpretáveis pelo futuro instalador.
- toolkit/project-run-template.v1.json — estrutura de log por projeto.
- docs/CARTILHA_MESTRA_PROJETOS_E_PRESERVACAO_NUMERO.md — políticas e proteção de ativos.

## Integração ainda necessária
O catálogo e o playbook são dados versionados, não um instalador autônomo já funcional. Próximas tarefas: validador de schema, motor de seleção, interface de poucos cliques, gravação segura de eventos e métricas, execução de testes e integração à instalação real.

## Proteção do número comercial
Mesmo número no WhatsApp Business App é restrição obrigatória. Não desregistrar nem migrar por tentativa. A coexistência precisa ser oficialmente elegível e comprovada. Se indisponível, modo assistido com número preservado.
