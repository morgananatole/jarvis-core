# PULSE no celular, notebook e outra empresa

Direção de produto confirmada em 11/10/2026: executar gestão, comunicação e
produção com instalação simples, preservando controle humano e dados separados.
Rever o caminho de instalação/conexão, sem reconstruir o núcleo existente.

## Experiência que estamos preparando

O comprador recebe o endereço do PULSE exclusivo da empresa e os dados de
autorização por canal privado. Abre no aparelho, instala quando o navegador
oferecer essa opção, informa seu código e entra. Conversa com o JARVIS para
configurar a empresa, revisa os dados críticos e começa a organizar o trabalho.
As credenciais administrativas e configuração de provedores ficam com a equipe
responsável pela implantação. Não colocar códigos, chaves ou tokens no link.

| Uso | O que é necessário |
| --- | --- |
| Celular e notebook da mesma empresa | Mesmo endereço e banco; autorização individual por navegador/aparelho; licença com vagas suficientes |
| Segundo navegador do mesmo aparelho | Pode ter armazenamento separado; novo acesso individual, sujeito ao limite da licença |
| Outra empresa compradora | Implantação, banco, permissões, BUSINESS_ID e credenciais exclusivos; testar isolamento antes de emitir acesso |
| WhatsApp na aba Comunicação | Canal API da própria empresa preparado e testado; atendentes acessam pelo PULSE |
| Mesmo número também no WhatsApp Business nativo | Coexistência oficial e sincronização homologadas; instalar PULSE não concede isso |

O código já oferece aplicativo web responsivo com manifest, ícones e service
worker. O núcleo fica no servidor, portanto o notebook não precisa instalar
Python/MongoDB. Precisa de internet e navegador com HTTPS, WebCrypto e IndexedDB
para acesso por dispositivo. Sem instalação oferecida pelo navegador, pode
continuar na aba. Não prometer funcionamento offline nem compatibilidade física
de um aparelho que não passou por teste.

## Preparação feita no código local

- Instalação visível e orientação para notebook, Android, iPhone/iPad e janela
  já instalada, inclusive sem evento `beforeinstallprompt`.
- Endereço copiável para outro aparelho, sem segredos.
- Autorizar e entrar em uma ação; não substituir chave de aparelho já autorizado.
- Conferir capacidades e gravar a chave local antes de consumir o código.
- Recuperação explícita se instalação, armazenamento ou autorização falhar.
- Diagnóstico conjunto de conexão e última entrega, sem enviar mensagem ou
  alterar Meta; API acessível não é prova de coexistência.
- Espaço inferior para a caixa flutuante e rolagem explícita no diálogo.

Código local não é versão publicada. As correções da revisão de ecos continuam
incluídas e a feature permanece desligada. PR22 Pix/trial continua separada.

Validação desta entrega: **213 testes passaram, sem skips**, incluindo quatro
casos Mongo reais de ecos, recuperação de autorização no JavaScript, manifest,
ícones e service worker. Falhas de armazenamento antes do envio não consomem o
código; acesso existente não é sobrescrito; autorização válida abre o login.
O teste de navegação da caixa conversacional e a sintaxe JavaScript passaram.
O ambiente de testes teve dependências restauradas conforme requirements.txt;
não houve alteração desse arquivo. Não foi feito teste visual em notebook ou
Android físico, publicação, chamada real de IA ou envio de mensagem. Os testes
do navegador usam execução JavaScript em Node com serviços simulados.

## Preparar a venda nos bastidores

1. Provisionar serviço e banco exclusivos do comprador. O script existente
   `scripts/new_customer_plan.py` gera um plano, não cria a infraestrutura.
2. Configurar número e credenciais próprios da empresa, usando fluxo oficial
   aplicável. O exemplo oficial da Meta demonstra onboarding incorporado e
   gerenciamento de contas: https://github.com/fbsamples/business-messaging-sample-tech-provider-app
3. Validar entrada, resposta e recibo real; controle humano; isolamento; acesso
   no aparelho; conexão de provedores. Confirmar separadamente coexistência.
4. Emitir licença e códigos individuais no ambiente correto. Celular + notebook
   exigem ao menos duas vagas quando são autorizações distintas.
5. Entregar endereço e acessos privadamente. Não enviar credencial do proprietário.
6. Homologar Pix e a chave de uma hora da PR22 antes de oferecer teste pago ou
   anunciar liberação automática. A hora começa conforme validação explícita do
   funcionamento, preservando o requisito já decidido; este patch não altera a PR22.

## O que impede concluir tudo nesta etapa

Nova Vida está registrada na API; o registro privado informa app nativo não
conectado e fluxo incorporado sem opção comprovada de coexistência preservadora.
Revisão de permissões e acesso técnico Meta também têm pendências documentadas.
O caminho de número já API-only para app+API precisa ser comprovado, sem
desregistrar nem trocar o número ao acaso. Não é impedimento do notebook.

Também faltam homologação real Mercado Pago em ambiente autorizado, confirmação
de cobrança/licença, uso no Android/notebook físico e prova de sincronização
real. Não contratar provedor, cadastrar cartão ou criar ambientes pagos por
iniciativa técnica. Não afirmar que uma licença cria isolamento multiempresa.

Próxima sequência: validar patch e guardar evidências; submeter versão separada
à revisão/CI; completar dependências Meta e Pix; publicar apenas conforme escopo
autorizado. O limite anterior de não fazer deploy/ativar ecos segue preservado.
