# AGENTS.md — protocolo de continuidade do JARVIS PULSE

Aplicável a toda sessão de engenharia trabalhando neste repositório. Esta regra **não** modifica o roteamento das IAs, a Meta, os webhooks, a cobrança nem configurações de produção.

## Primeira operação de uma sessão
1. Leia este arquivo e a documentação relevante em `docs/`.
2. Se houver acesso autorizado ao Google Drive do proprietário, localize e leia o documento **JARVIS PULSE — Continuidade de Desenvolvimento (10-10-2026)** (documento privado e cumulativo). Se não houver acesso, sinalize a limitação; **não presuma conhecer** ideias ou mensagens que não leu.
3. Leia o estado atual da branch, commits/PRs, CI, deploy e testes antes de alegar que algo já está em produção.

## Checkpoints no decorrer do trabalho
Não espere que o usuário peça "salve", nem que a tarefa termine.

- **Antes** de iniciar uma sequência extensa de operações, registre o objetivo atual, as restrições e a próxima ação no documento privado acessível.
- **Imediatamente** após nova decisão, ideia, requisito, mudança de escopo ou descoberta que altere a arquitetura, registre o conteúdo **e o motivo**. Não salve só o resultado técnico; preserve a lógica da decisão e as alternativas descartadas.
- **Antes e depois** de alterar credenciais, pagamentos, provedor, migrations, branch principal, PRs, deploys ou conexões de produção, registre evidências, plano de verificação, reversão e resultado. Execute essas ações somente quando autorizadas.
- Ao realizar muitas chamadas externas seguidas, estabeleça um ponto de retomada **antes** de continuar. Use como gatilho cada marco de decisão, alteração ou bloco pequeno de ações; não conte com o esgotamento da janela de contexto como aviso.
- Em cada checkpoint, distinguir `ideia`, `decisão`, `código local`, `branch/PR`, `merge`, `CI`, `deploy Live` e `teste ponta a ponta`. Incluir próximo passo concreto.
- Se Drive indisponível, anote apenas informações técnicas não confidenciais no changelog versionado adequado, declarando que o registro privado não foi atualizado. Nunca copie informações privadas para o GitHub público.

## Proteções
- **IA híbrida:** preservar a prioridade da gratuita e o fallback pago limitado, inclusive o retorno à gratuita após recuperação; **não alterar** `ai_router.py` nem políticas relacionadas sem pedido específico.
- **Custo:** nenhum cadastro de cartão, contratação ou cobrança por iniciativa do agente; capacidades pagas podem ter interfaces preparadas e permanecer desativadas.
- **WhatsApp:** não desregistrar o número atual, nem alterar a Cloud API, sem plano de restauração e autorização expressa.
- **Memória:** não guardar senhas, tokens, dados de cartão, identidades de pacientes, contatos empresariais ou conversas privadas neste repositório público.

## Limite objetivo
Este protocolo depende de um assistente/sessão que **leia e siga** este arquivo. Ele **não** cria captura a cada 15 segundos, não lê automaticamente outras conversas do ChatGPT Work e não continua executando depois que uma sessão encerra. Não anuncie uma solução de autosave universal como concluída sem capturador autorizado, armazenamento durável, teste de recuperação e integração real com a origem dos eventos.

## Regra de entrega
No fim de cada trabalho, reporte separadamente: feito e verificado, feito sem teste real, pendente/bloqueado, e exatamente como retomar. Prefira um registro parcial preservado a uma grande resposta perdida.
