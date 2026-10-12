# Incidente: latência e coexistência WhatsApp — 2026-10-12

Captura mostra resposta de fallback da IA no WhatsApp e relato de que o mesmo número não funciona no aplicativo Business do celular.

Render jarvis-core está live no main, commit 306fc6f. Logs históricos POST /webhook 200 não provam entrega completa.

main.py: quando generate_reply devolve UNAVAILABLE, sistema solicita humano e envia mensagem de indisponibilidade.

Hipótese de cold start ainda não comprovada; medir webhook, Mongo, IA, envio e entrega separadamente.

Criados instant_greeting.py e tests/test_instant_greeting.py na branch: saudação local Sobriedade, opcional, apenas primeiro contato, sem repetir e sem sobrepor atendimento humano.

Os arquivos ainda não estão integrados ao processamento, testados ou publicados. A saudação por API ainda pode incorrer tarifa Meta; validar custo antes de habilitar.

Próximas ações: medir falha IA, integrar com idempotência e consentimento, testar no número autorizado, diagnosticar coexistência oficial sem desregistrar, migrar ou excluir o número.

Indicador de digitação somente por mecanismo oficial, sem fingir atendimento humano ou impor atraso artificial.

Critério final: mesmo número utilizável no WhatsApp Business e PULSE, resposta entregue, pausa humana, custo controlado.
