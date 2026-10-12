# CHECKPOINT — preservação de número e cartilha universal — 2026-10-12

## Decisão do proprietário
Números comerciais antigos de empresas usuárias do BOOST/PULSE não podem ser perdidos, substituídos ou desativados. O cliente precisa continuar usando o mesmo número no WhatsApp Business App. Coexistência oficial com Cloud API deve ser verificada antes de qualquer alteração. Se não for possível, modo assistido preserva o número e a integração automática é marcada como indisponível.

## Entregas na branch
- docs/CARTILHA_MESTRA_PROJETOS_E_PRESERVACAO_NUMERO.md: processo universal de projetos, catálogo de acertos/erros, métricas e roteiro N0–N7.
- toolkit/project-run-template.v1.json: modelo versionado de execução por projeto, com restrições, orçamento e registros sanitizados.
- A política de custo zero anterior continua como módulo isolado, ainda não integrada ao envio em produção.

## Próxima ação sem depender do proprietário
1. Criar teste de contrato para garantir que todo novo projeto tenha restrições de preservação de número, orçamento e N0–N7.
2. Fazer o instalador carregar o modelo e exibir as etapas sem pedir dados sensíveis.
3. Adicionar exportação de log sanitizado e catálogo de erros comprovados.
4. Rodar testes CI, revisar alterações concorrentes e preparar PR.
5. Só depois, verificar coexistência real no Render/Meta com a conta autorizada.

## Não comprovado
A coexistência no número atual, envio e entrega reais, custos reais, execução CI e deploy. Nenhuma mudança foi feita na conta Meta ou no número.
