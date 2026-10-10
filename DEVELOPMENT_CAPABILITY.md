# Segundo Eu — desenvolvimento e manutenção de integrações

Decisão de Morgan em 09/10/2026: incorporar desenvolvimento e manutenção ao JARVIS, preservando identidade, autonomia útil e execução com verificação.

Esta capacidade concretiza a Capability Forge já prevista nas decisões canônicas de 08/09/2026; não cria outro JARVIS. A permissão Meta “Desenvolver app” permite configurar, testar e ver análises desse app. Não equivale a autonomia global, administração de outras contas ou autoalteração irrestrita.

## Implementação inicial

`development_preflight.py` é uma capability executável de diagnóstico somente leitura, sem dependências externas. Pode ser chamada pela futura camada de execução ou como CLI:

```bash
python development_preflight.py --ready-url https://jarvis-core-ou8d.onrender.com/ready
python -m unittest test_development_preflight.py
```

O diagnóstico distingue configuração pronta, transporte oficial verificado e atendimento inteligente comprovado. /ready sozinho prova apenas configuração e banco. As evidências de função, token, número oficial, webhook, entrada e entrega são fornecidas explicitamente ao contrato `IntegrationEvidence`; o CLI não inventa essas evidências.

## Contrato da Capability Forge

1. Recuperar decisões e observar o estado atual.
2. Identificar a lacuna e propor a menor alteração suficiente.
3. Vincular permissão a ator, recurso, escopo, duração e ação concreta.
4. Implementar em ambiente isolado; testar resultados e falhas significativas.
5. Promover somente após teste e autorização aplicável.
6. Verificar efeito real, registrar resultado sem segredos e preservar retomada.
7. Reverter quando seguro; não repetir envios incertos nem ampliar permissões por tentativa.

Credenciais pertencem ao serviço e ao usuário correto. Não entram em memória, prompts, repositório, relatórios ou diagnósticos. A autorização de Morgan para uma integração não se transfere automaticamente às instâncias comerciais do Pulse.

## Limites da versão inicial

Este módulo não gera código, concede permissões, cria tokens, envia mensagens ou se modifica. Ele implementa a etapa verificável de diagnóstico e o contrato de evidências. Adaptadores de desenvolvimento, testes, implantação, rollback e ledger durável precisam ser implementados e ligados ao Trust Kernel antes de se anunciar desenvolvimento autônomo completo.

## Evidência da integração atual

Em 09/10/2026, o acesso Desenvolver app foi aplicado ao usuário jarvisnovavida2026 no app 1585460142806819. Após atualização do painel, as permissões WhatsApp ficaram disponíveis e um token de 60 dias foi criado. O Render recebeu o token e o Phone Number ID oficial 1372243162639360 em modo test. A resposta ponta a ponta permanece dependente de verificação real; concessão de permissão e criação de token não comprovam entrega.

## Regra obrigatória para novos aplicativos e automações

O padrão de interação `docs/REGRA_INTUITIVIDADE_PULSE_1-3-0.md` integra a metodologia de desenvolvimento: uma ação principal clara, até três interações para uma tarefa comum e zero erros sem um caminho seguro. A cada mudança, testar cenários vazios, falhas de rede, ações repetidas, acessibilidade móvel, permissões e resultado verificado. Funcionalidade que não cumprir esse contrato deve permanecer marcada como pendente; não publicar apenas por passar no build. O objetivo é um produto útil, intuitivo e auditável, não uma demonstração de botões.
