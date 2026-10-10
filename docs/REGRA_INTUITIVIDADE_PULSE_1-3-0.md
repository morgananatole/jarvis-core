# REGRA PULSE 1·3·0 — padrão de intuitividade de interfaces e automações

**Escopo:** usar em todas as novas funcionalidades do JARVIS/PULSE, e como padrão de projeto para aplicativos e automações futuros que adotem este repositório ou este documento.

## O contrato 1·3·0
- **1** tarefa principal por tela: a pessoa entende em uma frase **o que consegue fazer** e **qual será o resultado**. A ação principal tem nome verbal (Atender, Organizar, Conferir), não jargão de API.
- **3** interações no máximo para concluir a tarefa comum depois do login: escolher área, selecionar dado e executar/confirmar; fluxos complexos têm etapas resumidas, sem menus em cascata nem configurações obrigatórias desnecessárias.
- **0** becos sem saída: qualquer tela vazia, erro, falta de permissão, falha de internet ou conclusão deve explicar o estado e a próxima ação **segura**. Sucesso requer evidência concreta, não apenas HTTP 200 ou fila criada.

## Regras executáveis
1. **Quatro rotas principais no máximo:** Atender, Organizar, Retornos, Conversas. Fotos, licenças, conexões e configuração ficam em 'Mais recursos', com rótulos claros. Uma tarefa urgente deve estar a um toque.
2. **Progresso visível e reversível:** ações que alteram estado mostram espera, sucesso, falha ou revisão, desabilitando repetição enquanto estão em andamento. Falha de rede após envio/Pix é **indeterminada**: verificar no servidor antes de repetir.
3. **Aprovação explícita antes de impacto externo:** importação, extração e cadastro não enviam mensagens; falar com cliente e cobrar exigem ação autorizada; mensagens aprovadas respeitam janela Meta, consentimento e atendimento humano.
4. **Dados entram uma vez:** formulário pode ter campos opcionais; IA sugere preenchimento, usuário revisa; o resultado vira cadastro, histórico e próximo passo, não se perde numa conversa efêmera.
5. **Nunca esconder a saída:** Sair, Fechar, Voltar, Corrigir, Pausar IA e Assumir atendimento continuam visíveis na situação aplicável.
6. **Acessibilidade:** alvos de toque >=44px nos comandos principais, rótulos legíveis em português, foco por teclado visível, feedback via aria-live/role=status, contraste e layout responsivo.
7. **Aprenda sem obrigar:** interface simples por padrão; usuário avançado encontra integrações/licenças dentro de mais recursos. Nada de seis menus técnicos no primeiro contato.
8. **Memória útil:** continuidade entre conversas só com fatos declarados e registrados; a memória pode estar errada e não é motivo para pressão de venda. Não chamar intimidade simulada de empatia.
9. **Provas de função:** cada recurso precisa de estado (proposta / no código / teste automatizado / teste real / produção), mais protocolo de falhas. Não chamar 'Live' de validação de pagamento real.
10. **Privacidade e segmentação:** todo cadastro, arquivo e memória são da empresa autorizada; nada de banco compartilhado entre clientes sem isolamento validado. Credenciais nunca em código, UI pública nem logs.

## Teste de intuitividade a cada modificação
- Usuário leigo consegue identificar a ação principal em 5 segundos?
- Consegue Atender/Organizar/Conferir retorno em até três interações?
- Sem conteúdo, existe estado vazio e opção de começar?
- Em erro 401/403/503 ou perda de rede, existe mensagem legível e caminho seguro?
- Botões críticos são repetíveis sem efeitos duplicados? Exigem chave de idempotência, revisão e consulta antes de reenviar?
- Com tela de 360px, todos os quatro destinos principais são alcançáveis por toque >=44px?
- Estão separados: recebido, organizado, enviado, entregue, pago e confirmado?
- Está claro quem está falando: IA ou humano?
- A preferência expressa pelo cliente foi respeitada? Não há memória fabricada?
- Instruções, transações e dados privados estão protegidos?

**Reprovação do teste:** se uma resposta for negativa ou não verificável, o recurso não deve ser anunciado como pronto. Não exige esconder a complexidade técnica; exige que o produto a administre por trás de uma interface simples.

## Simulação de falhas futuras
- **Internet cai ao enviar:** não repetir automaticamente um POST com efeito externo; orientar verificação do estado, preservar idempotência.
- **Meta demora ou entrega recibos fora de ordem:** distinguir aceito de entregue; não criar conversa duplicada nem cobrar duas vezes.
- **Lembrança desatualizada:** usar evidência e data; não supor que um problema foi resolvido após elogio.
- **Arquivo sem texto/OCR:** preservar original, pedir outra forma, não inventar dados.
- **Render suspende:** mostrar estado temporariamente indisponível e fornecer tentativa segura; considerar hospedagem contínua.
- **Assinatura venceu:** permitir pagamento somente com licença/dispositivo válido e confirmado por provedor; não abrir dados privados por conveniência.

## Fonte de verdade
O painel implementa o primeiro conjunto de princípios. Os testes em `test_pulse_ux.py` inspecionam as rotas, feedback e parse JavaScript quando Node está disponível. Testes automatizados não substituem validação em navegador real, com touch, leitor de tela e serviço de pagamento.
