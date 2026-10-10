# Decisão: pré-habilidades e camada periférica do Jarvis

Morgan, 10/10/2026 às 13:01:45 em Recife, autorizou registrar integrações, códigos, acessos e locais como pré-habilidades e criar uma segunda camada que analise melhorias em paralelo, começando pela visualização e evolução gradual do app. Às 13:03:03 esclareceu que o app precisa de uma tela de perguntas intuitivas com ajuda de IA para alimentar a base.

## Implementação inicial

A Caixa PULSE oferece cadastro guiado: objetivo, pessoa/serviço, informações conhecidas, próximo passo e telefone/data opcionais. As respostas viram entrada privada para a IA existente; ela organiza itens com evidência literal e até três perguntas para preencher lacunas. O operador confere antes de aplicar ao banco. Arquivo original e origem permanecem preservados; cadastro não gera consentimento nem envia mensagem automaticamente. Não há atualização automática da base clínica institucional a partir de documentos de clientes.

`peripheral.py` mantém um registro de decisão e catálogo de pré-habilidades: WhatsApp, entrada multimodal, retornos, licenças, evidência externa e pagamento futuro. Registra caminhos de API, nomes de variáveis e existência de configuração, nunca os valores das chaves. Os estados declaram o que existe e quais testes ainda faltam; configuração presente não significa integração funcionando.

A cada entrada `/crm/intake`, `asyncio.gather` inicia a organização e a análise periférica simultaneamente. A análise periférica tem prazo de dois segundos, é independente da IA principal e falhas não bloqueiam o cadastro. Usa somente tipo de mídia e objetivo; não copia textos, fotos, telefones ou dados de pacientes para o log de melhorias. Registro idempotente da simulação usa versão, empresa e hash da chave da entrada. Eventos: `observation_received` e `simulation_created`.

Esta primeira camada é um planejador por regras, não um segundo agente de IA permanente. Sugere capacidades a conferir, motivos e passos simulados; todos ficam `proposed`, `executed: false`. Não executa integrações, código, cobranças ou mensagens. Não funciona indefinidamente fora do servidor: cada observação roda durante uma operação do app. Hospedagem gratuita pode suspender o processo.

## Revisão no app

Proprietário → **Dispositivos** → **Periférico do Jarvis · simulação**. É possível simular organização, venda, retorno ou acessos e ver as últimas propostas. Clientes com licença não administram esta área.

- GET `/crm/peripheral`: decisão, catálogo e últimas 30 simulações, filtradas por empresa.
- POST `/crm/peripheral/simulate`: `{ "media": "text|image|audio|pdf|other", "goal": "organize|sell|followup|access" }`.
- Ambas exigem bearer do proprietário. Campos livres e instruções de execução são recusados.

## Evolução gradual registrada

1. Ver e testar app guiado com um dado ou arquivo real.
2. Validar cadastros, consentimento e retornos ponta a ponta.
3. Transformar observações aprovadas em melhorias pequenas, testadas e publicadas.
4. Só então conectar um planejador de IA adicional ou gateway, com custo e escopo definidos.

Não guardar credenciais no catálogo de pré-habilidades, não assumir que cópia de fonte pública pode ser impedida e não vender isolamento de empresas antes de implantar bancos separados.
