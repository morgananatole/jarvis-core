# DECISÃO TÉCNICA — WHATSAPP DENTRO DO PULSE + AJUDANTES JARVIS
Data: 2026-10-12

## Não migrar o número neste momento
A migração destrutiva não é pré-requisito demonstrado. Primeiro validar elegibilidade e configuração da coexistência oficial Meta para manter o mesmo número no WhatsApp Business App e na Cloud API. Não excluir conta, desregistrar número ou mudar WABA sem prova de necessidade e procedimento seguro de retorno.

## Caixa de entrada dentro do aplicativo
Já existem rotas autenticadas em crm_admin.py:
- GET /crm/contacts — contatos sem telefone completo no índice.
- GET /crm/contacts/{number} — perfil e eventos recentes.
- GET /crm/human — fila humana.
- POST /crm/contacts/{number}/mode — pausa IA e modo humano.
- POST /crm/contacts/{number}/reply — resposta pelo operador via serviço existente.
Estas rotas são a base para interface de conversa estilo WhatsApp. É necessário confirmar o comportamento de envio, cobrança, autorização, ordenação e recibos antes de prometer paridade total com WhatsApp. Conteúdo e mídias devem respeitar acesso por empresa e retenção.

## Agentes auxiliares
Criados toolkit/shipyard.v1.json e shipyard_validate.py:
- três papéis (arquitetura, construção, verificação);
- tarefas com dependências, orçamento zero por padrão, limites e testes de aceitação;
- contratos sem credenciais, números de clientes ou conversas;
- alterações de Meta, cobrança, deploy e envio real requerem autorização.
**A fila é uma especificação e não executa IAs em paralelo por si só.** Requer executor, provedores de IA, isolamento de repositório, controle de conflitos e logs antes de rodar.

## Próximas entregas
1. Construir uma visão de conversas no painel usando rotas existentes, com tratamento de erros, confirmação explícita e acesso por empresa.
2. Executar testes offline do módulo de validação da fila e da caixa de entrada.
3. Implementar worker opcional de agentes com orçamento, fila persistente e permissões, inicialmente em modo simulado.
4. Validar conta Meta e coexistência oficial no workspace correto.
5. Somente depois testar mensagens autorizadas e liberar deploy.

## Critérios de conclusão
Mesmo número no celular, mensagens recebidas no PULSE, resposta do operador entregue, pausa da IA sem duplicação, custo dentro do teto e roteiro reproduzível de instalação.
