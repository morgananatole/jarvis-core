# Prospecção e atendimento com zero gasto de transporte — 12/10/2026

## Objetivo, regra e alcance

Preparar gestão comercial de contatos e conversas preservando caixa central,
IA gratuita prioritária, opt-out e pausa humana. Não reimportar agenda já enviada.
Importação não é consentimento nem campanha. Número salvo pelo destinatário não
é requisito da Cloud API; opt-in e regras do canal continuam necessários.

Fontes oficiais consultadas nesta etapa:
- https://whatsappbusiness.com/policy/
- https://whatsappbusiness.com/products/platform-pricing/

A política publicada permite respostas livres dentro de 24 horas da mensagem do
usuário e exige modelos aprovados fora dessa janela. A página oficial de preços
consultada informa mensagens de serviço gratuitas nessa janela; marketing possui
precificação por mensagem entregue. O gate existente de retornos usa 23 horas
como margem conservadora. Uma reabertura de conversa por template não herda a
gratuidade de uma resposta de serviço.

Isso corrige a referência anterior baseada em tarifas secundárias/franquia de
1.000 serviços: não usar aquela estimativa como regra vigente. Confirmação na
conta e documentação técnica continua necessária antes de ativar capacidade paga.

## Implementação desta etapa

- `outreach_overview.contact_path` explica o caminho por contato sem IA extra:
  não contatar, atendimento humano, aguardar autorização, piloto, conferir IA,
  aguardar mensagem do cliente ou revisar resposta de serviço.
- Prospecção mostra o caminho no painel junto do interesse já demonstrado.
- `send_template` bloqueia por padrão qualquer template sem gratuidade
  comprovada, mesmo se variáveis antigas ativarem template e limite diário.
- `WHATSAPP_ZERO_COST_ONLY` tem padrão true; valor desconhecido também bloqueia.
  Alterar para false não faz parte desta entrega e não habilita templates sozinho.
  Não alterar em produção sem decisão específica de custo.
- O emissor de templates checa diretamente recusa, pausa e permissão antes de
  acessar orçamento/provedor; controles existentes de fila e autorização continuam.

O bloqueio é específico da rota de templates: não anunciar que ele audita todas
as categorias/custos, infraestrutura ou provedores. Respostas ao cliente e
roteador de IA não foram alterados. Não foi adicionada automação WhatsApp Web,
disfarce, rotação de números ou técnica para contornar bloqueios.

## Aquisição sem disparo API pago

Usar site, publicações orgânicas e canais em que já exista autorização para
convidar pessoas a iniciar conversa com a empresa. Conteúdo pronto:

“A Nova Vida está disponível para esclarecer dúvidas sobre acolhimento e
tratamento. Se quiser conversar conosco, abra nosso WhatsApp e envie sua pergunta.
Nós explicamos os próximos passos com respeito e clareza.”

Não distribuir esse convite automaticamente aos contatos importados sem opt-in.
Mensagem iniciada pelo interessado abre atendimento; não concede permissão
ilimitada para campanhas futuras. Ao receber, qualificar por fatos relatados,
responder à necessidade, encaminhar ao humano e combinar retorno autorizado.
Silêncio não é interesse. Grau de interesse não substitui autorização.

Não há quantidade diária que garanta ausência de bloqueio. Limites do canal,
qualidade, recusas e retornos incertos devem interromper envios conforme a política;
limite baixo serve à operação, não ao contorno de controles.

## Evidência e próxima ação

Base de desenvolvimento: main 8551525300f6840c5e39f1340c4ec03944cb9c3e.
Objetivo e restrições foram lidos em AGENTS/CENTRAL_NORMAS e documentos de
experiência; script read_before_work executado. Documento privado original não
foi atualizado: a interface de Drive disponível não expõe roteamento por link_id
exigido para o anexo mapeado; esta nota contém somente dados técnicos sanitizados.

Painel público abre; navegador desta sessão não está autorizado. Não foi possível
confirmar contagem final da importação, permissão por contato, entrega WhatsApp
ou efeito da interface privada. Nenhum arquivo foi reenviado, nenhuma campanha
foi ativada, nenhum contato real foi classificado nesta etapa e nenhuma mensagem
externa foi enviada. Não houve alteração Meta, cartão, credenciais ou ai_router.

Próxima ação operacional: acesso proprietário ao PULSE para conferir total/status
da importação e a visão de prospecção. Depois testar com contato próprio autorizado
uma resposta de serviço, entrega e pausa humana, antes de qualquer campanha.

Validação local: 26 testes focados passaram. A suíte completa inicialmente
encontrou uma asserção antiga de texto no teste de cadastro Meta, em arquivo não
alterado pela mudança de prospecção. O teste foi alinhado à mensagem atual mantendo
as exigências de verificação da API e de não anunciar conexão pronta. Não mudou
o cadastro Meta. O resultado final da suíte e CI será registrado na PR.
