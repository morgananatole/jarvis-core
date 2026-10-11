# Duas IAs, duas experiências

## IA da empresa

Área privada do PULSE, conversa livre por modelo gratuito já configurado. Mensagem enviada é salva antes da chamada externa. A IA pode organizar vários fatos por turno, responder dúvida, aceitar correção e sugerir uma pergunta útil. Sugestões são atalhos opcionais; não existe sequência obrigatória de perguntas.

O modelo retorna fatos com evidência literal da mensagem atual e sugestões de até dois destinos conhecidos. O servidor valida campos, limites, catálogo de até oito produtos e destinos. A interface cria os botões com esses rótulos; destinos não aparecem como URLs. Texto/HTML/código do modelo não é executado. Ao abrir a área, a mesma caixa segue flutuante.

`business_setup_drafts` guarda rascunho, conversa limitada aos últimos 40 turnos, revisão e estado. `business_profiles` e `business_profile_proposals` mantêm perfil aprovado e propostas. A conversa não recebe contatos, eventos clínicos ou inbox de clientes. Perfil inclui empresa, segmento, público, oferta, apresentação, diferenciais, palavras-chave, responsável, canal direto, horários e catálogo com descrição, preço e condições por item.

Falha de IA: a mensagem continua salva, nada novo entra no cadastro e o estado é explícito. Retentar revisita a mensagem; editar o resumo é alternativa. Revisões atômicas impedem sobrescrever mudança de outra sessão. O proprietário revisa e ativa uma cópia do cadastro; dispositivos podem propor, mas não aprovar. Rascunho não é contexto de atendimento.

Abertura automática da configuração exige autenticação e ausência de perfil aprovado. Retomada exige o mesmo ambiente empresarial autorizado. Uma implantação/banco e credenciais exclusivos por empresa continuam necessários: esse cadastro não transforma o CRM legado em SaaS isolado.

## IA do cliente

`customer_care.py` e política comercial compartilhada fornecem critérios e referências, não respostas fixas. Contexto da etapa e memória existente orientam o modelo híbrido e OpenAI. O modo híbrido mantém extração de fatos com evidência; OpenAI continua usando memória cadastrada sem extração própria de novos fatos. O resumo longitudinal completo permanece uma lacuna.

| Situação | Intenção e referência de tom |
| --- | --- |
| Primeiro atendimento | Apresentar instituição e IA brevemente, responder ao pedido já feito; se for apenas cumprimento, uma pergunta sobre a necessidade. “Sou o JARVIS, assistente virtual da Nova Vida. Posso acolher sua dúvida e explicar nosso tratamento enquanto a equipe humana não inicia o atendimento.” |
| Segunda interação | Continuar o assunto sem reapresentação. “Essa preocupação com a rotina faz sentido. Posso explicar como ela funciona; se preferir, também encaminho para a equipe.” Só usar a preocupação quando relatada. |
| Espera humana | Perguntar se já conseguiu atendimento e oferecer apoio se há pendência. Texto pode ser composto pela IA gratuita usando só nome/tratamento, com aviso fixo como fallback. Um aviso por episódio; urgência/exclusividade mantém aviso protegido. |
| Pós-atendimento | Reconhecer resultado confirmado e verificar necessidade restante. “Ficou algum ponto daquele atendimento que você gostaria de esclarecer?” Não supor satisfação ou contratação. |
| Fidelização e cortesia | Retomar assunto real sem reiniciar venda. “Como ficou aquela dúvida sobre a rotina?” Somente com assunto conhecido, permissão e retorno revisado; não criar disparos novos. |

Oferta humana é avaliada a cada duas interações quando útil, sem repetição se já recusou, pediu ou aguarda atendimento. Apoio emocional e informação não equivalem a psicoterapia, diagnóstico ou consulta profissional. Triagem pergunta um dado necessário por vez, usando o já conhecido.

Os 15 anos foram informados pelo responsável e entram na base institucional. A expressão “4.000 mil” desta conversa foi interpretada como intenção de quatro mil; quantidade de pacientes precisa ser conferida no cadastro antes de publicação. “Melhor equipe do Nordeste” não é apresentado como ranking objetivo sem fonte; destacamos a equipe multidisciplinar.

## Contatos separados

No WhatsApp, pedido de contato abre botões separados: Ligar, Abrir WhatsApp e Ver número. Botões de resposta escolhem o canal; o sistema envia somente o contato escolhido, para tocar/abrir/copiar conforme o aplicativo. Eles não são botões nativos de discagem. Na caixa da empresa, botões de ligação/WhatsApp embutem o destino e copiar usa a área de transferência com fallback legível.

Encaminhar ligação é uma alternativa quando mensagens não bastam, sem afirmar que alguém está ocupado ou que atenderá. Não apresentar canais antes de ouvir. Número vem do perfil aprovado; outro BUSINESS_ID não herda Morgan. Opt-out, urgência, pausa e deduplicação permanecem.

## Limites verificáveis

Voz é ditado opcional do navegador, com revisão antes de enviar; áudio ao vivo e leitura falada não foram implantados. Caixa acompanha somente a navegação interna. Retomada no banco foi testada com dados fictícios; mensagens reais, recibos Meta, comportamento do modelo ao vivo e percepção do cliente exigem validação de produção. Render Free pode dormir. Isolamento integral de dados de saúde, exclusão completa e memória longitudinal não foram resolvidos por esta etapa.
