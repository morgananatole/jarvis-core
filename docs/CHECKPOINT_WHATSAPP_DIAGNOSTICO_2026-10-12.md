# CHECKPOINT — diagnóstico WhatsApp no painel manual — 2026-10-12

## Entrega confirmada em código
- Botão "Diagnóstico WhatsApp" adicionado ao painel manual na branch docs/paf-01-alinhamento-fundacional-20261012.
- Clique usa a função api() já existente, que encaminha a /crm/whatsapp/connection e aplica autenticação de sessão ou assinatura do dispositivo.
- Resposta exibe apenas acesso de leitura da API e estado de coexistência. Não envia mensagem, não altera conta, não expõe número ou token.
- Teste estático correspondente adicionado em tests/test_readiness_contract.py.
- Verificação por leitura após commit: botão, chamada e função api() presentes.

## Limites
- Não houve execução de teste Python ou browser neste turno.
- Não houve teste real da Meta, do webhook ou de entrega.
- Nenhum merge ou deploy foi efetuado.

## Próxima ação
1. Executar suíte Python e testes reais de navegador, corrigindo falhas.
2. Verificar compatibilidade da branch com main e mudanças concorrentes do Work.
3. Conectar caixa de prontidão ao onboarding autenticado, sem armazenar segredos.
4. Após confirmação do workspace Render, verificar /ready e diagnóstico autenticado.
5. Realizar teste de mensagem apenas com destinatário autorizado e conferir recibo entregue e aplicativo Business.

## Perguntas adiadas
- Qual workspace Render é correto?
- Qual número de teste está autorizado a receber mensagens?

## Condição para declarar pronto
Meta API legível, webhook assinado recebido, resposta enviada e entregue, celular confirmado e pausa humana funcional.
