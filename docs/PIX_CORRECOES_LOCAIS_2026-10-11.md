# Correções locais Pix — 11/10/2026

Base: 9847df20d766872ed757f5b431eaa859b79002f4. Sem publicação ou deploy nesta etapa.

- Orders exige `user_id` igual ao recebedor de `/users/me`, inclusive no retorno de criação assíncrona. Ausência/divergência bloqueia; homologar presença do campo no contrato real antes de publicar.
- `/billing/connection` distingue presença/configuração sintática (`configuration_complete`) de recebedor/ambiente compatíveis (`configured`). Expõe `environment_matches`, modo esperado e motivos sem segredos. Diagnóstico pode consultar conta mesmo com configuração incompleta.
- `BILLING_MP_SANDBOX_APRO` desligado por padrão. Ativação explícita somente em ambiente isolado, conta de teste confirmada, modo literalmente false e fixture oficial 50.00 / test_user_br@testuser.com. Produção recusa antes do POST. Clientes não podem enviar first_name ao checkout.
- `.env.example` documenta nomes; nenhum valor real foi alterado. CPF continua requisito legado do checkout e hash de repetição; não é enviado pelo adaptador Orders. Corrigido comentário, sem mudar contrato comercial.

Testes locais: seguir o resultado do checkpoint. Banco em memória e API simulada não homologam Mercado Pago, MongoDB concorrente ou recebimento bancário.

Sem mudanças em WhatsApp, roteador IA, licenças, assinatura de dispositivos ou acesso interno. Sem credenciais, pagamentos, contas externas ou contratação.

Próxima etapa: aplicar em branch sobre base conferida, CI, homologação isolada, duas Orders e duas extensões únicas, replay/concorrência/expiração. Não ativar APRO na produção. Não publicar o patch antes da prova de contrato de homologação. Reversão: descartar branch local; depois de publicada, reverter commit e desligar APRO no ambiente de teste.

Fonte do fixture e user_id: https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/integration-test/pix
