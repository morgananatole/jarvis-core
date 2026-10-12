# Espelho JARVIS v2 — interação primariamente verbal e componentes sob demanda

## Correção da visão
O Espelho não é um menu de botões. É uma superfície conversacional que traduz intenções em execução, recorrendo primeiro a ferramentas conhecidas. A pessoa fala ou escreve; se a tarefa for resolvível com o contexto e permissões disponíveis, o JARVIS age e relata evidências. Quando faltar uma decisão ou informação, a superfície materializa um campo, botão, seletor, confirmação ou formulário; terminado o passo, o controle desaparece. Evitar controles permanentes, preservando saída, acessibilidade e intervenção humana.

## Presença visual
Brilho que oscila suavemente, sem vídeo ou imagens pesadas. Estados visuais distintos para aguardando, processando e aguardando entrada. Respeitar prefers-reduced-motion. Nunca confundir animação com evidência de processamento real.

## Biblioteca em vez de geração repetitiva
Catálogo JSON v2 em toolkit/catalog.v1.json, com componentes e fluxos declarativos. Componentes pré-definidos: campo de texto, campo de credencial segura, seletor, confirmação e voltar. Fluxos: configuração da empresa, busca de cliente, criação de projeto e demonstração de conexão. O planejador deve localizar, validar e compor esses itens antes de gerar código novo. Cache/presets locais minimizam custo de IA.

## Credenciais e efeitos externos
Campos de senha apenas em contexto seguro autenticado, sobre TLS, com cofre de segredos e política de não persistência em histórico, logs, prompt ou armazenamento do navegador. Nunca pedir credenciais na conversa de demonstração. Ações externas precisam de permissão, recibo e verificação. Não tentar contornar fluxos obrigatórios de consentimento de provedores.

## Entrega real nesta etapa
- toolkit/mirror-preview.html atualizado: os controles surgem e somem por etapa, com animação CSS oscilante, navegação acessível e instruções contextuais.
- toolkit/catalog.v1.json atualizado: metadados declarativos de fluxos, componentes e estados de homologação.
- Nenhuma chamada de rede, modelo de IA, voz, integração com PULSE ou alteração de dados. O protótipo interpreta somente algumas intenções por regras locais.

## Próximas etapas técnicas
1. Inspecionar o estado atual do main e as mudanças concorrentes do Work antes de tocar no painel.
2. Criar renderer com esquema estrito, ações autorizadas, validação de entradas e testes de segurança.
3. Conectar o Espelho à navegação e ao cadastro real do PULSE, sem remover as rotas críticas.
4. Integrar o planejador com ferramentas catalogadas e executor com recibos/idempotência; inicialmente dry-run.
5. Adaptar o mesmo componente para a entrada universal do JARVIS e novos produtos.
6. Homologar no celular e em produção, separando claramente código, testes e operação real.

## Princípio de evolução
JARVIS cria produtos; PULSE é uma instância. Cada nova capacidade deve ampliar a caixa de ferramentas compartilhada sem contaminar o núcleo com regras exclusivas de um cliente. Preservar os registros de decisões e seus porquês.
