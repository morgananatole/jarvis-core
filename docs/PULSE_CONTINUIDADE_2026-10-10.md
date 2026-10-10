# JARVIS PULSE — direção e retomada de 10/10/2026

Prioridade autorizada por Morgan: WhatsApp oficial e app comercial. A conversa real
respondeu corretamente com a base da Nova Vida, segundo confirmação do proprietário.
Não reiniciar a integração como se ela estivesse sem resposta.

## Intenção que governa o trabalho

A empresa alimenta a Caixa PULSE com foto, áudio, texto e documento; a IA organiza
pessoas, contatos, serviços, valores e datas, cria próximos passos e mantém o
relacionamento comercial e pós-serviço. Anexos são fontes do banco da empresa.
Interface para leigos: instale e use, uma entrada visível, botões explicativos
somente quando necessários, resultado e próxima ação claros.

O produto deve demonstrar valor em 30 segundos de conversa: uma informação vira
cadastro, contexto e próximos contatos. Isso é meta de experiência, não garantia
de venda ou de configuração de uma empresa em 30 segundos.

A IA comercial acolhe, responde dúvidas e objeções, apresenta os diferenciais reais
e conduz para um próximo passo. Pode consultar referências públicas primárias para
esclarecer dúvidas gerais; não deve usar dados externos como prova de resultado
da Nova Vida, fabricar estatísticas ou decidir indicação clínica individual.

Urgências e exceções ficam com Morgan. Não misturar dados pessoais do Segundo Eu
com material empresarial nem dados privados dos contatos com conhecimento público.

## Leitura e auditoria

Foram relidos o projeto PULSE (incluindo a raiz de experiência), o blueprint e a
auditoria integral de hoje. A auditoria registra análise de código, testes,
implantação, Meta e evidência real da conversa. Os rascunhos locais anteriores
não estão neste checkout nem nas branches remotas; a implementação desta entrega
foi reconstruída usando os critérios e problemas documentados.

## Implementação desta etapa

- Regra comercial versionada em `sales_policy.py`, integrada aos modos híbrido e OpenAI.
- Consulta opcional a duas fontes primárias fixas (OMS/NIDA), com limites,
  cache e título/link/data; sem enviar conversa ou identidade à fonte pública.
- `/crm/intake`: texto, JPEG/PNG/WebP, áudio, PDF digital, TXT/CSV; 5 MiB por arquivo.
  PDF escaneado é identificado e exige OCR/reenvio em imagem; XLSX ainda não suportado.
- Original preservado em documento privado MongoDB; extração/transcrição e resumo
  separados da base institucional. Conteúdo não vira instrução do sistema.
- Prévia com evidências; nomes, telefones e datas inventados são rejeitados.
  Datas relativas/ambíguas exigem confirmação do operador.
- Aplicação idempotente com registros por item; falha parcial permite retomada.
  Isso não equivale a transação multi-coleção atômica.
- Múltiplos eventos de um documento geram tarefas distintas, sem sobrescrever
  os dois retornos de um mesmo contato. Nenhuma mensagem sai pela importação.
- Leases recuperam trabalho anterior ao envio; aceitação incerta vai à revisão.
- Busca de tarefas vencidas ordenada, prontidão exige CRM, `sair` cobre opt-out.
- Caixa PULSE no painel, demonstração fictícia de 30 segundos, manifesto,
  ícones e instalação PWA online. Nenhum cache de respostas privadas.
- CI funcional adicionada; fixtures antigos de webhook corrigidos.

## Limites que ainda precisam de aceite real

- Extração por visão/áudio e envio futuro precisam de teste real autorizado,
  além dos testes automatizados com provedores simulados.
- Este serviço permanece uma implantação por banco/empresa. `BUSINESS_ID`
  organiza os novos documentos; não torna o CRM legado um SaaS multiempresa.
- Datas e consentimento não podem ser inferidos da importação. Retornos criados
  ficam planejados até ativação; o executor exige permissão, janela/template,
  ausência de pausa humana e escopo do número de teste quando configurado.
- O plano gratuito pode dormir. O verificador de disponibilidade já existente
  não oferece SLA nem precisão de cronograma. Infraestrutura contínua segue pendente.
- WhatsApp Business no celular ainda ausente, informado por Morgan. Coexistência
  precisa de verificação no onboarding Meta; não remover registro da API para testar.
- O resumo não afirma que o produto completo, a segunda empresa, uma licença
  comercial, áudio/foto reais ou um contato agendado já foram validados.

## Próxima verificação

Abrir `/painel`, autorizar o dispositivo, enviar um material empresarial de teste,
conferir a prévia e aplicar. Confirmar dois eventos para um contato próprio autorizado,
ativar os retornos e observar entrega real. Resolver execução contínua e coexistência;
depois expandir onboarding, políticas e isolamento comercial.
