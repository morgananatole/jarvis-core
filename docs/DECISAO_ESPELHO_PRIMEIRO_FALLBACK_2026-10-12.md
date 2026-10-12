# Decisão de produto — Espelho primeiro, painel manual visível

Data: 2026-10-12

## Preferência confirmada
A primeira experiência é uma tela essencialmente vazia com presença luminosa oscilante e conversa como controle principal. A IA busca ferramentas existentes, executa tarefas locais conhecidas e só materializa campos ou botões quando necessários. Um botão **Painel manual** deve permanecer visível, permitindo trabalhar sem IA. A IA paga é opcional; o modo econômico é padrão.

## Viabilidade e limites
- A interface estática em HTML/CSS/JS tem custo marginal muito baixo e pode ser servida pelo serviço atual.
- Regras locais, catálogo, busca por palavras-chave, templates e cache reduzem dependência de chamadas de modelo.
- Não é correto prometer IA grátis ilimitada; cotas, limites, disponibilidade e preços dependem do provedor.
- Trocar para desktop não elimina limite remoto. A alternativa robusta é o painel manual funcional.
- Voz depende de recursos do navegador/dispositivo e de permissões; não alegar suporte universal.
- Segredos não podem entrar no chat do Espelho, no catálogo ou em logs.

## Mudança concreta
Em branch isolada, o panel.html recebeu seletor compacto grátis/pago e botão manual que revela o painel existente. O Espelho ainda não é a tela inicial exclusiva; o código existente de autenticação e navegação precisa ser reconciliado antes de alterar essa sequência. Sem deploy, sem migração de banco e sem alteração do WhatsApp.

## Critérios de aceite para próximo ciclo
1. Abertura após login mostra Espelho em destaque, com acesso manual em um toque.
2. O Espelho encontra fluxos por catálogo versionado; sem chamar IA para tarefas determinísticas.
3. Um pedido sem ferramenta retorna alternativa útil, sem afirmar execução.
4. Esgotamento de cota real detectado por resposta do provedor, sem inventar status, e fallback sem perda de trabalho.
5. Testes mobile, acessibilidade, autenticação, estado de erro, continuidade e não vazamento de dados.
6. Rebase/reconciliação com alterações do Work antes de merge; revisão da PR #32.
