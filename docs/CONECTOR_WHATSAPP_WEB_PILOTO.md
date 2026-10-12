# PULSE — conector local WhatsApp Web, piloto 0.1

## Estado e alcance

Código experimental isolado, sem merge/deploy de produção e sem teste de
entrega real. Usa whatsapp-web.js (cliente não oficial), Node 22.13+ e um
processo Python do PULSE. Não modifica a Cloud API nem desregistra números.
Automação não oficial pode sofrer restrição e quebrar com mudanças do WhatsApp.
Não há garantia de ausência de bloqueios, custo total zero ou operação 24h.

O piloto recebe texto de até cinco destinatários explicitamente autorizados,
responde e registra memória no banco exclusivo. Não lê/importa a agenda,
não cria campanhas nem executa retornos agendados. Grupos, LID, mídia,
histórico antigo, fotos de saída e interface CRM não estão conectados.
Pausa humana, urgência e pedido de não contato bloqueiam a IA.

Reutiliza `main.generate_reply`, `ContactMemory` e `ReplyRouter` sem alterar
esses módulos. O processo local não inicia lifespan/worker do main. Modo
inicial `test` devolve resposta fixa, claramente identificada como teste,
sem chamada de IA. `hybrid` reutiliza provedor gratuito já autorizado e
instruções revisadas; fallback pago fica desativado neste processo.
Banco vazio não herda perfil comercial aprovado da produção: revisar/copiar
somente informações institucionais autorizadas antes de avaliar venda.

Os 10 testes offline passaram nesta entrega. A instalação npm não concluiu
no ambiente de desenvolvimento; não há lockfile nem teste de compatibilidade
do cliente real. Resolver dependências no notebook antes do pareamento.

## Instalação no notebook (Ubuntu)

Na raiz de um checkout desta branch, use ambiente separado, sem `.env` de
produção. Requer Node 22.13+ e Python compatível com requirements do projeto.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd connectors/whatsapp-web
npm install
```

Configurar privadamente estas variáveis no terminal local ou gerenciador de
segredos, nunca no chat/Git. Não copiar credenciais da Meta:

| Variável | Valor necessário |
|---|---|
| `PULSE_WEB_PILOT` | `true` |
| `PULSE_WEB_OWN_NUMBER` | Número de teste já instalado no WhatsApp, país+DDD |
| `PULSE_WEB_ALLOWED` | Até 5 telefones de teste autorizados, separados por vírgula |
| `PULSE_PILOT_MONGODB_URI` | Conexão privada com permissão somente no banco piloto |
| `PULSE_PILOT_DATABASE` | Nome começando com `pulse_web_pilot_` |
| `PULSE_PILOT_ID_SECRET` | Segredo novo de pelo menos 32 caracteres |
| `PULSE_PYTHON` | Caminho absoluto do `.venv/bin/python` da raiz |
| `PULSE_PILOT_REPLY_MODE` | `test` inicialmente; depois `hybrid` se autorizado |
| `GROQ_API_KEY`, `JARVIS_INSTRUCTIONS` | Só para teste com IA gratuita |

```bash
npm start
```

Parear o QR privado no notebook pelo WhatsApp do número de teste, em
Dispositivos conectados. O conector confere o número pareado e recusa outro.
Não parear o número comercial API-only nem migrá-lo para realizar este teste.
QR e pasta de sessão são credenciais: não compartilhar ou publicar.

Para primeiro contato individual com destinatário autorizado da lista:

```bash
node connector.cjs send TELEFONE_TESTE 'Sou o JARVIS. Esta é uma mensagem de teste autorizada.'
```

Esse comando faz um envio e encerra. Reinicie `npm start` para responder.
Execuções manuais novas são novas intenções: não repetir comando se o resultado
anterior for incerto. Não há envio em lote. `Ctrl+C` encerra sem apagar sessão.

## Verificação e recuperação

1. Pareamento: `piloto_conectado`; isso ainda não prova mensagem entregue.
2. Envio: `accepted` é aceitação do cliente Web, não entrega/leitura.
3. Destinatário confere recebimento e responde; verificar resposta fixa e memória.
4. Testar segunda mensagem, reinício/sessão, urgência e `parar`.
5. Só depois habilitar IA gratuita, com perfil empresarial revisado no banco piloto.

Diário SQLite privado guarda somente IDs hash e estado. Memória de conversas
fica no Mongo piloto. Duplicatas/reinício não reenviam trabalhos existentes.
Falha ou timeout marca revisão; não há reconexão/reenvio automático em loop.
Mensagem durante processamento recebe diagnóstico de piloto ocupado e não é
enfileirada: o piloto ainda não garante processamento de todas as mensagens.
Desconexão encerra; reiniciar manualmente com a mesma pasta, após revisão.
Sem alteração de fingerprint, anti-bloqueio ou remoção de proteções do browser.

Testes offline:

```bash
python3 -m unittest test_local_web_pilot -v
cd connectors/whatsapp-web
npm test
```

Reversão: parar processo local. Produção permanece no transporte oficial.
Para revogar sessão usar Dispositivos conectados do número piloto.
Falta para produto completo: teste real, recibos, fila durável de entradas,
interface de pausa/revisão e integração de tarefas/mídia por canal.

Fontes técnicas consultadas em 12/10/2026:
https://wwebjs.dev/guide/creating-your-bot/authentication.html
https://docs.wwebjs.dev/Client.html
https://github.com/wwebjs/whatsapp-web.js
