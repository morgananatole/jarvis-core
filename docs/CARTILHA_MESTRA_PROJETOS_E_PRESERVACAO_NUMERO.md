# CARTILHA-MESTRA — JARVIS / PULSE / BOOST

Versão 1.0 — 2026-10-12

## Regras obrigatórias

O número comercial antigo é um ativo insubstituível. O mesmo número deve continuar funcionando no WhatsApp Business App do usuário e, quando houver elegibilidade oficial, no PULSE via Cloud API. Não desregistrar, migrar, excluir, transferir ou substituir o número como tentativa de correção. Se coexistência não for confirmada, preservar o aplicativo e ativar modo assistido/manual; não afirmar automação simultânea.

Não usar WhatsApp Web não oficial nem contornar tarifas, bloqueios ou políticas. Não prometer mensagens API ilimitadas sem custo. JARVIS pode economizar IA, mas não eliminar cobrança de transporte da Meta. Não registrar credenciais, telefones completos ou dados de clientes.

## Processo para TODO projeto novo

1. Abrir ficha antes de implementar: objetivo, orçamento, restrições, ativos, versão, dependências e rollback.

2. Inventariar estado atual e evidências; separar relato, hipótese e fato testado.

3. Projetar solução modular com caminho gratuito, custos externos e fallback.

4. Trabalhar em branch, uma hipótese por alteração, preservar backup e reversibilidade.

5. Registrar ação, entrada, saída, falha, correção e evidência sanitizada a cada passo.

6. Testar unidade, integração, navegador, celular, falhas e recuperação.

7. Transformar passos confirmados em instalador guiado com diagnóstico e ajuda contextual.

8. Publicar progressivamente após conciliar main e branch; medir custo, tempo, cliques e falhas.

9. Consolidar soluções comprovadas em receitas e falhas em antipadrões.

## Registro mínimo por passo

project_id; run_id; step_id; playbook_version; timestamp_utc; objetivo; prerequisitos; ambiente; commit; acao; resultado_esperado; resultado_observado; evidencia_sanitizada; status; erro_codigo; causa_ou_hipotese; correcao; duracao_segundos; custo_estimado; custo_observado; chamadas_ia; rollback; humano_necessario; proximo_passo.

Status permitidos: pending, running, verified, blocked, rolled_back. Nunca registrar token, senha, conteúdo de conversa ou dado pessoal desnecessário.

## Caminho especial de preservação do número

N0 — Confirmar número funcionando no WhatsApp Business App, sem alterar cadastro.

N1 — Consultar conta, WABA, número e permissões apenas por leitura.

N2 — Verificar elegibilidade do fluxo oficial de coexistência App + Cloud API.

N3 — Validar webhook e eventos sem migrar o número.

N4 — Comprovar que o mesmo número continua funcionando no aplicativo após ativação autorizada.

N5 — Testar recebimento no PULSE com contato consentido.

N6 — Testar envio, entrega, pausa humana e custo sem duplicações.

N7 — Documentar telas, caminhos, erros, correções e reversão.

Se N2, N4 ou N6 falhar: parar, preservar número no aplicativo e oferecer modo manual. Critério de aprovação: mesmo número ativo no app e no PULSE, sem perda de contatos e sem cobrança inesperada.

## Indicadores para otimização

Tempo de instalação; passos/cliques; intervenções humanas; falhas por versão; tempo de recuperação; custo Meta, IA e hospedagem; cache hit; armazenamento; instalações concluídas sem suporte; incidentes de número.

## Evolução da cartilha

Cada projeto usa toolkit/project-run-template.v1.json. Receitas só são classificadas como comprovadas com evidência. A cartilha deve ser acessível pelo instalador e atualizada após cada correção. Esta versão é documentação em branch, ainda não integrada ao motor de execução.
