# JARVIS PULSE — Instalar, aprender o negócio e renovar a cada 30 dias

## Regra comercial autorizada em 10/10/2026
O comprador recebe acesso a um PULSE novo, com dados operacionais vazios. Ele informa a chave de licença e o código de autorização do dispositivo. Após entrar, o assistente faz perguntas simples sobre segmento, público, oferta, diferenciais e próximo passo comercial. As respostas preenchem o perfil empresarial para revisão e aprovação. Cadastros e documentos enviados à Caixa PULSE alimentam registros próprios da empresa, sempre com revisão de informações incertas. O banco é orientado ao atendimento, vendas, pós-venda, compromissos e acompanhamento.

Nenhum contato da Nova Vida ou outra empresa pode aparecer no novo ambiente. Uma nova licença no mesmo serviço **não** cria banco separado. Para entregar um PULSE realmente vazio, é necessário provisionar uma implantação e banco MongoDB exclusivos (via scripts/new_customer_plan.py). Isso ocorre nos bastidores: o comprador não precisa configurar o banco, mas a entrega comercial só acontece quando o ambiente isolado estiver pronto. O script gera um plano de implantação; não cria automaticamente um serviço Render nem muda segredos.

## Licenciamento
O proprietário usa 'Licenças comerciais' e a opção 'Iniciar com chave de 30 dias, contados da emissão'. O servidor aceita trial_days=30 sem data de expiração, gera chave secreta de ativação e define 30 dias desde a **emissão**. Não é renovação automática, nem período de teste gratuito presumido: são 30 dias de acesso contratados conforme os termos definidos pelo proprietário. O código de dispositivo continua de uso único com validade de 10 minutos. A chave comercial e o código são informados separadamente na instalação.

Ao vencer o prazo, o acesso ao CRM é bloqueado. O dispositivo autorizado pode chegar à sua página de renovação. Após Pix real confirmado diretamente pelo provedor, o servidor libera mais dias conforme a configuração da licença (30 dias como sugestão no painel), sem contagem duplicada em reenvios. O valor da renovação não é inventado: proprietário configura uma quantia explícita antes de disponibilizar QR Code.

## Recorrência: o que existe e o que falta
Hoje a integração usa **Mercado Pago Orders** para Pix manual de renovação. O cliente precisa efetuar um novo Pix por período. O sistema automatiza a verificação e a extensão, **não o débito da conta bancária**.

Para Pix Automático real, dependerá de um fluxo de autorização do pagador e produto/API com suporte confirmado pelo prestador. Não converter uma cobrança avulsa Orders em consentimento de débito automático, não cobrar sem autorização e não anunciar recurso como pronto. Mercado Pago oferece plataformas de assinaturas; disponibilidade de Pix Automático na conta/produto precisa ser avaliada separadamente.

Status atual de Pix real: ainda não comprovado. Conferir variáveis MP_COLLECTOR_ID, BILLING_PUBLIC_BASE_URL, conta recebedora, webhook, pagamento e liberação; não mostrar credenciais.

## Fluxo de primeira configuração
1. Comprador acessa o endereço do PULSE de sua empresa e autoriza o navegador com código individual e chave comercial;
2. Faz login com o dispositivo; sem perfil cadastrado, vê cinco perguntas simples sobre o negócio;
3. Responde em linguagem natural; o sistema preenche o perfil comercial estruturado e o mostra para conferência;
4. Confirma e envia o perfil para revisão do proprietário do ambiente; só fatos aprovados são usados nas respostas externas;
5. Alimenta a Caixa PULSE com texto, fotos, áudio ou documentos e prepara contatos e retornos;
6. Usa o WhatsApp/CRM somente após configuração da Meta e autorização de contato.

A primeira versão do questionário é **guiada por regras** e reaproveita o cadastro de perfil existente; não é conversa livre gerada por IA. Interpretação e organização via IA continuam disponíveis na Caixa PULSE. Conectar a IA ao próprio questionário é evolução futura.

## Como criar ambiente inicial para cliente
Em uma cópia do repositório execute:

python3 scripts/new_customer_plan.py --empresa 'Empresa Exemplo'

A saída informa um BUSINESS_ID exclusivo, um banco MONGODB_DATABASE exclusivo e os passos de implantação. Não define permissões MongoDB automaticamente. Não compartilhar SERVICE/CRM_ADMIN_TOKEN proprietário nem chaves Meta existentes. Cada empresa terá seu próprio número ou onboarding autorizado.

## Testes de aceitação antes de comercializar
- Uma nova empresa não vê dados de outras, nem após renovação.
- Uma licença de 30 dias expira corretamente e exige pagamento real; não renova por print, retorno falso ou webhook duplicado.
- Usuário novo sem perfil consegue concluir o cadastro guiado no celular.
- Acesso com chave inválida ou expirada falha sem acessar CRM.
- Renovação informa claramente se é Pix avulso ou Pix Automático autorizado.
- WhatsApp pertence à empresa certa e não envia mensagens sem autorização.
- Todos os estados 'concluído' são suportados por testes, não apenas deploy Live.
