# Atendimento humano sem abandono

Quando um contato solicita Morgan ou o operador assume a conversa, uma espera persistente começa. Após cinco minutos sem resposta humana, o worker envia um único acompanhamento: pergunta se o cliente já recebeu atendimento, antes de oferecer alternativas. Telefone e links ficam disponíveis quando solicitados ou necessários. O aviso não usa modelo de IA nem supõe que Morgan está em reunião ou disponível.

Depois do aviso aceito, mensagens novas podem receber apoio comercial da IA existente, com memória e instrução de que o atendimento humano continua pendente. A fila não é encerrada. Resposta humana ou nova tomada de controle desativa esse apoio; nova mensagem aguardando resposta humana abre outro período de espera. Recebimentos sucessivos não reiniciam o prazo. Pedidos urgentes ou de atendimento exclusivamente humano recebem somente o aviso fixo e os contatos, sem respostas comerciais automáticas.

O retorno comercial previamente planejado continua suspenso durante a espera humana. O acompanhamento da espera é uma resposta à conversa em aberto, não uma campanha de prospecção.

O worker confere janela ativa, opt-out e escopo de teste. Cada período tem um envio identificado de forma única no banco. Reinício/duplicata não repete o aviso. Envio incerto permanece para revisão, sem reenvio automático. Locks de contato preservam a ordem entre resposta humana e acompanhamento nesta implantação de instância única.

O primeiro aviso e o encaminhamento inicial não despejam contatos. Quando houver pedido ou necessidade de contato direto, os links informados pelo proprietário são tel:+5581989927699 e https://wa.me/5581989927699; número para copiar +55 81 98992-7699. O link WhatsApp abre a mesma conversa; não garante presença humana. O aplicativo do destinatário determina se o URI tel é clicável.

Limites: a verificação ocorre no worker a cada aproximadamente 60 segundos enquanto o servidor está executando; Render Free pode dormir, então cinco minutos não é garantia de prazo em produção. Mensagens/recibos reais precisam de homologação. O apoio comercial usa o roteamento de IA já existente, sem habilitar fallback pago nem alterar tokens, número Meta ou cobrança.

Teste: python -m unittest test_human_waiting test_human_service -q; suíte completa: python -m unittest discover -s . -q.

Reversão: reverter apenas o commit desta mudança. Os novos campos privados de espera podem permanecer sem uso; não apagar cadastro ou conversa.
