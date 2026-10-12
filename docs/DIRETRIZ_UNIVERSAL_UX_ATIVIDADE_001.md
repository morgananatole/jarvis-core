# Diretriz universal UX-ATIVIDADE-001 — interfaces vivas e feedback de processamento
Data: 2026-10-12

## Abrangência
Obrigatória para todos os produtos presentes e futuros JARVIS, PULSE, BOOST, instaladores, painéis, Espelho e assistentes de atendimento.

## Contrato
1. Ações assíncronas visíveis precisam apresentar feedback imediato e acessível, por exemplo: "Consultando informações…", "Preparando resposta…", "Conectando…", "Enviando…".
2. O feedback deve representar o estado real. Nunca declarar "digitando" quando não há resposta sendo preparada, nem simular presença humana.
3. Enquanto houver trabalho, oferecer animação sutil de atividade; respeitar prefers-reduced-motion, acessibilidade e dispositivos modestos.
4. Concluída a tarefa, trocar o indicador por resultado, erro compreensível ou alternativa segura. Não deixar atividade infinita sem timeout e recuperação.
5. Operações demoradas devem ter etapas de progresso verificáveis e opção de cancelamento quando tecnicamente possível.
6. Primeira resposta pode ser determinística e econômica, sem esperar geração por IA, desde que consentimento, contexto, custo de transporte e pausa humana sejam respeitados.
7. No WhatsApp Cloud API, o indicador oficial de digitação pode ser enviado com a confirmação de leitura quando houver mensagem recebida e resposta sendo preparada. A Meta encerra o indicador ao responder ou após cerca de 25 segundos. Não repetir artificialmente para criar ilusão de pessoa. Documentação: https://www.postman.com/meta/whatsapp-business-platform/request/lhf0duq/send-typing-indicator-and-read-receipt
8. Cada implementação deve registrar latência até feedback, duração real, taxa de timeout, resultado, correção e impacto em custo.

## Implementação inicial
Em panel.html foi incluído pulseActivity, com animação CSS de baixo custo e controle de requisições concorrentes no wrapper api(). O texto é "JARVIS está consultando os dados…" e desaparece no finally da última requisição. É progresso real de consultas CRM, não promessa de geração de IA. Não publicado ou validado em navegador ainda.

## Pendências
- Cobrir ações assíncronas fora do wrapper CRM e fluxos de geração de IA.
- Adicionar timeout e estados de recuperação onde faltarem.
- Integrar a saudação inicial determinística no backend com segurança de custos e idempotência.
- Medir e corrigir latência real do WhatsApp; habilitar indicador oficial apenas no fluxo elegível.
- Executar CI e validar em Android antes de merge/deploy.
