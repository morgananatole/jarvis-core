# PULSE: vínculo verdadeiro com cada cliente — primeira entrega

## Objetivo
O PULSE não deve apenas responder. Deve criar e sustentar confiança com atendimento individualizado: reconhecer a pessoa, acompanhar problemas já relatados, retomar combinações verificadas, respeitar preferências de canal e entregar um próximo passo útil. O vínculo pertence à relação empresa-cliente; JARVIS é um assistente virtual transparente.

## Esta mudança (primeira etapa operacional)
- Captura **apenas** sinais explícitos nas mensagens do próprio cliente: dificuldade no atendimento, resolução declarada, satisfação declarada e preferência por ligação/mensagens.
- Guarda uma lista curta de evidências e a indicação de dificuldade ainda aberta no cadastro persistente. Cada registro aponta para o ID da mensagem original e horário. Não transforma elogio em "problema resolvido".
- Retoma contextos reais, sem afirmar sentimentos ou intimidade da máquina, sem supor culpa da empresa e sem fabricar lembranças.
- Em caso de dificuldade relatada, sugere um retorno para verificar a pendência e oferecer atendimento humano. O executor existente **não envia automaticamente** mensagens sem aprovação e requisitos de consentimento.
- Integra o contexto contextualizado aos modos de IA híbrido e OpenAI. O modo teste continua resposta fixa.
- Não altera Pix, contas recebedoras, chaves, licenças nem números WhatsApp.

## Verificação / limites
- Testes automatizados cobrem feedback explícito, elogios, problema não encerrado por gentileza, resolução, preferência, limite de histórico, duplicatas e integração ao cadastro.
- Isso não é ainda um "conselheiro emocional", análise confiável de tom, transcrição integral vitalícia ou prova de satisfação. A extração é conservadora por expressões reconhecidas e pode não captar outras formas de expressão.
- Os eventos de conversas continuam com retenção de 90 dias; a memória de sinais usa no máximo dez momentos, e o contexto da IA usa até cinco momentos dentro de 365 dias.
- Atualmente a aplicação é de uma empresa por implantação/banco. Antes de usar com empresas distintas, exigir isolamento completo por empresa.
- Retomar a interface do proprietário: permitir consultar, corrigir ou excluir anotações relacionais e registrar resultados efetivamente verificados. Não usar dados sensíveis como sinal de perfil social ou para persuadir alguém.
- Próximas etapas: sumarização longitudinal com revisão; histórico consultável sob demanda; eventos de acompanhamento pós-serviço confirmados, não enviados a esmo; medição de continuidade (problema resolvido, retorno atendido), sem escore opaco de manipulação.

## Diretriz de produto
"Vínculo não é repetir o nome: é lembrar, ouvir, cumprir e acompanhar. A pessoa deve sentir que foi reconhecida porque a empresa realmente usou o que ela relatou para ajudá-la."

## Segurança de implantação
Revisar testes CI antes de integrar ao ramo main e não presumir funcionamento real do WhatsApp, renovação Pix ou execução automática a partir de código publicado.
