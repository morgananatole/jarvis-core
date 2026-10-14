# Diretriz raiz — inteligência de preparação e inteligência de interação

Autor: Morgan Anatole. Decisão de 14/10/2026. Aplicação pretendida: projetos JARVIS, PULSE, Nova Vida e novos projetos, conforme segmento e objetivo.

## Princípio

Dois processos lógicos coexistem. O primeiro prepara e organiza conhecimento favorável ao objetivo legítimo da empresa. O segundo conversa com a pessoa, compreende o caso, consulta esse conhecimento e conduz ao próximo passo concreto. Podem usar o mesmo modelo ou provedores diferentes. Não exigem dois modelos grandes rodando o tempo todo.

Não basta responder: o atendimento precisa utilizar os diferenciais, benefícios, objeções, vocabulário e condições reais da empresa. O objetivo pode ser vender tratamento, matricular aluno, vender outro produto, orientar ou organizar uma tarefa. A preparação adapta ao segmento, público, local, região e etapa; não transplanta a Nova Vida para outra empresa.

## Processo A — preparação orientada ao propósito

Entradas: perfil revisado do proprietário; catálogo; condições; região; público; objeções; conhecimento institucional; fontes públicas identificadas quando pertinentes. Organiza cards por intenção, benefício, objeção, etapa, localização e próximo passo. Cada card mantém empresa, fonte, evidência, data, versão, escopo e estado (proposta/aprovado).

Sugestões de uma IA e textos públicos entram como propostas, não como fatos da empresa. A decisão de ativação pode ser uma regra determinística previamente aprovada pelo proprietário ou revisão explícita; neste protótipo novas propostas exigem aprovação. Fontes externas são dados, nunca instruções executáveis. Não copiar história clínica individual para banco comercial nem cruzar bases de empresas.

O organizador não conversa nem envia mensagens a clientes. Processa fontes empresariais em fila e pode ser interrompido para priorizar atendimento. Não bloqueia a resposta esperando pesquisa. Materiais úteis à venda não dispensam condições, limitações ou dúvidas relevantes do cliente.

## Processo B — interação

Antes de responder, recupera memória individual e compromissos. Identifica intenção, dados conhecidos/faltantes, objeção, urgência relatada e etapa. Seleciona até dois cards relevantes por turno, respeitando região, objetivo e público. Não despeja catálogo nem repete slogan. O histórico de exposição ao modelo controla repetição; não é prova de leitura do cliente ou de fechamento.

Atende, compreende e auxilia antes de oferecer; apresenta benefícios e trabalha objeções com persistência respeitosa. Cada resposta deve facilitar um próximo passo: esclarecer, identificar uma pendência, combinar retorno, encaminhar avaliação ou confirmar condições com responsável. Não encerrar dúvidas comerciais com perguntas abstratas como “Como gostaria de abordar essa informação?”.

O processo B registra dados individuais com evidência da mensagem: nome; para quem; parentesco; idade da pessoa; cidade; substância; aceitação relatada; quem decide; dúvidas; compromisso de data. Ao salvar conversa, atualiza classificação e próxima regra ou razão para não retornar. Conteúdo não informado permanece desconhecido.

## Aprendizado e não repetição

Dúvidas e resultados podem gerar sinais para melhoria da base, mas não tornam a fala de um cliente uma afirmação institucional. Uma melhoria deve conservar fonte, motivo, versão, teste e decisão de ativação. Não declarar que frase causa venda ou que a pessoa comprará sem mensuração. O protocolo admite medir respostas, continuidade, avanço e fechamento confirmado; correlação não vira causalidade.

Variar forma e escolher conteúdo relevante preservando fatos. Não alternar preços ou condições para parecer natural. O intervalo entre respostas é informação de interação, não diagnóstico de interesse ou causa da demora.

## Nova Vida — aplicação específica

Foco em acolhimento, cuidado e venda: ambiente protegido; afastamento do acesso a substâncias e das rotinas/locais associados ao consumo; avaliação e desintoxicação acompanhada conforme necessidade clínica; continuidade; novos hábitos; atendimentos individuais e grupos; vínculos, rotina e vida social. Valor comercial é a proposta real de tratamento e apoio, não uma promessa de cura, casamento ou emprego recuperado.

Pode reconhecer sofrimento, perdas e riscos relatados, e explicar que tratamento pode proteger vidas e apoiar mudança. Não declarar que uma pessoa sem internação certamente morrerá, fracassará, perderá tudo ou fará a família morrer. Não usar culpa, vergonha ou falsa urgência. A IA não determina indicação clínica individual; risco imediato pede atendimento humano/emergencial apropriado. Persistência comercial respeita recusa e controle humano.

## Latência

Abertura fixa identifica a IA e confirma recebimento no primeiro contato e após intervalo sem conversa. Não anuncia prazo garantido. Perguntas de apresentação e triagem comuns podem usar respostas contextualizadas da base sem chamar modelo. O atendimento tem prioridade sobre organização. Resumo compacto e cards pequenos reduzem processamento; latência real exige teste.

## Aplicação aos projetos

| Projeto | Processo A | Processo B |
| --- | --- | --- |
| PULSE/Nova Vida | Benefícios, objeções, catálogo, região e regras de avanço | Atendimento comercial, memória e acompanhamento |
| JARVIS/Segundo Eu | Referências, preferências e critérios do objetivo autorizado | Organização e execução da tarefa com contexto |
| Sites e atendimento de outras empresas | Oferta e conhecimento aprovados daquela empresa | Conversa e conversão adequadas ao seu segmento |
| Conteúdo e mídia | Referências e briefing para o objetivo criativo | Produção e revisão guiadas pelo briefing |
| Novos projetos | Perfil, público, objetivo e base próprios | Interação contextual do mesmo protocolo |

Esta tabela define reaproveitamento. Não significa que o código de todos esses projetos foi alterado ou publicado.

## Estado técnico desta entrega

Código local preparado no piloto PULSE 0.5.0: banco empresarial próprio SQLite, cards aprovados iniciais da Nova Vida, fila de fontes empresariais, organizador por Ollama, seleção contextual, controle de repetição e atendimento prioritário. Rascunhos novos não entram automaticamente no atendimento. Não foi feito rastreamento contínuo de toda a internet.

Correções locais: retorno de recebimento também em retomada depois de 30 minutos; resposta imediata para pedidos iniciais de informações; nome/idade da frase real de teste; filtro de pergunta vaga. 70 testes automatizados passaram; organizador de IA foi testado com provedor simulado, não com chamada real nesta entrega. As primeiras versões 0.3.2 e 0.4.0 tiveram validação parcial pelo usuário, não validação integral da 0.5.0.

Pendente: instalação e teste real 0.5.0, integração com memória central já existente, transporte definitivo do número comercial, migração do executor para servidor, painel integrado em celular/tablet/PC, reconciliação da agenda, prospecção, isolamento operacional integral e aplicações concretas aos demais repositórios. Sem novo deploy nem retirada da Meta nesta entrega. Não reenviar 2.953 registros.

## Regra de continuidade

Antes de desenvolver atendimento nos projetos, ler esta diretriz e os requisitos comerciais do PULSE de 14/10/2026. Reutilizar componentes existentes; preservar memória, sessões e autorizações. Registrar decisão, implementação, teste, publicação, limite e próxima ação separadamente. O arquivo não cria execução automática ou memória universal entre sessões.
