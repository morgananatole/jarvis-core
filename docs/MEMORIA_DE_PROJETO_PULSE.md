# Continuidade do projeto — memória no PULSE

Esta funcionalidade fica no painel PULSE, depois de entrar **como proprietário**:
**Mais recursos → Memória do projeto**.

## O que faz (implementado nesta branch)

- **Rascunho recuperável:** cada alteração de texto é armazenada imediatamente neste navegador e, após uma pausa de aproximadamente 1,5 segundo, é sincronizada no MongoDB. A aba pode fechar antes da sincronização; a próxima abertura do mesmo navegador tenta recuperar o rascunho local.
- **Evita substituir texto recente:** o salvamento exige a revisão atual do servidor. Se outro aparelho gravou uma versão mais recente, o servidor responde 409 e não sobrescreve. A interface oferece **Juntar versões sem apagar**.
- **Versões anteriores:** mantém até 12 instantâneos de rascunhos, com data e revisão, sem colocá-los no GitHub.
- **Registros classificados e imutáveis:** ao clicar em Registrar no histórico, classificar como **Ideia, Diretriz, Sugestão técnica, Fato verificado ou Revisão de diretriz**. O tipo padrão é Ideia. Diretriz exige confirmação; revisão exige apontar a diretriz anterior. As entradas antigas não são editadas/apagadas ao registrar uma revisão.
- **Retomada:** botão para copiar o texto atual para outro chat.
- **Autorização:** APIs GET/POST /crm/continuity e /crm/continuity/entries exigem a credencial secreta do proprietário; dispositivos licenciados comuns não podem acessar a estratégia.
- **Idempotência dos registros:** uma repetição da mesma chave não cria uma segunda anotação.

## Limites reais

- Não capta automaticamente o que é dito ou digitado dentro de **outra conversa** no ChatGPT ou no Work. O autosave começa a funcionar para texto digitado **dentro do editor PULSE**. Captura do Work exigiria integração autorizada pela plataforma; não inventar uma.
- A cópia imediata local fica no armazenamento deste navegador; não use dispositivo compartilhado para informações sensíveis.
- MongoDB/Render precisam estar acessíveis para a cópia de servidor. Antes disso há apenas rascunho do aparelho. Um serviço gratuito pode estar suspenso; o navegador pode impedir armazenamento, então a interface informa quando não tem confirmação.
- Não colocar senhas, dados bancários, documentos médicos, cadastros de clientes ou informações sigilosas no diário; é estratégico, não uma pasta de documentos sensíveis.
- Quando o texto for uma decisão **dita no chat**, o agente deve continuar salvando a diretriz na memória privada do Drive, de acordo com o AGENTS.md, além de seu trabalho técnico.

## Não alterado

Rotas de IA gratuita/paga, webhooks WhatsApp, cadastro do número 7699, faturamento Pix/Meta, contratos de licença e segurança de dispositivos.

## Verificação

`python -m unittest test_project_continuity test_pulse_ux -v`

Após integrar, verificar no celular: entrar como proprietário, criar ideia, aguardar confirmação do servidor, fechar e abrir aba, verificar restauração; abrir em dois aparelhos e confirmar que não ocorre sobrescrita silenciosa; registrar uma diretriz e depois revisão com referência. Dados de teste, nunca credenciais reais.
