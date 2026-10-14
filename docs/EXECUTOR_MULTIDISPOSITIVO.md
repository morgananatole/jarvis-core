# JARVIS — execução em dispositivos

Decisão atual: conectar o JARVIS a notebook/Linux, Windows, tela, Android e Google,
com ações executáveis e resultados, diminuindo a cópia manual de comandos.
O código reaproveita DeviceAccess; não muda a IA, Meta, cobrança ou agenda.

## Componentes implementados

- `execution_hub.py`: API integrada ao main, fila Mongo, claim atômico,
  chave de idempotência, validade, resultado com prova do claim e revogação.
- `connectors/agent.py`: executor por conexão HTTPS de saída, assinatura P-256,
  nonce por requisição e recibo SQLite antes do envio do resultado.
- `connectors/adapters.py`: comandos nomeados definidos localmente, diagnóstico/testes
  PULSE, captura/clique/texto/teclas na tela, estado/captura/toque/teclas Android,
  listagem Drive e leitura/acréscimo Docs via OAuth local.
- `connectors/mcp_bridge.py`: ferramentas reais para cliente MCP compatível.
  Não se conecta automaticamente ao ChatGPT nem adiciona ferramentas à conversa atual.
- Instaladores Linux e Windows, configuração inicial e login Google.

## Instalar e parear no notebook

Python 3.11+ e git necessários. Não executar com sudo. Usar checkout separado do PULSE:

```bash
git clone https://github.com/morgananatole/jarvis-core.git "$HOME/JARVIS_Executor"
cd "$HOME/JARVIS_Executor"
bash connectors/INSTALL_LINUX.sh https://jarvis-core-ou8d.onrender.com
```

Antes do merge, usar a branch `feature/device-execution-20261014` no clone.
O instalador não altera o banco nem a sessão PULSE. Se a configuração já existe,
é preservada e o comando termina sem sobrescrever.

No painel PULSE, entrar como proprietário e gerar código de dispositivo **sem licença
comercial**. A validade é dez minutos. Digitar o código no prompt local, nunca no chat:

```bash
.executor-venv/bin/python -m connectors.agent pair
.executor-venv/bin/python -m connectors.agent doctor
.executor-venv/bin/python -m connectors.agent run
```

O executor começa com `system.info`, `pulse.doctor`, `pulse.test`. Atualizações podem
ser comandos nomeados em config.json, com `argv`, `cwd` e `timeout`; o proprietário
habilita `command.run`. Nenhum comando livre recebido da rede vira shell.
Caminho absoluto do Node pode ser configurado se nvm não estiver no PATH do serviço.

No Windows: PowerShell, executar `connectors/INSTALL_WINDOWS.ps1 -Server URL`,
então `.executor-venv\Scripts\python.exe -m connectors.agent pair|doctor|run`.
O instalador restringe a pasta privada ao usuário atual; não exige administrador.
Executar dentro da sessão gráfica, não em serviço Windows Session 0.
A receita systemd de usuário é exemplo de persistência; ainda não instala autostart.

## Tela e Android

Adicionar capacidades desejadas à lista `enabled` na configuração privada e reiniciar
executor. PyAutoGUI requer sessão gráfica e suporte do sistema; Linux Wayland não
está validado e pode exigir uma sessão X11. Screenshot é captura do momento, não
vídeo contínuo. Mouse no canto interrompe PyAutoGUI pelo mecanismo failsafe.
Digitação inicial é ASCII; português com acentos ainda requer adaptador de texto.
Capturas ficam somente no resultado privado do servidor; não são publicadas.

Android utiliza ADB no notebook e aparelho autorizado por USB/depuração sem fio.
Instalar platform-tools, autorizar o computador no telefone, verificar `adb devices`
e configurar `android_serial` com o serial exato. Não há acesso Android sem esse
pareamento nem controle quando o aparelho/notebook estiver offline. iOS não implementado.

## Google

A conexão Google existente no ChatGPT não é transferida ao JARVIS. O executor utiliza
OAuth próprio no computador. Criar cliente OAuth desktop no projeto Google, habilitar
Drive/Docs e baixar JSON de cliente somente para pasta privada. Então:

```bash
.executor-venv/bin/python -m connectors.google_login --client-file /CAMINHO/cliente.json
```

Para acréscimo em documentos, executar com `--allow-docs-write` e conceder esse escopo.
Configurar `google_token` e habilitar capacidades Google. Leitura é o padrão.
OAuth pode exigir configuração da tela de consentimento/verificação do projeto;
não existe cliente Google universal embutido. Não copiar tokens entre empresas.

## Conectar inteligência

A API de tarefas aceita o bearer já usado pelo proprietário do CRM. O executor não
possui esse bearer: só sua chave por dispositivo. Um cliente MCP local pode iniciar
`python -m connectors.mcp_bridge` com JARVIS_SERVER e JARVIS_OWNER_TOKEN no ambiente
privado. As três ferramentas são jarvis_devices, jarvis_submit e jarvis_result.
Não pôr token em comando, print, git ou conversa. A inclusão em ChatGPT exige um
cliente/conector que suporte essa conexão; stdio não é uma URL pública de conector.
Não foi criado servidor MCP público nem autorizado um cliente nesta sessão.

## Verificação e recuperação

Registrar não comprova capacidade do hardware: é declaração do executor. Primeiro
consultar system.info, executar pulse.doctor e confirmar o resultado. Captura/clique,
Android, Google e Windows precisam testes nos dispositivos reais. Não executar todas
as capacidades só porque estão no catálogo.

Tarefa queued pode expirar; claimed nunca volta automaticamente à fila. Se resultado
se perder, recibo local reenvia somente o resultado. Se processo cair antes de persistir
resultado, observar estado incerto e conferir o alvo. Não repetir atualização/clique/
escrita às cegas. Revogar dispositivo no painel bloqueia novas tarefas/consultas;
a ação que já começou no aparelho pode terminar. Parar executor local interrompe
novas consultas. Retenção de tarefas/resultados: sete dias via TTL Mongo (não instantâneo).

Estado desta implementação e evidência de publicação estão no checkpoint associado.
