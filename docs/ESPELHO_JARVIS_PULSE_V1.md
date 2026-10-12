# Espelho JARVIS — experiência universal de entrada

## Intenção
A pessoa encontra uma presença visual abstrata, luminosa e discreta, que serve como ponto de conversa e orientação. A inteligência conduz instalação, configuração e trabalho cotidiano, gerando ações contextuais no lugar de sobrecarregar a tela com botões fixos.

## O que foi construído
- Prévia HTML/CSS/JS em `toolkit/mirror-preview.html`: responsiva, animação leve, suporte a redução de movimento, botões gerados conforme o passo, explicações do que cada ação faz e fluxo guiado ilustrativo.
- Catálogo inicial de ações em `toolkit/catalog.v1.json`, sem tokens ou dados de clientes.
- Sem imagens, fontes externas, bibliotecas, IA remota, banco, requisições ou armazenamento persistente: custo de hospedagem praticamente restrito a arquivos estáticos.

## O que não está pronto
O espelho ainda não está ligado ao painel PULSE, ao login, ao instalador real ou a um modelo de IA. O interpretador de texto é local e limitado. O catálogo JSON é um contrato inicial, não um executor. Não alegar instalação automática nem inteligência em produção.

## Integração incremental segura
1. Preservar os destinos fixos acessíveis e as saídas críticas, mesmo com botões contextuais.
2. Conectar as ações contextuais às rotas existentes do painel, respeitando login e autorização.
3. Vincular a entrada à configuração real por empresa e aparelho, com progresso salvo e retomada.
4. Ligar catálogo validado ao planejador, com revisão antes de efeitos externos.
5. Testar navegação no Android e telas pequenas, estados vazios, contraste, foco, movimento reduzido e a regra 1·3·0.
6. Confirmar os commits/deploys concorrentes do Work antes de integrar ao main.

## Diretriz visual
Luxo tecnológico sem peso: fundo noturno profundo, brilho turquesa/azul suave, tipografia do sistema, animação CSS econômica, conteúdo legível e poucos elementos. A estética não substitui feedback real nem inventa que a IA esteja respondendo.
