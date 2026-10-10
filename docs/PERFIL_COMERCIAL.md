# Seu negócio, seu jeito

Pedido de Morgan em 10/10/2026, 13:07:34 Recife: proprietário ou usuário alimenta o app, adapta ao segmento e destaca diferenciais; a IA deve conduzir uma venda concreta sem falar mais que o necessário. Autorização explícita para implementar.

Na Caixa PULSE, abra **Seu negócio, seu jeito**. Informe segmento, público, oferta, até quatro diferenciais reais e próximo passo. Proprietário e dispositivo autorizado podem enviar uma proposta. O proprietário revisa os fatos e aprova o que pode ser apresentado ao cliente. Propostas pendentes não entram nas respostas da IA.

- GET `/crm/business-profile`: perfil ativo e até 20 propostas pendentes da implantação.
- POST `/crm/business-profile/proposals`: `segment`, `audience`, `offer`, `differentials` (lista até 4), `next_step`.
- POST `/crm/business-profile/proposals/{id}/approve`: exige bearer do proprietário além do acesso normal. Dispositivo de cliente recebe 401 mesmo estando autorizado para operar o app.

Perfil aprovado é disponibilizado como dados de contexto nos caminhos híbrido Groq/OpenAI e OpenAI direto. Não é treinamento de modelo, não substitui conhecimento clínico institucional e não é instrução de sistema. Não coloque segredos ou informações pessoais de pacientes nesses campos: são fatos comerciais destinados a respostas a clientes. Informações sobre um cliente individual pertencem ao cadastro e histórico desse contato.

Política comercial `commercial-2026-10-10-v2`: normalmente 2–3 frases e até 60 palavras; uma pergunta por vez, diferencial pertinente à necessidade e próximo passo simples. Dúvida complexa ou segurança pode exigir mais explicação. Sem preço, desconto, vaga, garantia ou ação inventados. Estas regras orientam o modelo; tamanho e eficácia comercial ainda precisam ser avaliados em conversa real.

A implantação atual continua Nova Vida, com base institucional própria. Personalização de outra empresa exige implantação isolada e revisão de sua identidade e base de conhecimento; mudar o campo segmento não migra o sistema nem cria isolamento multitenant.
