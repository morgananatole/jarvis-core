# Atendimento com prioridade gratuita

O modo `hybrid` usa Groq como principal e OpenAI apenas durante limite de cota
ou falha temporária. Não usa a API paga quando a configuração da gratuita está
errada (401/403/modelo inválido). Retorna à gratuita na primeira mensagem após
o `Retry-After`; não paga por sondagens em segundo plano.

O estado de espera e as reservas de chamadas pagas ficam no MongoDB, sobrevivem
a reinícios e são compartilhados. O limite diário é de chamadas tentadas, não
de mensagens entregues: falhas também contam, pois podem ter gerado cobrança.
Nenhuma chave é incluída no repositório ou nos diagnósticos.

Variáveis para ativar: `JARVIS_REPLY_MODE=hybrid`, `GROQ_API_KEY`,
`GROQ_MODEL=openai/gpt-oss-20b`, `OPENAI_API_KEY`,
`OPENAI_MODEL=gpt-4.1-mini`, `JARVIS_INSTRUCTIONS`.
Reserva paga só liga com `AI_PAID_FALLBACK_ENABLED=true` e
`AI_PAID_MAX_CALLS_PER_DAY` maior que zero. Padrão: zero chamadas pagas.
`AI_MAX_OUTPUT_TOKENS` padrão 300, máximo 500.

São enviados no máximo seis turnos recentes, com limite de texto. Histórico
usa identificador HMAC por telefone, expira em sete dias e é comum às duas IAs.
Não registrar mensagens ou números nos logs. Avaliar retenção antes de uso
com pacientes. Este módulo não substitui atendimento humano.

Quando as duas APIs estão indisponíveis ou o teto pago foi atingido, responde
com informação transparente sobre a indisponibilidade e encaminha ao humano.
Não confundir essa resposta com uma interpretação por IA.

# Disponibilidade sem contratar hospedagem

`.github/workflows/availability.yml` verifica `/ready` a cada dez minutos.
Usa runner padrão gratuito apenas enquanto o repositório for público e não
chama IA nem manda WhatsApp. Verifica também o banco e registra falhas no job.
O tráfego ajuda a evitar a suspensão por inatividade do Render.

Não é garantia de disponibilidade: o GitHub pode atrasar agendamentos e
desabilitar schedules após 60 dias sem atividade; o Render pode reiniciar ou
suspender por outros limites. As 750 horas são compartilhadas no workspace.
Mudança de visibilidade interrompe o monitor para evitar cobrança no privado.

Testes locais não consomem créditos. Ativar `hybrid` somente depois de conferir
as chaves no serviço e testar pergunta real, fallback e retorno.
