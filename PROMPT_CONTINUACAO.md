# Diário do projeto: automação de auditoria de influenciadores

> ## ⚠️ NÃO COMECE POR AQUI. Leia `COMECE_AQUI.md` primeiro.
>
> Este arquivo virou **diário cronológico** em 07/09/2026. A seção mais nova é
> de **12/09/2026** (a que começa logo abaixo, "O QUE ACONTECEU DE 09/09 A
> 12/09/2026"). Entre 02/09 e 08/09 existe trabalho real que está no código e
> nos testes, mas **sem registro de conversa**: eu (a sessão de 12/09) achei os
> arquivos já prontos na cópia de trabalho, sem ter estado presente quando
> foram decididos. Ver a nota "O QUE FICOU SEM DIÁRIO" dentro da seção nova,
> para não confundir "sem registro" com "não aconteceu".
>
> **O estado atual do programa está em `COMECE_AQUI.md`**, que é o arquivo de
> orientação: arquitetura, as telas, as regras da régua, o que é manual,
> as medições que valem como fato, as armadilhas e as pendências abertas.
>
> Use este diário quando precisar do **porquê de uma decisão passada**, e não
> para saber como as coisas estão. Onde os dois discordarem, vale o
> `COMECE_AQUI.md`.

---

## O QUE ACONTECEU DE 09/09 A 12/09/2026

Escrito em 12/09/2026, a pedido do auditor: "faça um prompt novo detalhando
cada passo dessa conversa que tivemos para que tudo tenha contexto e a gente
continue mexendo nesse projeto. Não esqueça de colocar nada." É o registro
completo de uma sessão longa, em ordem. Onde o detalhe técnico exaustivo já
está em outro arquivo (o Calendário tem `DESENHO_CALENDARIO.md` inteiro para
si), este diário resume e aponta para lá, mas nenhuma DECISÃO fica de fora.

### 1. O link de story sem número

O auditor relatou um problema real de uso: "nesses casos onde só existe 1
story, eu não consigo pegar o link, pois para pegar o link eu precisaria
passar de story para voltar e conseguir pegar o link com aquela numeração no
final, caso contrário, o link fica assim
`https://www.instagram.com/stories/felipekersch/`". Eu errei o diagnóstico
duas vezes seguidas (primeiro disse que o número não era necessário, depois
culpei o formato de link de Reel), e o auditor me corrigiu as duas vezes com
experiência real de uso, até eu me firmar no código (`_REGEX_POST` exige o @
no caminho, `fluxo_downloads.py` por volta da linha 4052). **Não houve
mudança de código aqui**: o link sem número realmente não tem como ser
processado sem o programa perguntar o número interno do perfil ao Instagram,
que é a chamada mais arriscada que existe. O auditor resolveu manualmente
("só consegui agora pq ele postou outro, eu voltei e consegui pegar o link
completo"), e o item ficou sem ação de código.

### 2. Abrir o programa, e o atalho para a analista

Pedido simples ("abra o programa"), resolvido subindo os dois processos.
Depois o auditor perguntou pelo atalho de Área de Trabalho para a analista de
Marketing que vai testar o programa. Criei:

- `abrir_programa.bat`, que sobe os dois processos (`trabalhador.py` e
  `painel.py`) com um clique só
- `ferramentas/criar_atalho_area_de_trabalho.ps1`, que cria o atalho na Área
  de Trabalho apontando para o `.bat`
- `testes/teste_atalho_de_abrir_o_programa.py`, provando que o atalho aponta
  para o caminho certo

Confirmado ao auditor: sim, ele pode usar o mesmo atalho, e sim, o arquivo
pode ser copiado para o notebook da analista (é só um atalho, não carrega
credencial nenhuma). Rodei o comando de criação e registrei o passo no
`INSTALAR.md`.

### 3. A justificativa do ciclo incompleto ficou mais suave

"nessa justificativa aqui to achando muito incisiva... pode colocar algo como
CICLO INCOMPLETO/ALTERADO". Troquei "Ciclo não apto a pagamento" por "Ciclo
incompleto ou alterado" em `escopo_e_entrega.py`, `APRESENTACAO[INCOMPLETO]`.

### 4. A pausa entre downloads, e dois diagnósticos errados antes do certo

O auditor comparou com a extensão de terceiros que o Marketing usa: "é muito
rápida para baixar dois downloads um atrás do outro". A descrição inicial
dele ("34 de uma vez só" ter corrido o risco de bloqueio em agosto) me levou a
um diagnóstico errado sobre o espaçamento entre links, que citei de volta
para ele sem checar — **errei duas vezes antes de entender o problema real**.
Só quando ele detalhou com precisão ("quando o usuário tem dois vídeos de
stories, eu coloco o link pra baixar e logo após eu coloco outro link, o que
eu estou dizendo que tá demorando é esse intervalo entre um video baixar
depois do primeiro") ficou claro: **um link colado no meio do trabalho pagava
a pausa longa entre rodadas** (180 a 420 segundos, pensada para conter rajada),
quando devia pagar só o intervalo curto entre links.

A correção, em `fluxo_downloads.py`:

- `PAUSA_INSTAGRAM_MIN_SEG`/`MAX_SEG` caiu de 30–180 para **20–45 segundos**
- a pausa longa (180–420s) só entra quando a rodada foi **barrada pelo
  limite** de 3 downloads por vez (`barrados_pelo_limite`), não em toda
  rodada

Testado e aceito pelo auditor ("ta bom esse valor por enquanto").

### 5. O Calendário Geral de Divulgações: a automação inteira

Esta foi a mudança de maior porte da sessão. **O detalhe técnico completo, com
todas as medições, está em `DESENHO_CALENDARIO.md`**, que tem versão própria
(chegou à v3) e foi atualizado em cada correção. Aqui vai o resumo em ordem,
com as decisões e as falas do auditor que as motivaram.

**O pedido original**, com as palavras dele: "quero ligar a automação à outra
planilha deles, que é o CALENDÁRIO GERAL DIVULGAÇÕES... a ideia é que elas
postam esse cronograma todo dia preenchendo manualmente cada linha com os
influencers e tal, porém o jogo, o status, horário e monitorado por, são
coisas que são preenchidas depois de baixar o vídeo". Ele foi claro sobre o
que sai da lista: "não precisa colocar o APAGADA não" (não existe esse status
na planilha real, 0 em 1.984 linhas medidas) e sobre o horário do post: "é
possível estimar? ou teria como ter um campo falando a quanto tempo aquela
postagem foi feita?" — resolvido descobrindo que a hora **já vinha do
Instagram** e estava sendo jogada fora por um `.date()` em três lugares
diferentes; bastou parar de descartar e converter de UTC para Brasília
(`fluxo_downloads.hora_de_brasilia`).

**O que foi construído** (`calendario_divulgacoes.py`, novo módulo):
normalizar handle e marca, achar a aba pelo mês do post, achar a linha certa
(a chave repete em ~3% dos casos, sempre quem posta dois stories no mesmo
dia; a regra é "a primeira linha ainda com Status vazio"), nunca sobrescrever
célula preenchida, nunca criar linha nova. Escrita sempre na cópia de teste
até existir `marketing_producao/calendario_id.txt`, autorizado só por quem
administra o Calendário do Marketing — **esse arquivo continua não existindo**,
e a automação continua escrevendo na cópia de teste.

**A pergunta sobre "há quanto tempo está no ar"** (para pegar quem apaga
story antes de 24h) foi levantada pelo auditor e **adiada por decisão dele**
("ok, sigo o recomendado"): reconferir custa uma chamada extra por
influenciador, e o teto diário (20 chamadas/conta) já está sendo usado por 18
influenciadores/dia medidos, 15 com story. Não cabe sem decidir antes se sobe
o teto ou se reconfere só um subconjunto. Fica registrado em
`DESENHO_CALENDARIO.md`, seção "O que vem depois".

**Populei a cópia de teste do Calendário** com dados fictícios (186 linhas
reais + 56 fictícias para 14 handles conhecidos) para dar o que testar, a
pedido do auditor.

**Achado 1, em 11/09: `Não Postada` virou motor de comparação**, e apareceram
divergências entre o Calendário e o que a auditoria tinha baixado (a mesma
data marcada `Publicada` na planilha deles, sem vídeo na auditoria, e
vice-versa). Decisão do auditor: mostrar a divergência em vez de copiar o
check deles — "a evidência da auditoria é o vídeo baixado e validado, não o
check que o Marketing pôs na planilha".

**Achado 2, ainda em 11/09: o janela do ciclo explodiu para anos.** A tela
mostrou a mensagem tentando ler abas `ABR.26` a `JUL.26` que a cópia de teste
nunca teve, com o erro técnico bruto da API repetido. Causa raiz medida: **o
número do ciclo se repete em períodos bem separados do mesmo influenciador**
na base real (`@lucasguimaraes` ciclo 6 tinha posts de maio/2024 a
agosto/2026, mesmo rótulo reaproveitado). Medido nos 1.032 ciclos reais:
12,6% passavam de 365 dias de largura sob o mesmo número. Corrigido em
`fluxo_downloads.janela_do_ciclo` com duas travas: ciclo com mais de 90 dias
de posts próprios vira `(None, None)` (não confia no rótulo), e a vizinhança
com o ciclo anterior/seguinte nunca estica mais que 45 dias além do medido,
mesmo que o vizinho também esteja contaminado. Efeito medido: a maior janela
caiu de 32 meses para 5, e 265 dos 1.032 ciclos (25,7%) agora dizem
honestamente "não dá para confiar" em vez de inventar uma janela de anos. De
brinde, `calendario_divulgacoes._aba_nao_existe` passou a reconhecer "aba não
existe" (erro específico da API, `Unable to parse range`) como limite
esperado do Calendário, não como falha de leitura.

**Achado 3, o mais importante: "essa mensagem não existe".** O auditor
corrigiu o entendimento de base sobre a aba Financeiro inteira: "entenda,
fechar ciclo é uma coisa, essa mensagem não existe, a de fechamento de ciclo
não existe, o Financeiro olha a própria planilha de monitoramento para
efetuar o pagamento... o que eu quero é que vc gere, cada post confirmado na
planilha de calendário, aquele texto que dá o check nas datas, que vai gerar
o texto que vai pro whatsapp do próprio marketing". Ou seja: a solicitação de
pagamento com escopo x entrega e justificativa (que existia desde 03/09,
antes desta sessão) **nunca foi um documento real que alguém manda**. O que
existe de verdade é o cronograma que o Marketing já manda no grupo deles
(print de "Júnior EDS" mostrado logo no início desta janela de trabalho:
"CRONOGRAMA DE POSTAGENS | EDS | LUCASGUIMARÃES | CICLO 6/12", checklist por
data).

Consequência em código: nasceu uma seção **nova e independente** em
`pages/3_Financeiro.py`, "Texto do cronograma para o WhatsApp do Marketing",
que gera exatamente esse formato a partir do Calendário, sem nenhuma menção a
escopo, situação do ciclo ou justificativa. E a seção antiga ("Fechar o
ciclo": justificativa, botão "Solicitar pagamento", registro de fechamentos)
ficou atrás de uma chave nova, `FECHAMENTO_DE_CICLO_ATIVO = False`, **guardada
e não apagada** — o código inteiro continua no arquivo, dentro de um `if`, e
liga trocando `False` por `True`.

Essa mudança teve um tropeço meu no meio: entendi errado da primeira vez e
tirei a **aba Financeiro inteira** do menu. O auditor corrigiu na hora: "não
era pra excluir a aba de financeiro, mas sim a parte do ciclo fechado". A aba
voltou ao menu com a pergunta "qual parte sai" respondida por ele mesmo:
"Fechar o ciclo" mesmo, e mais nada.

**Sobre a volatilidade do Calendário**, o auditor levantou um ponto de fundo:
"essa parte da planilha deles é bem volátil, sempre pode mudar... o que está
na planilha de calendário não necessariamente é o que será entregue". Isso
motivou três proteções, todas ainda de pé:

- só data com `Status` já preenchido pelo Marketing (`Publicada`/`Não
  Postada`) entra na mensagem; data com `Status` vazio é conferida na tela mas
  não sai para fora, **exceto** que depois o próprio auditor pediu para
  inverter isso (ver item 6 abaixo)
- a mensagem carrega o carimbo de quando o Calendário foi lido
- o que o Calendário dizia naquele instante é **congelado** no registro de
  fechamentos (`registro_fechamentos`, campo novo `cronograma_calendario`),
  gravado sempre, independente da chave de "Fechar o ciclo" estar ligada — é
  evidência do que a auditoria viu, não texto de aviso

E antes de aceitar isso como resposta definitiva, investiguei **como o
Marketing de fato trabalha quando o influenciador não posta**, medindo a
planilha real (1.989 linhas, `AGO.26` + `SET.26`): 96,4% das linhas `Não
Postada` têm alguém assinando em "Monitorado por" (é registro conferido, não
plano esquecido), e 85,9% delas nunca reaparecem publicadas depois (não é
remarcação frequente). A conclusão prática: o risco de remarcação é menor do
que parecia, mas a decisão de manter as três proteções ficou de pé mesmo
assim.

### 6. "Todas as datas, para a pessoa ir preenchendo"

Depois de ver a primeira versão do texto do WhatsApp (só com datas já
confirmadas), o auditor pediu a virada final: "seria possivel colocar todas
as datas pra pessoa ir preenchendo a medida que forem postando? pq assim que
eles fazem, e ai caso a data futura mude no calendário, deve mudar na
mensagem tbm". Troquei a fonte do texto de `cronograma_resolvido` (só
Publicada/Não Postada) para `cronograma` inteiro: data sem marca ainda
aparece **sem ✅ nem ❌**, pronta para ser preenchida, e como o texto é
montado na hora a partir do Calendário, qualquer edição de lá aparece na
próxima leitura (cache de 120 segundos), sem precisar baixar nada.

### 7. A saga de "por que não funciona no programa de verdade"

Pedi ao auditor para testar sozinho, e ele não achou nenhum influenciador
funcionando de verdade na tela. Isso levou a uma investigação em três
camadas, que vale registrar porque é exatamente o tipo de coisa que confunde
de novo:

1. **Nenhum dos 23 pares handle+ciclo que existem hoje na Monitoramento de
   teste tinha exemplo completo.** 16 caíam em `janela_do_ciclo` retornando
   `None` (rótulo de ciclo reaproveitado, o mesmo achado do item 5), e dos 9
   que sobravam com janela válida, **nenhum tinha linha correspondente na
   cópia de teste do Calendário** (ela só cobre `AGO.26`, `SET.26`, `OUT.26`).
2. **Ao tentar popular um exemplo (`@andersonneiff`, ciclo 5) escrevendo
   direto na Monitoramento de teste, caí eu mesmo numa armadilha já
   documentada no código**: usei `sheets_client.adicionar_linhas` (feita para
   a fila), que faz `.append()`, e a API deslocou a linha inteira uma coluna
   para a direita, porque a coluna A da Monitoramento é vazia no cabeçalho e
   o Google entende que a tabela começa na B. É literalmente o comentário que
   já existe em `registrar_na_monitoramento`: "a coluna A da Monitoramento é
   vazia no cabeçalho, e o Google entende que a tabela começa na B,
   empurrando a linha inteira uma coluna pro lado". Corrigi reescrevendo a
   linha em posição explícita (`.values().update()` num range exato), do
   jeito que o próprio `registrar_na_monitoramento` já faz.
3. Depois de corrigido, populei também 5 linhas no Calendário de teste
   (`AGO.26`) para `@andersonneiff`/LOTTU cobrindo a janela real do ciclo 5
   (12/08 a 31/08/2026): duas `Não Postada`, uma `Publicada` batendo com o
   download real, uma célula vazia (pendente) e uma `Publicada` **sem**
   download correspondente (para mostrar a divergência). Esse é hoje **o
   único exemplo garantidamente funcional de ponta a ponta** no programa de
   teste.

**O auditor testou a atualização ao vivo** (mudar o Status de uma linha do
Calendário de teste e ver o texto do WhatsApp mudar sozinho, sem baixar
nada) e confirmou que funcionou.

### 8. Decisão permanente: não usar as skills do superpowers

"não use superpowers" / "gasta muitos creditos" — já estava registrado como
preferência (`feedback_evitar_skill_pesada_com_cota_apertada.md`), e nesta
sessão o auditor confirmou que é definitivo, incluindo
`subagent-driven-development`. O rigor do processo (aprovação antes de agir,
medir antes de afirmar, testar antes de declarar pronto) continua sendo
seguido sem o maquinário de skills.

### 9. O `#publi` de baixo contraste, investigado e sem ação

Pergunta pontual sobre um vídeo de `@cassinha.161` que saiu `REQUER ANÁLISE
HUMANA`: baixei o arquivo do Drive, extraí quadros com ffmpeg e confirmei que
o `#publi` é texto branco fino sublinhado sobre céu e folhagem, sem caixa,
enquanto todo aviso que o OCR leu tem caixa opaca atrás. Concluí que o
veredito estava certo (a peça é conforme nesse ponto) e ofereci investigar
pré-processamento de contraste; o auditor fechou com "vamos deixar como
está".

### 10. Hoje: git

Descoberto que **já existe repositório git em `producao/analises`** (a raiz
`Documents/Auditoria` não é git, mas esta pasta é, desde 29/08/2026), com
`.gitignore` em formato de lista de permissão (bloqueia tudo, libera só
programa). O último commit era de 07/09/2026, e havia **cinco dias de
trabalho não commitado**, incluindo tudo desta sessão e mais os itens de
07–08/09 do "O QUE FICOU SEM DIÁRIO" abaixo. Conferido antes de commitar que
nenhum identificador de planilha REAL de produção aparece em arquivo
versionável (só os de teste, que já é o padrão aceito). Commit único
`54f2a87`, 60 arquivos, 9.637 inserções, mensagem detalhada por tema.

### O QUE FICOU SEM DIÁRIO (07 e 08/09/2026)

Ao revisar o que estava pendente de commit, apareceram testes e mudanças de
07 e 08/09/2026 que **não têm registro de conversa**: eu as encontrei já
prontas na cópia de trabalho, e o que sei delas vem só do docstring de cada
teste, não de ter estado presente na decisão. Ficam listadas para não
desaparecer, mas sem o "porquê contado pelo auditor" que o resto deste diário
tem:

- **Segmentation fault no trabalhador**, sem traceback: `sheets_client`
  guardava um único `service` por módulo sem trava entre threads
  (`teste_planilha_uma_thread_por_vez.py`)
- **Link que ficava esperando na fila sem baixar sozinho**, medido em uso
  real com dois stories da `@lomma` colados (`teste_link_esperando_baixa_sozinho.py`)
- **Visão que não respondeu virava `False`**, misturado com "não viu"
  (`teste_visao_sem_resposta_nao_acusa.py`)
- **Reel e post autenticados sem as três proteções de conta** (pausa, teto
  diário, recuo em bloqueio) que o caminho de Story já tinha
  (`teste_reel_e_post_passam_pelo_freio.py`)
- **Perfil já conhecido voltou a não gastar a chamada mais limitada** do
  Instagram (`teste_perfil_conhecido_nao_gasta_chamada.py`)
- **Escrever nos sistemas REAIS do Marketing passou a exigir os três
  arquivos de autorização**, não um só (`teste_modo_real_autorizado.py`)
- **Reforma visual**: emoji trocado por ícone do Streamlit em botão, e o CSS
  parou de mirar elemento por posição (`teste_telas_sem_emoji_em_botao.py`,
  `teste_estilo_nao_usa_seletor_posicional.py`)

Se o auditor confirmar o contexto de algum destes, vale registrar aqui como
seção própria, com data e citação, no mesmo padrão do resto do arquivo.

---

## AGENDADO PARA 03/09/2026: as rotas das pastas mudam

**Pedido do auditor em 02/09/2026, no fim do dia**, com a instrução explícita
"ainda não faça a modificação, agende para amanhã". Nada disso está no código.

### O que ele especificou

A ordem dos níveis dentro da pasta do dia **INVERTE**. Hoje é assim:

```
@influenciador / DD-MM / {story|reels|feed} / [orgânico] / arquivo
```

E passa a ser assim:

```
@influenciador / DD-MM / {orgânico | link | ???} / {story|reels|feed} / arquivo
```

Três coisas novas, nas palavras dele:

1. **A pasta `link` passa a existir**, irmã de `orgânico`. Ela é para "quando o
   influencer coloca o link da marca no post".
2. **A tela precisa de um botão Link** além do de Orgânico.
3. **Precisa existir uma TERCEIRA pasta**, para o que não é orgânico nem link:
   "a gente precisa de um lugar pra colocar feed/reels/story que não for orgânico
   e nem link". Ou seja, o tipo de mídia **nunca** fica solto direto na pasta do
   dia.

O nome dessa terceira pasta **não foi definido**. Não invente: pergunte, e leve a
medição do Drive deles junto (ver abaixo).

### O QUE AS TRÊS PASTAS SIGNIFICAM, nas palavras dele

Isto é a parte mais importante desta seção, e ela **não é sobre organização de
arquivo**. Perguntado o que separava uma da outra, ele respondeu:

> "a tela de orgânico é quando o usuário mostra só alguma coisa da marca, uma
> garrafa com a logo da lottu ou da EDS, ou Ona, e link é quando ele anuncia os
> jogos e coloca os avisos da portaria e tudo mais, porém ele coloca tbm o link
> que redireciona pra bet"

Então as três não são "orgânico contra pago". São **graus de peça publicitária**:

| pasta | o que a peça faz |
|---|---|
| `orgânico` | só mostra algo da marca, uma garrafa com a logo, sem anunciar jogo |
| a terceira | anuncia os jogos e traz os avisos, **sem** link para a bet |
| `link` | anuncia os jogos, traz os avisos, **e** leva o link que redireciona |

A terceira pasta é, portanto, a peça publicitária comum: anuncia com os avisos e
não redireciona. É por isso que ela precisava existir, e o nome tem que dizer
isso.

### A CONSEQUÊNCIA QUE ISSO TEM NA ANÁLISE, e ela é grande

Hoje o programa aplica **a mesma exigência a tudo** que baixa: aviso da portaria,
+18, "aposta não é investimento" e declaração de publicidade, e falta de qualquer
um é NÃO CONFORME (régua confirmada por ele em 02/09/2026).

Se `orgânico` é uma peça que só mostra uma garrafa com a logo, **a régua atual a
reprova sempre**, porque ela nunca vai ter os quatro avisos.

**O AUDITOR DECIDIU, em 02/09/2026, e a decisão é dele:**

> "orgânico não é fazendo propaganda, logo, ele não precisa colocar os avisos
> regulatórios pq ele ta so mostrando o patrocinio"

Então a régua passa a depender da marcação:

| marcação | avisos obrigatórios? |
|---|---|
| `orgânico` | **não**, porque a peça não anuncia, só exibe patrocínio |
| a terceira | sim, os quatro |
| `link` | sim, os quatro |

Continua valendo o que ele confirmou antes: se o item **está na tela, ainda que
pequeno, é conforme**; se não está, é problema; e na dúvida, REQUER ANÁLISE.

### A MARCAÇÃO DE ORGÂNICO NÃO PODE SER UM PASSE LIVRE

Isto é levantamento meu, e é o cuidado que essa decisão exige: se marcar
"orgânico" dispensa os quatro avisos, então a marcação passa a **decidir a
conformidade**, e ela é escolhida por uma pessoa na hora do download. Sem
contrapeso, marcar orgânico vira o caminho para qualquer peça passar.

O contrapeso já existe no motor e é barato: `REGEX_CONTEUDO_APOSTA`, em
`validar_avisos_portaria136.py`, detecta conteúdo de aposta no texto lido da
peça. Então dá para conferir a marcação em vez de confiar nela:

- marcada `orgânico` **e** o OCR não acha conteúdo de aposta → coerente, avisos
  dispensados
- marcada `orgânico` **mas** o OCR acha conteúdo de aposta → a peça anuncia. Ou a
  marcação está errada, ou é publicidade sem os avisos. Nos dois casos é para
  aparecer, e não para passar calado

Sugestão a levar para ele: nesse segundo caso a linha vira REQUER ANÁLISE com o
motivo dizendo qual foi a contradição, e não CONFORME nem NÃO CONFORME, porque o
programa não sabe qual das duas é.

### LINHAS JÁ ANALISADAS SOB A RÉGUA ANTIGA

Peça marcada como orgânica e analisada antes desta mudança tem veredito calculado
com a régua antiga. Conferido em 02/09/2026, na Monitoramento de teste: das 17
linhas com influenciador, **2 estão marcadas como orgânicas**, e as duas já têm
veredito:

```
linha  4   @julyafreitass   29/08/26   REELS   REQUER ANÁLISE HUMANA
linha 16   @jubrasil        25/08/26   REELS   REQUER ANÁLISE HUMANA
```

Nenhuma foi condenada como NÃO CONFORME, então não há falso achado gravado. Mas
as duas foram avaliadas exigindo avisos que, pela decisão dele, não se aplicam a
peça orgânica. Depois da mudança, apagar a célula de VALIDACAO dessas duas para
elas voltarem à análise.

### A pergunta que ficou sem resposta

Como a tela oferece as três opções, e o que acontece quando um post é orgânico
**e** tem o link da marca. O arquivo só pode morar em uma pasta.

- **escolha única** (rádio de três estados): sem ambiguidade, mas se o post for as
  duas coisas o analista escolhe uma e a outra informação não fica registrada
- **duas marcas independentes**, com precedência definida para a pasta e as duas
  colunas marcadas na Monitoramento, sem perder registro

Chegou "escolha única" pelo formulário, **mas ele avisou que fechou a pergunta
sem querer**, então essa resposta não vale. Pergunte de novo, e agora com a
terceira pasta no desenho, que muda as opções.

### O que precisa mudar quando a decisão vier

Levantado lendo o código em 02/09, para a conversa de amanhã não começar do zero:

| Onde | O que muda |
|---|---|
| `pastas_dentro_do_influenciador` | devolve `[data, marcação, tipo]` no lugar de `[data, tipo, orgânico?]` |
| `PASTA_ORGANICO` | ganha companhia: `PASTA_LINK` e a terceira |
| `nome_de_pasta_a_conferir` | as pastas novas também são "de palavra", então entram no aviso de grafia |
| `_pasta_de_destino_drive`, `enviar_para_drive` | o parâmetro `organico=` vira a marcação escolhida |
| fila (planilha) | hoje tem coluna `organico` (F); precisa carregar a escolha |
| Monitoramento | hoje tem `ORGANICO` na AB e `PEDIDO_POR` na AC; a marcação nova entra depois |
| tela de Downloads | o `st.checkbox` de orgânico vira a escolha de três |
| tela de Monitoramento | filtro e contagem de orgânico acompanham |
| `pages/1_...` (envio da supervisão) | tem a mesma marcação, e ela precisa mudar junto |

**A profundidade da busca NÃO muda**: hoje `_arquivos_do_influenciador` desce 3
níveis (data, tipo, orgânico) e continua sendo 3 (data, marcação, tipo). Vale
conferir, porque essa profundidade é o que faz a contagem de tela achar os
arquivos, e errar nela faz a numeração recomeçar do 1 sem avisar.

**Arquivo que já está no Drive não se move.** Renomear ou remover pasta lá é
ação separada, no Drive deles, e não foi pedida.

### MEDIDO EM 02/09/2026: como a pasta deles está HOJE, nível por nível

Varredura só de leitura, confinada a `VÍDEOS INFLUENCIADORES`, em **60
influenciadores**. Limitação que precisa ser dita: ela parou nesse limite e leu
as bets na ordem em que o Drive devolveu, então **não é amostra proporcional** das
quatro bets.

```
nível 1, dentro do @influenciador:   só pastas de DATA (21/05, 14/05, 17/08...)
nível 2, dentro da data:             story (48)  stories (23)
                                     vídeobruto (46)  bruto (25)
                                     vídeosbrutos (1)  brutos (1)
nível 3:                             VAZIO
```

Três coisas que isso mostra, e duas contrariam o que eu supunha:

1. **Não existe pasta `orgânico` nem `link` nessa amostra.** As duas aparecem em
   varredura por nome no Drive deles, feita em 01/09, mas não neste nível e não
   nestes 60. Então a estrutura que ele está pedindo é **nova**, e não a
   reprodução de algo que já esteja lá.
2. **O nível 3 está vazio**: os arquivos ficam direto dentro de `story`. Ou seja,
   a pasta `orgânico` que o programa cria HOJE dentro de `story` já é um nível a
   mais do que eles usam. Isso reforça o pedido de inverter.
3. **`vídeo bruto` e `bruto` são IRMÃOS de `story`**, no mesmo nível da data, e
   somam 73 pastas na amostra. Com a marcação entrando acima do tipo, é preciso
   decidir onde o bruto fica: irmão das marcações, ou dentro de cada uma. Ele não
   falou disso, e o programa hoje só IGNORA essas pastas ao contar tela (ver
   `e_pasta_de_bruto`), então a decisão é de organização, não de código.

A pasta da data usa barra (`21/05`), o que confirma `pasta_da_data`. Barra é nome
válido no Drive e separador no Windows, e é por isso que existe `nome_para_disco`.

---

## O QUE FOI DECIDIDO E FEITO EM 01/09/2026

Tudo abaixo está no código e coberto por teste. Suíte: 19 arquivos, 19 passando.

**1. A estrutura de pastas ficou assim**, e os nomes vieram de medição no Drive
deles, não de escolha nossa:

    bet / ano / mês / @influenciador / DD/MM / <tipo> [ / orgânico ]
    arquivo: "@influenciador Tela N"

`<tipo>` é `story`, `reels` ou `feed`. **É "story", minúsculo e no singular**, e
isso é medido: dentro da `VÍDEOS INFLUENCIADORES` existem 411 pastas `story`
contra 133 `stories`, 14 `Story` e 4 `STORY`. Um quarto do material está na
grafia plural, então a lista de sinônimos (`GRAFIAS_DA_PASTA_DE_TIPO`) não é
precaução: sem ela o programa criaria uma `story` ao lado de cada `stories` que
já tem material. `feed` nunca apareceu e `reels` apareceu 2 vezes, em maiúsculas,
então para esses dois a grafia é palpite.

**A pasta de CICLO não existe mais no Drive.** Ciclo é interpretação de contrato
e vive só na coluna CICLO da Monitoramento. Data é fato do vídeo e vira pasta.

**A pasta do dia é a data do POST, não a do download.** As duas quase sempre
coincidem em Story, mas não sempre, e a data da captura tem coluna própria
(DATA_DOWNLOAD). Sem data, a pasta sai como `sem-data` em vez de chutar hoje.

**2. Orgânico virou marcação, e a classificação é BINÁRIA**: orgânico ou não
orgânico. Confirmado pelo auditor, e isso encerrou uma dúvida que mudava o
desenho, porque uma descrição anterior dizia "orgânico, link ou ambas", e com
"ambas" a pasta não serviria de registro para nada.

Marcado, o material ganha uma pasta `orgânico` DENTRO da do tipo, e a linha
entra com a coluna ORGANICO (AB) marcada. Os dois no mesmo ato: pasta serve para
achar no Drive, coluna serve para filtrar e contar, e é a coluna que responde
"quantos posts deste ciclo eram orgânicos". A aba de Monitoramento ganhou filtro
de três estados e contagem.

A marcação existe nos DOIS caminhos de entrada: a seção do link e o envio de
arquivo, que é da SUPERVISÃO e é por onde a foto entra. Foto importa aqui: nas
pastas `orgânico` que já existem há 11 imagens contra 6 vídeos.

**3. O PROGRAMA PASSOU A CRIAR PASTA, e a regra "nunca criar" foi revisada.**
Pedido do auditor, com a premissa: facilitar a vida dos analistas, e quanto menos
eles criarem, melhor.

| nível | quem cria | por quê |
|---|---|---|
| bet, ano | Marketing | 5 pastas que já existem, ganho zero, e errar na raiz deles é o pior erro possível |
| mês | programa | medido: a comparação tolerante encontra TODAS as 19 pastas de mês de 2026, então criar só acontece dia 1º |
| @influenciador | programa, **com trava do cadastro** | ver abaixo |
| DD/MM, tipo, orgânico | programa | nenhum depende de digitação |

**A trava do @** (`impedimento_para_criar_pasta`): cria só se o @ estiver na
`Dados_influ`. Ela substitui o "nunca criar" porque duas coisas mudaram: desde
30/08 o @ não é digitado (sai do endereço ou do vídeo), e o cadastro é uma lista
fechada. Falha fechada: cadastro ilegível não autoriza criar. Não exige estar
ATIVO, de propósito, senão status desatualizado viraria falha de download. Erra
uma vez e relê o cadastro antes de barrar, para influenciador novo funcionar sem
reiniciar o programa.

**O que isso poupa**: ~49 pastas por mês criadas à mão, e o pior caso deixou de
existir. Dos influenciadores com STATUS ATIVO, **29 não têm pasta nenhuma em
2026**, e cada um era um download que falhava DEPOIS de gastar a chamada ao
Instagram.

**4. Duas correções que a medição expôs**, e as duas eram defeitos anteriores:

- **`brutas` passava pela regra de material bruto.** A regra procurava o pedaço
  `bruto`, e "brutas" não contém "bruto": **25 pastas** de material não editado
  entravam na análise como se fossem peça publicada. `NOMES_SUBPASTA_IGNORADA`
  ganhou `bruta`.
- **`05.MAIO` da ONA não era encontrada.** A comparação ignorava espaço só nas
  bordas, e o programa monta `05. Maio` com espaço depois do ponto. O efeito não
  era erro na tela: era o programa concluir que falta a pasta de maio da ONA,
  que está lá com material dentro. `chave_de_pasta` passou a ignorar TODO espaço,
  e agora as 19 pastas de mês são todas encontradas.

**5. O programa avisa quando cria pasta de nome discutível** (tipo e orgânico,
não a do dia, que seriam dezenas de linhas iguais por rodada). Criar em silêncio
é o que transforma um nome errado em dezenas de pastas duplicadas.

**6. O endereço de story sem o número da peça passou a AVISAR no clique**
(02/09/2026, pendência que vinha de 31/08). O endereço só ganha o número quando a
pessoa navega entre os stories, e sem ele o programa precisaria perguntar ao
Instagram o número interno do perfil, que é a consulta mais arriscada que ele
faz. Em 31/08 respondeu **429 Too Many Requests** e a chamada foi gasta sem
baixar nada.

A conferência custa **zero chamada**: lê o texto do endereço e o arquivo de
perfis conhecidos, e há teste proibindo `yt_dlp`, `instaloader` e afins dentro
dela. Dois casos: perfil desconhecido **barra** e ensina a pegar o endereço
certo; perfil conhecido **passa avisando** que só funciona com um story no ar.
Não barra tudo de propósito, porque quem tem UM story só nunca consegue navegar
e nunca consegue o número.

> **MEDIDO, E MUDA A EXPECTATIVA:** o programa conhece **11 perfis**, e
> `@maumauzk` NÃO está entre eles mesmo depois de 4 downloads dele em 01/09. O
> número do perfil só é aprendido quando o programa precisa dele, e com link que
> já traz o número ele nunca precisa. Ou seja: o caminho que BARRA vai ser o
> comum, não a exceção.
>
> A melhoria óbvia é aprender o número em todo download de Reel ou post. **Não
> está feita**, e depende de medir o que o yt-dlp devolve: `uploader_id` do
> Instagram costuma ser o @, e não o número interno. Medir antes de afirmar.

### MEDIDO EM 02/09/2026: o OCR está funcionando, e o número de "Requer Análise" enganava

O auditor achou que a análise tinha ficado menos assertiva, e perguntou se
"descalibrou". **Não existe calibração para desregular:** o programa é regex fixo
mais um modelo de visão com perguntas fixas, sem treino, sem ajuste e sem
acumulação. Cada vídeo é analisado do zero, isolado, e o cache nunca alimenta a
decisão de um vídeo novo. Nada que alguém suba muda como o próximo é julgado.

O número que assustou, e por que ele engana:

    dia          total  CONF  N-CONF  REQUER   % REQUER
    2026-08-30      16     4       1      11      69%
    2026-08-31      12     3       2       7      58%
    2026-09-01      11     0       0      11     100%
    2026-09-02       2     0       0       2     100%

Causa dos 34 Requer Verificação: **24 são "não achou aposta e NÃO leu nenhum
item"**, 3 são item não lido com a visão sugerindo presença, 2 são a visão
sugerindo logo de aposta, 1 é item do banner com irmão confirmado.

E o auditor explicou os 24: ele subiu muitos stories que não tinham nada a ver
com aposta, só para testar. Para material que não é peça publicitária, Requer
Verificação é a resposta certa, porque o programa não sabe distinguir "isso não é
anúncio" de "isso é anúncio e eu não consegui ler".

**CONCLUSÃO: o percentual de Requer Verificação não mede qualidade enquanto a
amostra tem material que não é publicidade.**

CONFERIDO ARQUIVO POR ARQUIVO, baixando do Drive e rodando a mesma escada de OCR
que a análise usa, com zero chamada ao Instagram:

| arquivo | o que o OCR leu | veredito certo? |
|---|---|---|
| `@maumauzk Tela 1` (Lottu) | faixa inteira: 18+, PORTARIA, APOSTA NAO É INVESTIMENTO | sim, e o Requer é só pelo publi |
| `@maumauzk Tela 2` | "Veeeem pra live do maufas" | sim, não é peça de aposta |
| `@maumauzk Tela 1` (01/09) | "compre aqui seu boné da tropa" | sim, vende boné |
| `@tatianabrasil Tela 1` | "Bolo de tangerina (receita na legenda)" | sim, é receita de bolo |
| `@cassinha.161 Tela 1` | nada, e os 3 quadros são a pessoa falando em casa | sim, sem texto e sem aposta |

**A HIPÓTESE DE DEFEITO DE LEITURA FOI DESCARTADA.** O OCR lê a faixa do rodapé
com folga a 720x1280, com o recorte de 28% de baixo que já existe.

ISSO REBAIXA A PRIORIDADE do item (a) da lista "PARA FAZER" (recorte da faixa do
rodapé): ele foi medido em quadro sintético, e no material real a faixa é lida
limpa. O caso que sustenta aquele item continua sendo o
`30-08 - @miltinhooalves - tela 1.mp4`, e ali o que não foi lido é o **publi**,
não a faixa.

**O PUBLI É O ÚNICO ITEM FRACO**, e isso casa com o que o auditor observou por
outro caminho: poucos influenciadores usam. Quando não é lido, na maioria das
vezes é porque não está lá.

OBSERVAÇÃO QUE EU NÃO SEI JULGAR, e fica para quem entende da norma: a faixa do
`@maumauzk` diz **"AUTORIZADO PELA PORTARIA SPA/MF Nº 136/25"**. A exigência que
o programa aplica vem da Portaria SPA/MF 1.231/2024, alterada pela 1.964/2026.
Não sei se 136/25 é outra numeração, é a portaria de autorização do operador, ou
é referência desatualizada na peça. Se for desatualizada, pode ser achado, e isso
é decisão de Compliance ou Jurídico.

### ABERTO, com decisão do auditor de deixar para depois

**`DADOS`: 10 pastas dentro da raiz deles, com 50 imagens de métrica** (tipo
`METRICAS TWITCH ULTIMOS 7 DIAS.jpeg`), todas em pasta de data. O pipeline de
análise as pega: `pipeline_influenciadores.py` lista a pasta do mês descendo três
níveis, e `DADOS` está exatamente lá. Print de métrica não tem aviso de jogo
responsável, então **sai como NÃO CONFORME**, que é falso positivo entrando em
achado. O auditor pediu para relevar em 01/09 porque não sabe o que a pasta é.
Nada foi mudado. Quando ele souber, a correção é uma linha.

**`ENTREGAS`: 11 pastas**, com 22 vídeos, 7 imagens e as subpastas `STORY` e
`FEED` dentro. Ninguém sabe o que é. Não é bruto e não é métrica, então por ora
entra na análise como material publicado, o que pode até estar certo.

**Duas linhas de `@andersonneiff` na fila de downloads**, com status BAIXADO E
ORGANIZADO apontando para arquivos que estão na lixeira do Drive. Elas sobraram
de um esvaziamento do Drive de teste feito por fora da função de limpeza, em
01/09. Não atrapalham nada além de ocupar a tabela, e limpar libera aqueles dois
links para reteste. Basta `remover_material_de_teste(["andersonneiff"])`.

### O que a medição derrubou, para não voltar como verdade

- **`link` NÃO guarda endereço.** As 12 pastas têm 22 vídeos `.mp4` e 2 imagens.
  A hipótese de serem endereços de mídia que não pode ser baixada foi testada e
  não se sustenta. Reforçando: dentro da `VÍDEOS INFLUENCIADORES` **não existe um
  único arquivo ou pasta** com "live", "youtube", "twitch", "tiktok" ou "twitter"
  no nome, em sete buscas. `link` é categoria de arquivamento por origem, igual a
  `orgânico`.
- **A primeira varredura, com 120 influenciadores, não valia.** Ela pegou os 120
  primeiros que apareceram em 2026, e muita gente ali não pertence mais à casa.
  Com o recorte nos ATIVOS, `stories` saltou de 2 para 93, e `orgânico` e `link`,
  que eu tinha afirmado não existirem no Drive deles, apareceram.
- **Uma busca por nome no Drive todo não vale**: tem que ficar dentro da `VÍDEOS
  INFLUENCIADORES`. Sem confinar, entraram PDFs de PLV de jogo de cassino e
  arquivos do nosso próprio projeto.
- **Nenhuma pasta espalhada por erro de digitação foi observada de verdade.**
  `@testefeeed` e `@testesrtorieees` eram nomes que o auditor digitou de propósito
  em teste; só `@feiijonys` existe. Este arquivo e seis pontos do código
  afirmavam o contrário, e foram corrigidos. O argumento que fica de pé é outro,
  e independe de incidente: no nível do @ o programa não tem como distinguir erro
  de digitação de influenciador novo.

### Fatos estruturais do Drive deles que valem saber

- No nível da data convivem **cinco arranjos**: por tipo (`story`, `REELS`), por
  origem (`link`, `orgânico`), genérico (`ENTREGAS`, com tipo dentro), métrica
  (`DADOS`) e bruto (`vídeo bruto`, `brutas`). Nunca houve convenção, e é por
  isso que a decisão de hoje vai conviver com todos por um tempo.
- **`story` tem 73 subpastas dentro**, então existe um nível a mais em alguns
  casos. A listagem cobre com profundidade 3, que alcança influenciador, data,
  tipo e a subpasta.
- **11 pastas `story` ficam direto na pasta do influenciador**, sem pasta de
  data. E 11 estão vazias.
- Fora da `VÍDEOS INFLUENCIADORES` existem outras 84 `story` e 53 `stories`, que
  estão fora do escopo.

---

## LEMBRETE PEDIDO PELO AUDITOR PARA 01/09/2026

Ele pediu, no fim do dia 31/08, para ser lembrado destas duas coisas. Elas vêm
com explicação dele, então não comece a mexer antes de ouvir:

**1. A ORGANIZAÇÃO DAS PASTAS.** Mudanças na estrutura, a explicar. O mapa do que
já existe hoje sobre pastas está na seção "COMBINADO PARA 01/09", item 3, para a
conversa não recomeçar do zero: os dois layouts, por que a comparação de nomes é
tolerante, por que o layout do Marketing está dormente, e o fato de não existir
pasta de ciclo lá.

**2. MUDANÇA DE ALGUNS BOTÕES.** Sem detalhe ainda, e é dele. Não confundir com
os botões já mexidos em 31/08 (saíram "Abrir a fila" e o expansor "Anteriores", e
o "Sair" ficou legível na barra lateral): isto é pedido novo.

E há três itens já DECIDIDOS e não aplicados, que ficaram esperando o trabalhador
ser encerrado. Estão na seção "COMBINADO PARA 01/09", em ordem: a pausa que
acontece depois do último link à toa (item 0), as rodadas continuando sozinhas
até a fila esvaziar (item 1), e o ciclo com campo na seção 1 registrando quando
foi informado à mão (item 2).

**Ler o item 0 junto com o item 1 antes de mexer**: se as rodadas passarem a se
encadear sem pausa entre elas, o resultado fica pior que hoje.

---

> RECONCILIADO EM 31/08/2026. Cinco pontos deste arquivo contradiziam o código
> e foram corrigidos na data: a data do cabeçalho, a contagem de testes, o teto
> de chamadas do Instagram, o volume diário do Marketing e duas afirmações da
> seção de 28/08 que medições de 29/08 já tinham derrubado. As seções antigas
> ficam como histórico, e agora avisam quando foram superadas. Se encontrar
> outra contradição, o código vale mais que este arquivo.

O que estava marcado para 30/08 (provar o download de Story e o primeiro uso
real do baixador local) foi feito. O histórico daquele plano está mais abaixo,
na seção "O QUE MUDOU EM 29/08".

---

## ABERTO E SEM CAUSA: a tela cai sozinha, sem deixar rastro no Python

Aconteceu DUAS vezes em 31/08/2026, e o auditor viu a primeira. O registro de
eventos do Windows mostra as duas com a MESMA assinatura:

    12:43:00   python.exe -> ntdll.dll   0xc0000005   offset 0x116135
    13:56:56   python.exe -> ntdll.dll   0xc0000005   offset 0x116135

`0xc0000005` é violação de acesso à memória, e o deslocamento é idêntico nas
duas. Isso é falha em código NATIVO, abaixo do Python, e explica por que o
arquivo de erro fica vazio: o processo morre no nível C, sem chance de gravar
rastro. Não é defeito de lógica do programa.

Na segunda vez: subiu 13:56:33, respondeu 13:56:49, morreu 13:56:56. Uns 20
segundos de vida. O trabalhador NÃO cai; só a tela.

NÃO CONSEGUI REPRODUZIR. Subindo com `-X faulthandler`, sobreviveu 75 segundos
sem nada além de um `ConnectionResetError` inofensivo (navegador fechando
conexão). Então é intermitente.

O QUE JÁ ESTÁ FEITO:

  - a tela sobe com a saída gravada em `teste_watch_folder/saida_da_tela.log` e
    `erro_da_tela.log`. Antes subia sem capturar nada, e por isso as primeiras
    quedas não deixaram pista
  - `-X faulthandler` armado: na próxima queda, se for em linha de execução que
    ele cobre, sai o rastro do Python no instante da falha

PISTAS, e nenhuma confirmada:

  - Python 3.14.6150 é muito recente, e o crash é em ntdll
  - memória livre estava em 2,6 GB de 15,7 GB, com VS Code, dois navegadores e
    o grupo de análise abertos. Numa máquina dedicada essa pressão não existe
  - as duas quedas foram minutos depois de eu reescrever arquivo do programa
    (`Set-Content` na página, `git bundle`), o que é suspeito mas não é prova

O QUE ISSO SIGNIFICA PARA O SERVIDOR, e é o ponto prático: processo que morre
em silêncio de vez em quando é sobrevivível SE algo o trouxer de volta. É
exatamente o item que o `preparar_servidor.ps1` já marca como bloqueio, "volta
sozinho: painel.py". Deixa de ser arrumação e passa a ser necessidade
confirmada por falha real.

ACRESCENTADO EM 31/08, FIM DO DIA: o "volta sozinho" ganhou um segundo
requisito, e por outro motivo. Foi medido que processo de análise sobrevive à
morte do trabalhador, então o mecanismo precisa limpar resíduo antes de subir.
Está na seção "O QUE MUDOU EM 31/08, FIM DO DIA". Não confundir os dois: um é a
tela que cai, o outro é o trabalhador que deixa filho para trás. Nada liga um ao
outro por enquanto.

---

## O QUE MUDOU EM 31/08, À NOITE: o login entrou em uso de verdade

**O LOGIN ESTÁ FUNCIONANDO, com conta Google, na máquina de trabalho.** Deixou
de ser código pronto e não ligado. O e-mail verificado aparece na barra lateral
e vai para a coluna de quem pediu cada tarefa, no lugar do nome digitado.

Como está configurado: `.streamlit/secrets.toml`, que o `.gitignore` bloqueia
pelo nome (confirmado pelo próprio git no `teste_acesso.py`). Provedor
`accounts.google.com`, cliente OAuth do tipo **aplicativo da Web**, retorno em
`http://localhost:8501/oauth2callback`.

**O cliente antigo do projeto NÃO serve**, e isso custa dez minutos a quem
tentar: o de `_drive_credenciais` é de aplicativo instalado
(`InstalledAppFlow`), e esse tipo não aceita volta de login web. Precisa de um
do tipo aplicativo da Web.

**No servidor o login exige HTTPS.** Google e Microsoft só aceitam retorno em
HTTP quando o destino é `localhost`. Isso vale para os dois provedores, não é
limitação do Google, e é item novo do checklist de subida.

### Achados do primeiro uso real, e nenhum foi pego por revisão de código

**1. Faltava a Authlib, e faltava também no `requirements.txt`.** O `st.login`
depende dela e ela não estava instalada. Passou batido porque a lista foi feita
lendo os imports dos arquivos, e nenhum arquivo nosso importa authlib: quem
depende é o Streamlit, por dentro. **O servidor seria montado sem ela e o login
não subiria, com o problema aparecendo no dia de ligar o login.** Instalada e
medida a 1.8.0, que trouxe joserfc 1.7.5. A compatibilidade foi conferida e não
presumida: a Authlib 1.8 marcou `authlib.jose` como descontinuada, e o Streamlit
1.59.2 tenta joserfc primeiro, então o caminho usado é o novo.

**2. Com provedor global, lista vazia aceitava o mundo inteiro.** O desenho
anterior era seguro por causa do provedor previsto, não por causa da regra:
lista de e-mails vazia significava "qualquer pessoa autenticada", e isso bastava
com o Entra ID da empresa, que já não deixa entrar quem é de fora. Com
`accounts.google.com`, que é global, ligar o login assim seria pior que não ter
login, porque pareceria protegido. Agora existe `DOMINIOS_AUTORIZADOS`, que já
vem com o domínio da empresa, e a porta **falha fechada**: sem lista e sem
domínio, ninguém entra.

**3. A navegação sumia, e com ela a proteção.** Sintoma: com o login ligado, a
aba "Validação Regulatória" desaparecia e a barra lateral mostrava nome de
arquivo. Causa: o `exigir_login` interrompia a página antes de o `painel.py`
chamar `st.navigation`, e o Streamlit caía no menu automático da pasta `pages/`,
que não conhece o arquivo da Validação, que mora na raiz.

O estrago maior apareceu na investigação: **as páginas de `pages/` são rotas
próprias e nenhuma exigia login por conta própria.** Só o `painel.py` exigia.
Isso valia inclusive para o caso em que o programa deveria estar TRAVADO, tela
na rede sem login. A trava protegia a porta e deixava as janelas abertas.
Corrigido em duas camadas: a navegação é declarada sempre, com uma página só
quando barrado, e cada página confere sozinha.

**4. Falha aparecia como sucesso.** Um Story que era foto saiu como "0 de 1
baixados e organizados" com marca VERDE. A tarefa termina como concluída porque
a rodada rodou até o fim, e o arquivo que não veio é resultado dela, não erro
dela. Agora zero organizados sai como erro, parcial sai como atenção, e o motivo
vem à vista. É o mesmo padrão do defeito do vídeo reaproveitado: a detecção
funcionava, a reação estava errada.

**5. Barra lateral.** O botão "Sair" ficava ilegível, texto quase branco em caixa
branca, porque o estilo pinta todo descendente da barra lateral de cor clara.
Chegou a ser confundido com campo de digitar o nome. E o e-mail aparecia como
link porque o markdown transforma endereço de e-mail em link sozinho.

### Duas coisas que o auditor achou na tela e NÃO eram defeito

Ficam registradas porque vão confundir de novo:

- **os "dois históricos" na tela de Downloads** eram a tarefa em andamento e a
  última terminada, não o mesmo bloco repetido. Mesmo assim foi corrigido: com
  trabalho em andamento, o resultado anterior não aparece
- **o clique em "Mandar analisar" que não fez nada.** Entre a tela ser desenhada
  e o clique, o caminho automático já havia enfileirado as linhas, então não
  havia mais nada para mandar. Medido na fila: só duas tarefas de análise depois
  das 16h, ambas com autoria "automático (após o download)", nenhuma com o
  e-mail dele. O botão não é silencioso, ele só existe quando há pendentes

---

## O QUE MUDOU EM 31/08, FIM DO DIA

### Processo de análise sobrevive à morte do trabalhador

Medido em 31/08/2026 com `Get-CimInstance Win32_Process`. Havia um processo de
análise vivo (18256), criado às 12:39:27, cujo pai (20264) não existe mais. O
pai não era o trabalhador atual (25912, subiu 13:56:33) nem a tela atual
(30756, subiu 14:00:35). A fila em disco estava com **0 pendente, 0 rodando e
44 concluídas**, então esse processo não tinha trabalho nenhum: era resíduo.

**O que isso prova:** quando o trabalhador morre, os processos de análise dele
NÃO morrem com ele. Ficam ocupando memória sem tarefa.

**Por que importa para o servidor:** o "volta sozinho" precisa limpar resíduo
antes de subir o trabalhador de novo, senão cada reinício acumula um processo, e
cada um pode carregar modelo. Memória livre na hora da medição: 2,3 GB de 15,69
GB. Isso deixa de ser arrumação e passa a ser requisito do mecanismo.

**O que NÃO foi provado, e não deve ser suposto:** que isso causa a queda da
tela. Foi conferido que a tela não cria grupo de processos, `abrir_equipe` só é
chamado em `trabalhador.py`. A coincidência de o resíduo nascer 12:39:27 e a
tela cair 12:43:00 não tem explicação e pode ser só coincidência.

### O botão de Manutenção agora avisa o alcance

Decidido pelo auditor em 31/08/2026, entre avisar ou tirar o botão da tela dos
analistas. **Ficou avisar**, porque encerrar antes de atualizar o programa é o
procedimento correto e frequente, e tirar obrigaria a chamar o administrador
para uma operação legítima.

O que mudou em `painel_trabalhador.botao_encerrar`:

  - o texto diz que **alcança todas as pessoas, não só quem clicou**. Antes lia
    como ação local, e existe um trabalhador só para as cinco pessoas
  - mostra quantos estão em andamento e quantos esperam na fila, e o que está
    sendo feito naquele momento
  - com trabalho em andamento ou na fila, o botão só libera depois de marcar
    ciência. Sem nada rodando não custa clique nenhum, que é o caso comum de
    quem vai atualizar o programa

Coberto por `testes\teste_manutencao_e_atalhos.py`, que mede o efeito e não só o
texto: sem a marcação, nenhum pedido de parada chega ao trabalhador.

### A tela de Downloads perdeu dois botões

Pedido do auditor na tela, em 31/08/2026: eram botões demais.

  - **"Abrir a fila" saiu.** A fila é passagem, não destino. Nada de rastro se
    perde: a planilha da fila continua existindo e recebendo tudo, o registro
    completo do fluxo fica no fim da tela, e o resultado de cada peça vai para
    a Monitoramento. Sobraram os dois atalhos que apontam para onde o material
    FICA. A função `fluxo.link_planilha_fila()` continua no lugar, sem uso.
  - **O expansor "Anteriores" saiu.** Mostrava um resumo de uma linha por
    download terminado, e essa lista some em 48 horas de qualquer forma. Quem
    precisa de histórico tem o registro do fluxo, que é mais detalhado e não
    desaparece.
  - o `▾` saiu dos rótulos de expansor, porque o Streamlit já desenha a seta e
    apareciam duas.

Efeito colateral medido de graça: o bloco lia 8 tarefas de cada tipo a cada 3 a
15 segundos, por pessoa com a tela aberta, e usava uma. Agora lê uma de cada.

---

## O QUE MUDOU EM 31/08, À TARDE: menos escolha, mais automático

Decisão do auditor, e o princípio vale para o que vier depois: **quanto menos a
pessoa escolhe no aplicativo, menos a escolha dela influi no resultado da
auditoria.** Foi dito com essas palavras, "por questão regulatória mesmo".

**A seção 1 virou só Instagram, com DOIS campos: link e marca.** O campo do @
saiu. Ele já era dispensável no Instagram desde 30/08, e ficava só para YouTube
e TikTok. O auditor confirmou que esses **não precisam ser baixados**: para
live de YouTube basta o link, que vai pela seção de registro. Link de fora do
Instagram agora é barrado na hora, com a mensagem apontando a seção certa, em
vez de falhar minutos depois na fila.

A marca é o único campo que sobrou porque é o único que o programa não tem como
descobrir: é informação de contrato, não está no link nem no vídeo.

**Baixar e analisar virou um passo só.** O botão passou a ser "Baixar e
analisar agora", com a chave "Analisar assim que baixar" LIGADA por padrão. Ver
`enfileirar_analise` em `fluxo_downloads.py`.

O ganho não é de clique, e esse é o ponto: escolher QUAIS vídeos analisar era
discricionariedade que não deixava rastro. Quem escolhia podia deixar um de
fora sem que nada registrasse. Analisando tudo o que entra, essa escolha
desaparece. Tirar algo da análise continua possível, mas só pelo caminho que
EXIGE motivo e fica gravado na planilha.

A chave existe para quem quiser só guardar o arquivo. Como já vem marcada, não
custa clique.

**"Bet" virou "Marca"** em toda a tela.

### VÍDEO REAPROVEITADO: o programa fazia o contrário do necessário

O auditor informou que reaproveitar vídeo é **vedado em contrato**: o
influenciador não pode republicar peça antiga como se fosse nova.

Ao conferir, apareceu que o programa engolia em silêncio exatamente esse
achado. Quando o mesmo vídeo era baixado de novo, `enviar_para_drive`
encontrava pela impressão digital, avisava "já está na pasta, não subi de
novo", e **RETORNAVA ALI, sem criar a linha na Monitoramento**. Resultado:

  - o segundo post não ganhava linha e nunca era auditado
  - o reaproveitamento não ficava registrado em lugar nenhum
  - a fila marcava "BAIXADO E ORGANIZADO", que lê como sucesso

Corrigido: agora avisa com a palavra REAPROVEITADO, diz que é vedado em
contrato, e **cria a linha assim mesmo**, apontando para o arquivo que já
existe. O arquivo não se duplica; a linha, sim, porque o post é novo e numa
data nova.

A DETECÇÃO nunca foi o problema, e vale registrar para quem vier: ela já
funcionava, por conteúdo, comparando a impressão digital que o próprio Drive
calcula, então nome diferente ou tela diferente não engana. O que estava errado
era a reação.

LIMITE CONHECIDO, e o auditor aceitou como piso: no layout do Marketing a busca
fica presa a UM mês e UMA marca, porque o caminho é bet/ano/mês/@influenciador.
Mesmo vídeo republicado no mês seguinte não é encontrado. No layout de teste ela
cobre o influenciador inteiro. Alargar para o ano e para todas as marcas é
melhoria registrada e não feita. Está no `teste_video_reaproveitado.py`, para
ninguém supor alcance que não existe.

---

## VOLUME REAL DO MARKETING, MEDIDO EM 31/08/2026

Levantado a pedido do auditor, contando ARQUIVO no Drive deles, e não linha de
planilha: cada arquivo é um download que alguém fez. Agosto de 2026, as quatro
bets, 1.195 arquivos de mídia.

**A estimativa que usávamos era três vezes pessimista.** Falávamos de 125 por
dia (5 pessoas × 25). O medido é 48 por dia útil.

**Eles trabalham em lote, e é isso que cria o risco.** Separando a data do post
de quando o arquivo entrou no Drive:

|  | por data do post | por dia que subiu |
|---|---|---|
| média por dia útil | 30,8 | **48,0** |
| maior dia | 46 | **182** |

Na quinta 27/08 subiram 182 arquivos, e os posts daquele dia foram 28. Sábado
29/08 subiram zero; domingo 30/08 subiram 71.

RESSALVA NOS PRÓPRIOS NÚMEROS: só 70% dos arquivos têm data no nome, então a
curva por data de post está subestimada. Corrigindo pela proporção, a média de
posts fica perto de 44 por dia, praticamente igual à de subida. As duas curvas
concordam no total e diferem na distribuição.

**Em chamadas ao Instagram**, a 2 por download:

| Cenário | Arquivos | Chamadas | Contra o teto de 20 |
|---|---|---|---|
| dia médio | 44 | ~88 | 4× |
| pico por data de post | 65 | ~130 | 6× |
| dia de mutirão (27/08) | 182 | ~364 | 18× |

**O achado que vale mais que os números:** usar a ferramenta todo dia, em vez
de em mutirão, derruba o pico de 182 para uns 65. É controle de risco que não
custa código, é rotina, e precisa entrar na conversa com o Marketing como
requisito.

**88% de tudo é LOTTU.** EDS 10%, ONA 2%, EDSCAP zero. Isso mede
principalmente a operação do LOTTU, e o volume sobe se as outras crescerem.

**2,23 arquivos por post**: 240 dos 378 posts têm 2 telas, 79 têm 3. Cada tela
é um endereço separado para o programa.

### O SERVIDOR ÚNICO NÃO FECHA COM SEIS CONTAS, e isso é de arquitetura

Achado em 31/08/2026, provado por teste (`teste_teto_com_seis_contas.py`, seção
4), depois de o auditor confirmar que cada pessoa tem a própria conta.

A regra **uma conta por dia por máquina** está em `situacao_da_conta`, em
`fluxo_downloads.py`. Ela existe por motivo medido: em 27/08/2026 duas contas
saíram do mesmo computador no mesmo dia e uma foi barrada. Além do contador,
duas contas no mesmo endereço de rede é por si só padrão que a plataforma
sinaliza.

**No servidor são seis contas e uma máquina.** Provado no teste: a primeira
conta que baixa prende a máquina, e as outras CINCO ficam barradas até o dia
virar, com a mensagem certa explicando a regra. Não é defeito da regra: é o
desenho de servidor único com seis contas que não fecha.

Três saídas, e só uma se sustenta:

  1. **servidor com UMA conta só.** São 90 chamadas por dia numa conta, 4,5
     vezes o teto de 20 e 6 vezes o maior dia limpo já medido. Não se sustenta
  2. **cada pessoa baixa da própria máquina, e o servidor analisa.** É o que o
     baixador local faz, e é a única que respeita a regra: uma conta por
     máquina, um endereço de rede por conta
  3. **seis contas saindo do servidor.** Viola a regra cujo motivo já foi
     medido em conta real

**ISSO REFORÇA E CORRIGE A JUSTIFICATIVA DO BAIXADOR LOCAL.** Ela estava
escrita como volume ("125 por dia não passam pela conta única do servidor"), e
o volume caiu para 45 por dia, o que enfraqueceu esse argumento. A justificativa
verdadeira é outra e é mais forte: **com seis contas, o download PRECISA sair de
seis máquinas.** O servidor continua fazendo o resto, que é analisar, organizar
no Drive e escrever na planilha.

Consequência para o procedimento de subida: o servidor NÃO deve ser o lugar de
onde saem os downloads do Instagram. Se alguém apontar o fluxo de download para
o servidor, cinco pessoas param no primeiro dia.

### CARTEIRA POR PESSOA, informada em 31/08/2026, e ela derruba o desenho do teto

O auditor levantou na planilha deles: **são SEIS pessoas, não cinco**, e os 45
influenciadores ativos estão divididos em carteiras de **10, 9, 8, 8, 8 e 2**.
Cada pessoa baixa em média **2 stories por dia** de cada influenciador seu.

Os nomes das pessoas ficam fora deste arquivo de propósito: para a decisão só a
distribuição importa.

A 2 chamadas ao Instagram por download:

| Carteira | Downloads/dia | Chamadas/dia | Contra o teto de 20 |
|---|---|---|---|
| 10 | 20 | **40** | 2,0× |
| 9 | 18 | 36 | 1,8× |
| 8 | 16 | 32 | 1,6× |
| 8 | 16 | 32 | 1,6× |
| 8 | 16 | 32 | 1,6× |
| 2 | 4 | 8 | 0,4× |
| **total** | **90** | **180** | |

**A TABELA ACIMA É O PIOR CASO, e não o dia normal. CORRIGIDO na mesma tarde.**

A primeira versão desta seção concluía que cinco das seis carteiras estouravam o
teto e que seria preciso ir a 40. Estava errado: a conta foi feita como se todos
os 45 postassem todos os dias.

O auditor esclareceu que **os influenciadores postam mais ou menos em dias
alternados, um dia sim e um dia não**. Em média metade da carteira posta em cada
dia, e o dia normal fica assim:

| Carteira | Postam/dia | Downloads | Chamadas | Contra o teto de 20 |
|---|---|---|---|---|
| 10 | 5 | 10 | **20** | exatamente no limite |
| 9 | ~5 | 9 | 18 | cabe |
| 8 | 4 | 8 | 16 | cabe |
| 8 | 4 | 8 | 16 | cabe |
| 8 | 4 | 8 | 16 | cabe |
| 2 | 1 | 2 | 4 | cabe |
| **total** | | **45** | **90** | |

**E OS DOIS CAMINHOS DE MEDIÇÃO CONVERGEM**, o que é a melhor notícia daqui: 45
downloads por dia por esta conta, contra **48 arquivos por dia medidos no Drive
deles em agosto de 2026**, levantamento independente que contou arquivo e não
linha de planilha. Duas contas por caminhos diferentes chegando ao mesmo lugar dá
confiança nas duas, e encerra a divergência que esta seção registrava.

Provado em `teste_teto_com_seis_contas.py`, que simula o consumo contra o
contador de verdade do programa, sem chamar o Instagram e sem subir teto nenhum.

**RESOLVIDO ÀS 19h05 DE 31/08/2026: É 1 CHAMADA POR DOWNLOAD, NÃO 2.**

Medição limpa, com UM link isolado, sem pausa e sem outro download no meio para
não confundir: o contador da @candyboxconfeitaria foi de **15 para 16** depois de
um download de story bem-sucedido, com arquivo no Drive e linha 34 criada na
Monitoramento.

ALCANCE, porque generalizar aqui seria repetir o erro que isto corrige: vale para
**story COM o número no link**, que é o caso comum. Story SEM o número custou 2
chamadas no mesmo dia e não baixou nada, porque gastou a consulta pelo @. Reel e
post não foram medidos.

**A TABELA DAS CARTEIRAS COM O NÚMERO MEDIDO:**

| Carteira | Downloads/dia | Chamadas/dia | Contra o teto de 20 |
|---|---|---|---|
| 10 | 10 | 10 | metade |
| 9 | 9 | 9 | cabe folgado |
| 8 | 8 | 8 | cabe folgado |
| 2 | 2 | 2 | cabe folgado |

**E ATÉ O DIA ATÍPICO CABE.** Se os 10 influenciadores da maior carteira
postarem todos no mesmo dia, são 20 downloads e 20 chamadas, exatamente o teto,
em vez do dobro. Cai a conclusão anterior de que a maior carteira pararia no meio
do dia em dia cheio.

`teste_teto_com_seis_contas.py` foi atualizado para o número medido, e agora
prova que a maior carteira usa no máximo metade do teto em dia normal e que o dia
em que todos postam cabe.

O texto abaixo fica como registro de como a dúvida apareceu, porque o método vale
para a próxima vez que um número deste documento nunca tiver sido medido.

~~ATENÇÃO: A PREMISSA DE 2 CHAMADAS POR DOWNLOAD FICOU EM DÚVIDA.~~

Observado em 31/08/2026, entre 18h41 e 18h56, na conta @candyboxconfeitaria, com
downloads reais de Story do Instagram:

| Momento | Contador |
|---|---|
| antes dos downloads | 11 de 20 |
| depois de QUATRO downloads bem-sucedidos | 15 de 20 |

Quatro downloads consumiram **quatro** chamadas contadas, e não oito. A premissa
de 2 por download está na base de TODAS as contas de teto deste documento,
inclusive da tabela das carteiras logo acima.

Se o certo for 1 por download, o teto de 20 vale 20 downloads por dia em vez de
10, e a maior carteira sai de "exatamente no limite" para metade do teto. Seria
folga que hoje se supõe não existir.

NÃO ESTÁ CONCLUÍDO, e por isso está registrado como dúvida e não como correção:
quatro downloads é amostra pequena, e existem caminhos diferentes de download
(story com número, story sem número, Reel, post, caminho de reserva pelo
instaloader) que podem contar diferente. A tentativa que falhou no mesmo dia, no
@andersonneiff, consumiu 2 chamadas para nada, o que sugere que a consulta pelo @
custa mais que o download em si.

COMO MEDIR DIREITO, para quem retomar: anotar o contador antes e depois de cada
download, separando por tipo de link, em vez de olhar o total do dia. O histórico
diário do contador (pendência 7) tornaria isso trivial, e é mais um motivo para
ele existir.

**AS CONCLUSÕES QUE FICAM, todas dependentes da premissa acima:**

1. **O teto de 20 já atende a operação de hoje.** Nenhuma carteira estoura em dia
   normal.

2. **Mas a maior carteira fica em 20 de 20, sem margem nenhuma.** Num dia em que
   os 10 influenciadores dela postem juntos são 40 chamadas, o dobro, e ela para
   no meio. É limitação conhecida, e é o que justifica a próxima etapa da subida
   existir. Não é motivo para subir correndo, e a regra da semana de observação
   continua valendo.

3. **Teto igual para carteiras desiguais continua sendo desenho errado**, só
   deixou de ser urgente: hoje custa uma pessoa parando em dia atípico, e não
   cinco parando todo dia. A maior carteira é 5 vezes a menor. Decidir se o teto
   passa a ser proporcional à carteira, e como o programa saberia disso.

4. **O que ficou grave não é o número do teto, é de onde as chamadas saem.** Ver
   a seção acima, sobre o servidor único não fechar com seis contas.

**PENDÊNCIA DE TEXTO, e é chata porque está espalhada:** o programa inteiro está
escrito para CINCO pessoas, incluindo texto de tela, comentário de código e este
arquivo. São seis. Corrigir onde aparecer.

### ~~A conta compartilhada~~ RESOLVIDA EM 31/08/2026: cada pessoa tem a sua

**CADA UMA DAS SEIS PESSOAS TEM A PRÓPRIA CONTA DO INSTAGRAM.** Confirmado pelo
auditor em 31/08/2026, e isso encerra a pergunta que era a mais urgente da lista.

O que isso resolve:

  - o teto por máquina (`baixador_local/_contagem_do_dia.json`) passa a ser teto
    por conta de verdade, que é o desenho correto
  - o baixador local recupera a justificativa: ele existia para não concentrar
    tudo numa conta só, e com seis contas ele faz exatamente isso

**O QUE ISSO NÃO RESOLVE, e convém não confundir:** o teto de 20 continua abaixo
do que a operação exige. Com as carteiras medidas (10, 9, 8, 8, 8 e 2), cinco
das seis pessoas precisam de 32 a 40 chamadas por dia. O problema deixou de ser
"tudo numa conta" e passou a ser "o teto é baixo e é igual para carteiras
desiguais". Ver a seção da carteira por pessoa, acima.

O raciocínio abaixo fica como histórico, porque explica por que a pergunta era
urgente e o que teria acontecido se a resposta fosse outra:

~~Surgiu em 31/08 a informação de que as 5 pessoas usam a MESMA conta do
Instagram, e o auditor ia confirmar. Se for verdade, muda tudo:~~

  - o teto do baixador local é POR MÁQUINA (`baixador_local/_contagem_do_dia.json`),
    então 5 máquinas × 20 autorizam 100 chamadas por dia na mesma conta, e
    ninguém vê o total: cada pessoa lê "18 de 20" e se sente disciplinada
  - a justificativa do baixador local cai: ele existia porque "125 por dia não
    passam pela conta única do servidor", e se a conta é a mesma ele não reduz
    carga de conta nenhuma, só espalha o endereço de rede
  - nenhum teto resolve: 88 chamadas por dia numa conta é 6× o maior dia limpo
    já medido (15, em 26/08)

Com CINCO contas, os números fecham: 88 ÷ 5 = 18 por dia por conta, dentro do
teto de 20 que já está no programa. Por isso essa confirmação virou a pergunta
mais urgente da lista, na frente do servidor.

---

## COMBINADO PARA 01/09/2026, E AINDA NÃO FEITO

Três coisas acertadas no fim do dia 31/08, nesta ordem de chegada. As duas
primeiras foram decididas e não aplicadas porque o trabalhador estava de pé, e
elas mexem em arquivo que ele importa.

**0. A PAUSA ACONTECE DEPOIS DO ÚLTIMO LINK, À TOA.** Achado em 31/08/2026 às
19h05, na mesma medição que resolveu a questão das chamadas por download.

O log, com UM único link na fila:

    19:04:30    -> subiu pro Drive de teste: ...
    19:04:31    (pausa de 125s antes do próximo link do Instagram, de propósito)

Não havia próximo link. A condição é `processados_instagram <
LIMITE_INSTAGRAM_POR_RODADA`, que olha se o limite da rodada foi atingido e NÃO
se ainda há trabalho na fila.

Duas consequências, e a segunda é a que incomoda de verdade: a tarefa fica
"rodando" por dois minutos sem fazer nada, o que é parte do que o auditor sentiu
como travamento; e como a análise só é enfileirada no fim da tarefa, **a análise
atrasa o tempo da pausa por nada**. No caso medido, 125 segundos.

Correção: pausar só quando existe próximo link do Instagram a processar. Fica
junto do item 1, porque é o mesmo trecho de código.

**1. As rodadas passam a continuar sozinhas até a fila esvaziar.** Decidido pelo
auditor. Hoje o programa processa 3 links do Instagram, deixa o resto e ESPERA
UM NOVO CLIQUE, o que ele encontrou ao mandar 4 links e ter um sobrando.

A escolha foi manter os 3 por rajada, com as pausas curtas de 30 a 180 segundos,
e fazer as rodadas seguintes sozinho, com uma pausa MAIOR entre elas, até a fila
acabar ou o teto do dia terminar. Ele havia pedido inicialmente subir para 5 por
rodada, e desistiu ao ver que 5 resolve o caso de 4 links e volta a pedir clique
a partir de 6.

CUIDADOS AO IMPLEMENTAR, e o primeiro é o que faria a mudança piorar tudo:

  - **precisa haver pausa entre as rodadas.** Hoje não há pausa depois do
    terceiro link (ver `if processados_instagram < LIMITE_INSTAGRAM_POR_RODADA`).
    Se a rodada seguinte começar logo, o resultado é uma rajada de 6 seguidos, o
    que é PIOR que subir o limite para 5
  - conferir `situacao_da_conta()` antes de cada rodada nova, e parar quando o
    teto do dia acabar ou a conta estiver em pausa
  - um limite de rodadas encadeadas como rede de segurança, para nunca virar
    laço infinito
  - só continuar se houve progresso na rodada anterior: sem isso, uma fila que
    não anda repetiria para sempre

**2. O ciclo passa a ter campo na seção 1, junto do link e da marca.** Hoje ele
só existe mais abaixo, na área das linhas pendentes, longe de onde o link é
colado, e o auditor apontou que definir ciclo não é exceção rara porque os ciclos
da Monitoramento se sobrepõem.

DUAS CONDIÇÕES, e a segunda não existe hoje:

  - o campo é OPCIONAL, com marca-lugar "pela data", como nas outras seções.
    Quem não mexe deixa o programa inferir, e a descoberta automática continua
    sendo o padrão. Isso preserva o princípio de 31/08 de reduzir escolha na
    seção 1, que foi o motivo de o campo do @ ter saído dela
  - **o programa passa a registrar quando o ciclo foi informado à mão**, em vez
    de inferido. Olhando a Monitoramento hoje não há como saber a diferença, e
    ciclo escolhido por uma pessoa é exatamente o tipo de discricionariedade que
    esta ferramenta existe para deixar rastreável

De passagem, isso resolve a inconsistência já registrada: a seção 2 exige ciclo
digitado enquanto as outras não, e a justificativa escrita em
`registrar_link_externo` não se sustenta, porque o ciclo vem da DATA e a seção 2
já pede a data.

**3. MUDANÇAS NA ESTRUTURA DAS PASTAS.** Avisado pelo auditor no fim do dia
31/08, para explicar melhor em 01/09. Não há detalhe ainda, então o que segue é
só o mapa do que já existe, para a conversa não recomeçar do zero:

  - `LAYOUT_PASTAS_DRIVE` escolhe entre dois desenhos, e o padrão é `teste`:
      - `teste`: árvore nossa, `@influenciador / Ciclo N`, e o programa CRIA
      - `marketing`: `bet / ano / mês / @influenciador`, e o programa ENCONTRA,
        nunca cria. Decidido em 30/08
  - a comparação de nomes é tolerante em todos os níveis do caminho, por medição:
    das 18 pastas de mês de 2026 no Drive deles, três não batem letra por letra
    (`01. Janeiro ` e `03. Março ` com espaço no fim, `08. AGOSTO` em maiúsculas)
  - **o layout do Marketing está DORMENTE**: só vale com a variável ligada, e só
    funciona de verdade com conta de serviço, porque o escopo `drive.file` só
    enxerga pasta que o próprio programa criou
  - **no Marketing não existe pasta de ciclo.** O ciclo vive só na planilha, e
    `pastas_dentro_do_influenciador` já devolve vazio nesse layout
  - o campo do @ como LISTA em vez de texto livre depende da mesma credencial, e
    é o item que tiraria a digitação do @ do caminho de vez. Enquanto for texto
    livre, um @ errado cria pasta órfã sem nenhum aviso, porque o programa não
    tem como distinguir erro de digitação de influenciador novo
  - coberto por `teste_pastas_do_marketing.py`, cujo nome resume a regra:
    encontrar pasta, nunca criar

---

## PARA FAZER, NESTA ORDEM

**As três frentes escolhidas e não feitas em 31/08 à noite.** Ficaram nesta
ordem por decisão do auditor, que preferiu fechar o dia. As duas últimas
EXIGEM encerrar o trabalhador antes, porque mexem em arquivo que ele importa.

  a) **Testar o recorte de faixa do rodapé num caso real.** É a melhoria de
     desempenho com maior efeito medido ainda pendente: 40% mais rápida e mais
     precisa que encolher o quadro inteiro (61,1s contra 101,5s), medida em
     29/08 num quadro sintético só, e por isso não entrou.

     O que faltava era um caso real com aviso pequeno de verdade, e ele
     apareceu em 31/08: o vídeo `30-08 - @miltinhooalves - tela 1.mp4`, onde o
     auditor confirmou a olho que o aviso existe e é pequeno, e nenhum dos três
     motores de OCR leu o #publi. Comparar os dois métodos NO MESMO arquivo.

  b) **A coluna EVIDENCIA passar a dizer o que faltou.** A definição dela, em
     `BLOCO_AUTOMACAO` no `fluxo_downloads.py`, é "o que faltou e em qual
     arquivo", e ela não faz isso: lista o que foi ENCONTRADO. O que faltou só
     aparece no veredito, na coluna VALIDACAO. Quem usa a evidência para
     conferir um achado, que é o uso dela, não encontra o que procura.

     Ao mudar, preservar a distinção que sustenta a regra de ouro: item que
     nenhum OCR leu e que a visão sugeriu NÃO pode ser escrito como ausência
     confirmada.

  c) ~~**QUESTÃO A DECIDIR: o 18+ deveria poder sair da lista de faltantes por
     sugestão da visão?**~~ **DECIDIDA EM 02/09/2026: a classificação FICA COMO
     ESTÁ, e o que estava errado era o texto.**

     Apareceu o caso real que faltava, e não foi com o 18+: foi com o **publi**,
     no `@andersonneiff Tela 1.mp4`. O auditor leu o motivo, concluiu "achei bem
     ok", e depois percebeu por conta própria, olhando o vídeo, que faltava o
     publi. A frase começava por *"IA de visão local sugere presença de
     identificação de publicidade"*, ou seja, **o texto escondeu o achado de
     quem escreveu a ferramenta.**

     Medido no cache: das 44 entradas, 10 dependem de uma sugestão da visão, e
     **8 delas são sobre o publi**. Todas as 10 estão como Requer Verificação.

     POR QUE A CLASSIFICAÇÃO NÃO MUDOU, conferido no código antes de mexer:

       - a sugestão da visão **nunca** produz Conforme. O ramo
         `if itens_ambiguos and not faltando_nao_ambiguo` devolve Requer
         Verificação, e só
       - um item confirmadamente ausente por OCR já produz Não Conforme,
         independente da ambiguidade dos outros
       - existe caso real nas DUAS direções, os dois registrados no código: a
         visão já confirmou um "18+" numa imagem que era print de conversa, e já
         acertou selo "18+" e publi de baixo contraste que o OCR não leu

     Com casos nos dois sentidos, cravar ausência seria a ferramenta afirmando
     mais do que sabe. O dano era todo de comunicação, e foi ali que se mexeu: a
     frase passou a começar pelo que NÃO foi confirmado, e a sugestão da visão
     virou ressalva. Coberto por `teste_ordem_da_frase_do_veredito.py`, que falha
     se alguém inverter a ordem de novo ou mudar a classificação sem querer.

     **FICA EM ABERTO, e é questão normativa, não de programa:** um aviso que
     três motores de OCR não conseguem ler pode ser considerado ostensivo? Se a
     resposta for não, o publi ilegível passa a ser achado por si, e isso muda a
     régua. Precisa de Compliance ou Jurídico, não de código.

  c2) **QUESTÃO ANTIGA, mantida como histórico do raciocínio do 18+**

     Levantada pelo auditor em 31/08/2026, ao lembrar que o aviso 18+ **precisa
     ser escrito**, e que o falado é reforço facultativo e nunca substitui.

     A regra do áudio já está certa e não precisa mexer: o áudio NUNCA alimenta
     `achou_18` nem nenhum outro `achou_*` (ver o comentário em
     `analisar_por_arquivo`). Isso foi conferido no código.

     O que ficou em aberto é outra coisa, e é uma tensão interna do desenho:
     quando nenhum OCR lê o 18+ e a IA de visão sugere que ele está lá, o item é
     marcado como ambíguo e SAI da lista de faltantes, sendo dito à parte. Só
     que o 18+ é exatamente o item em que a visão já alucinou, e isso está
     registrado neste arquivo, na regra de ouro: ela confirmou um "18+" numa
     imagem que era print de conversa.

     Ou seja, o item mais sujeito a alucinação é o que recebe o benefício da
     dúvida. Vale decidir se para o 18+ a sugestão da visão deve continuar
     tirando ele da lista, ou se ele deve entrar como faltante e o post ir para
     Requer Verificação quando for o único item.

     NÃO HÁ CASO CONFIRMADO. O auditor apontou um post que parecia ser esse, e
     depois concluiu que havia se confundido. Quem retomar precisa achar um caso
     real antes de mudar, porque endurecer a regra sem caso pode criar Não
     Conforme indevido em peça que traz o aviso ilegível para o OCR.

  d) **GUARDAR O NÚMERO DO PERFIL EM TODO DOWNLOAD, e não só quando ele é
     descoberto de propósito.** Levantado em 31/08/2026 às 18h50, depois de uma
     falha real.

     O que aconteceu: o auditor enfileirou `/stories/andersonneiff/?hl=pt`, link
     de story SEM o número do story. Esse formato obriga o programa a listar os
     stories do perfil, o que exige o número interno do perfil. Ele não tinha,
     caiu na consulta pelo @, e levou **429**. Duas chamadas gastas, nada
     baixado.

     O auditor estranhou, com razão: ele já tinha baixado desse influenciador
     antes. E é justamente aí que está o defeito de desenho.

     `guardar_userid` é chamado em DOIS lugares só: quando o número vem de um
     link de post (`userid_por_link_de_post`) e quando vem da consulta pelo @
     (instaloader). **Download comum não guarda nada.** Então baixar dez vezes
     do mesmo influenciador por link com ID não ensina o número ao programa, e o
     primeiro story sem ID paga a chamada mais arriscada que existe aqui.

     O mapa tinha 11 perfis em 31/08 (`instagram_userids.json`), e nenhum deles
     veio de download comum.

     A CONFERIR ANTES DE MEXER, e por isso isto é frente e não correção: o
     programa já usa o campo `uploader_id` dos dados que o Instagram devolve
     para descobrir o @, e DESCARTA o valor quando ele vem numérico (ver
     `_handle_dos_dados`, no teste `valor.isdigit()`). Quando vem numérico ele
     provavelmente É o número do perfil, mas isso não foi medido: precisa olhar
     os metadados de um download real de Reel e de Story para saber qual campo
     traz o número. Guardar número errado no mapa é pior que não guardar, porque
     o erro fica e não há sinal de que está errado.

     GANHO: cada influenciador passa a ter o número guardado depois do primeiro
     download bem-sucedido, de qualquer tipo, e a consulta pelo @ deixa de ser
     usada quase por completo. É a chamada que travou horas nos testes de 25/08
     e a que mais aproxima a conta de um bloqueio.

  e) ~~**Avisar na hora que o link de story não vai funcionar.**~~ **FEITO EM
     02/09/2026.** Ver `conferir_link_antes_da_fila` e o item 6 no topo deste
     arquivo. Foi feito com os dois endereços REAIS que o auditor mandou em
     print, e não com exemplo inventado, como este item exigia.

  f) **Enfileirar a análise a cada arquivo baixado**, e não no fim do lote.
     Hoje `enfileirar_analise` é chamado no fim de `processar_fila`, depois de
     todos os links e de todas as pausas. Com pausa de 150s entre links do
     Instagram, um lote de cinco deixa o primeiro arquivo pronto esperando mais
     de dez minutos com a máquina ociosa, e a linha aparece como pendente na
     tela de Validação nesse intervalo, convidando ao clique inútil (aconteceu
     em 31/08). Custo: uma leitura a mais da Monitoramento por link.


**0. O ciclo saiu das pastas, e sobraram quatro pontas.** Levantado pelo
auditor em 31/08/2026, ao perceber que o ciclo só vive na planilha porque o
Drive do Marketing é organizado por mês. A mecânica está certa
(`pastas_dentro_do_influenciador` já devolve vazio no layout do Marketing), mas
o texto e uma exigência não acompanharam:

> **CONFERIDO EM 02/09/2026: os itens a, b e c abaixo já estavam FEITOS, e este
> arquivo não sabia.** Não confie na lista sem conferir no código: foi por isso
> que a reconciliação de 31/08 existiu, e o mesmo aconteceu de novo.

  a) ~~**Dois textos da tela mentem**, dizendo que o Drive é organizado "por
     influenciador e ciclo".~~ **FEITO.** A única menção que resta em
     `pages/1_Downloads_e_Organizacao.py` é o comentário que explica que o texto
     dizia isso antes.

  b) ~~**A seção 2 (link externo) exige o ciclo digitado.**~~ **FEITO em
     31/08/2026.** Ver o comentário em `registrar_link_externo`, que registra o
     raciocínio: a justificativa antiga valia para o influenciador, não para o
     ciclo, que sai da data.

  c) ~~**A mensagem de vídeo repetido diz "já está em Ciclo N".**~~ **FEITO em
     31/08/2026.** Agora diz "já está na pasta X", usando o campo `onde`, que é o
     nome real da pasta onde o arquivo está.

  d) **O campo do @ deveria ser uma LISTA, não texto livre.** ÚNICO DOS QUATRO
     AINDA ABERTO, e continua sendo o mais importante.

     Digitar o @ só ajuda se estiver certo, e se estiver certo a pessoa poderia
     ter escolhido de uma lista. Campo de texto livre convida o erro que nada no
     programa consegue perceber, porque @ errado é indistinguível de
     influenciador novo. Lista elimina o erro pela estrutura, e não pela regra.

     **Bloqueado pela credencial**: o escopo `drive.file` só enxerga pasta que o
     próprio programa criou, então não há o que listar até existir conta de
     serviço.

     O campo NÃO pode ser removido de vez: em YouTube e TikTok não existe nada
     de onde descobrir o @. Desenho final: lista para Instagram, campo
     digitado só para YouTube e TikTok.

     **ATUALIZADO EM 01/09/2026, porque a premissa deste item mudou.** Ele dizia
     "no layout do Marketing o programa NÃO cria pasta". Agora ele CRIA a pasta
     do influenciador, com a trava do cadastro
     (`impedimento_para_criar_pasta`): cria só para quem está na Dados_influ. Ou
     seja, a proteção que a lista traria já existe em parte, e por um caminho que
     não depende da credencial. A lista continua sendo melhor, porque escolher de
     uma lista é menos trabalho que digitar e conferir, mas deixou de ser a única
     defesa contra @ errado.

**1. ~~Descobrir a capacidade da máquina do servidor.~~ RESPONDIDO EM 02/09/2026,
E A DECISÃO MUDOU DE DIREÇÃO.**

O auditor informou duas coisas que juntas mudam o desenho:

  1. **o servidor NÃO tem placa de vídeo**
  2. **os notebooks das analistas são IGUAIS ao dele**, e ele afirmou com essas
     palavras: "alias, estou afirmando, é igual o meu!"

A máquina dele, medida em 02/09/2026:

    Samsung 750XGK
    Intel Core i5-1335U, 13ª geração, 10 núcleos físicos, 12 lógicos
    15,7 GB de memória, e só 3,5 GB livres com o programa rodando
    Intel Iris Xe integrada, sem placa dedicada
    476 GB de disco, 344 livres

**SEM PLACA NO SERVIDOR, CENTRALIZAR A ANÁLISE NÃO COMPRA VELOCIDADE.** A análise
é CPU, e o trabalhador avisa isso na própria saída ("Using CPU. Note: This module
is much faster with a GPU"). Isso remove o principal argumento técnico a favor do
servidor.

**A PREFERÊNCIA DO AUDITOR, informada em 02/09/2026:** "se for viável instalar em
cada máquina, seria melhor que lidar com servidor".

CARGA DIÁRIA POR PESSOA, com o número medido e as máquinas iguais: **110 s por
vídeo** com dois processos ao mesmo tempo (medido em uso real: 25 vídeos em 46
minutos). Com 8 a 10 influenciadores por pessoa e 2 stories cada, são 16 a 20
vídeos, ou seja **29 a 37 minutos de máquina em CPU cheia por dia, por pessoa**.

> CORREÇÃO DE UM NÚMERO QUE EU DEI ERRADO na conversa de 02/09: falei "107 a 129
> segundos por LINHA". É por VÍDEO, e o valor com dois processos é 110 s. Linha
> pode ter mais de um arquivo, então a confusão inflava a conta.

ATENÇÃO À MEMÓRIA, que é o limite real e é igual em todas: 15,7 GB instalados e
3,5 GB livres com o programa de pé. O modelo de visão carrega inteiro na memória
e os dois processos de análise carregam duas vezes. Se apertar, o número a mexer
é `TRABALHADORES_PADRAO` no `pipeline_influenciadores.py`, hoje 2. Baixar para 1
custa velocidade (185 s por vídeo em vez de 110) e libera memória.

### O QUE FALTA PARA A INSTALAÇÃO LOCAL: três arquivos que hoje são locais

Levantado em 02/09/2026. Com seis instalações, três coisas FRAGMENTAM:

| arquivo | hoje | com 6 máquinas |
|---|---|---|
| `log_fluxo_completo.csv` | local | **6 registros parciais.** É a trilha de auditoria de todo download e envio, e numa auditoria ela não pode ser partida |
| `instagram_userids.json` | local | cada máquina reaprende o número do perfil, gastando **6 vezes** a chamada mais arriscada do programa |
| `resultados.json` | local | 6 caches de análise, e o mesmo vídeo pode ser analisado duas vezes |

E uma coisa MULTIPLICA: as credenciais. Três tokens do Google mais os cookies do
Instagram, hoje em texto puro, passariam a existir em seis máquinas. É o
argumento mais forte a favor da conta de serviço que a Segurança da Informação já
recomendou, e a decisão é deles.

Duas coisas JÁ ESTÃO CERTAS por máquina, e devem continuar: o contador do dia e a
trava de conta única (`CHAVE_MAQUINA`). Elas existem justamente para o cenário de
uma máquina por pessoa, que agora é o escolhido.

ORDEM SUGERIDA: começar pelo log, que é o que a auditoria não pode perder.

O QUE CONTINUA SEM RESPOSTA: se o setor de TI permite instalar Python e Ollama
nessas máquinas. É o mesmo pessoal que está com o SSO.

Quando souber, rodar na máquina de destino:

    powershell -ExecutionPolicy Bypass -File preparar_servidor.ps1
    py verificar_ambiente.py

O primeiro confere o que faz um notebook parar sozinho (suspensão, tampa,
voltar depois de reiniciar) e os mínimos de processador, memória e disco, com
o porquê de cada número. O segundo confere pacotes, ffmpeg, Tesseract com
português e Ollama, e funciona em Windows e em Linux.

**2. Entrar na leva do SSO da empresa.** Mudou de natureza DUAS vezes em
31/08/2026.

Primeiro porque o login **já funciona**, com conta Google, na máquina de
trabalho. O que falta não é código.

Segundo, e mais importante para o procedimento: **a cibersegurança está
implementando SSO neste momento**, informado pelo auditor, e segundo ele com
bastante confusão. Isso inverte o caminho que estava escrito aqui. Pedir um
registro de aplicativo isolado no Entra ID passa a ser o jeito errado: cria
aplicação paralela ao projeto em curso, que depois teria que ser desfeita, e
gera atrito exatamente onde já há confusão.

O certo é a ferramenta entrar como uma das aplicações do projeto de SSO. Ajuda
na conversa saber que ela **não pede nada de especial**: é OpenID Connect
padrão, com um endereço de retorno para cadastrar, e nenhum escopo além de
identidade.

**O LOGIN COM GOOGLE É SÓ TESTE, e isso precisa ficar dito.** O que ele provou é
o mecanismo (barra quem não entrou, a trava de domínio funciona, o e-mail
verificado chega na coluna de quem pediu, as páginas não são alcançáveis por
fora), e não a escolha de provedor. **NÃO levar o `.streamlit/secrets.toml` da
máquina de teste para o servidor**: se ele for copiado na subida, o Google vira
o provedor de produção por inércia, sem ninguém ter decidido. O cabeçalho do
próprio arquivo avisa isso, mas aviso não impede.

A trava de domínio (`DOMINIOS_AUTORIZADOS`) continua valendo com SSO. Com o
provedor da empresa ela deixa de ser a primeira camada e passa a ser a segunda,
que é o lugar certo dela, e cobre o caso de alguém trocar de provedor sem
lembrar que ela existe.

O Entra ID continua sendo o caminho previsto para o servidor, e o passo a passo
está no cabeçalho de `acesso.py`. Trocar de provedor é trocar cinco linhas de
configuração, sem mexer em código. **Escolher entre Google e Entra ID para a
ferramenta é decisão de arquitetura de identidade, e passa pela Segurança da
Informação.**

Enquanto o servidor não tiver login configurado, o programa funciona sem ele
desde que escute só em 127.0.0.1, e TRAVA sozinho se detectar a combinação de
estar na rede sem login. Desde 31/08 essa trava vale para as páginas também, e
não só para a porta de entrada.

Item novo do checklist de subida: **o login exige HTTPS no servidor.** Só
`localhost` é aceito em HTTP, nos dois provedores.

**3. Combinar com o Marketing duas coisas**, que são a mesma conversa: por
onde passam os downloads do dia, e a concessão de escrita na pasta deles no
Drive.

O número desta conversa mudou em 31/08/2026, e mudar para menos. Dizia 125 por
dia, que era estimativa (5 pessoas × 25). O medido, contando arquivo no Drive
deles em agosto de 2026, é **48 por dia útil**, com **pico de 182** num dia de
mutirão. Ver "VOLUME REAL DO MARKETING", mais acima. Levar o número medido para
a conversa, e levar também o pedido de rotina diária em vez de mutirão, que é o
que derruba o pico sem custar linha de código. Hoje o acesso é só leitura, confirmado pela API
(`canAddChildren` falso). É a conversa que mais muda o desenho da operação e a
que menos foi iniciada.

**4. Rever o desenho do teto do Instagram, e não só continuar a subida.**
Mudou em 31/08/2026, quando a carteira por pessoa foi informada.

O que estava planejado: foi para 20 em 30/08, primeira etapa de uma subida
medida, e uma semana limpa em 20 autorizaria ir a 30. Isso continua valendo como
método, e a regra de não pular etapa continua de pé: acima de 15 por dia não
existe dado nenhum no regime novo.

O que mudou: agora sabemos que **cinco das seis pessoas precisam de 32 a 40
chamadas por dia** (carteiras de 10, 9, 8, 8, 8 e 2, a 2 stories por
influenciador e 2 chamadas por download). Duas consequências:

  - o destino da subida não é 30, é perto de **40** para a maior carteira. São
    mais etapas do que se pensava, e cada uma pede a sua semana de observação
  - **teto igual para todos deixou de fazer sentido.** A maior carteira é 5 vezes
    a menor. Teto único faz quem tem 10 influenciadores parar no meio do dia
    enquanto quem tem 2 usa menos da metade. Decidir se o teto passa a ser
    proporcional à carteira, e como o programa saberia disso

Antes de dimensionar, reconciliar a divergência de volume registrada na seção da
carteira: 90 arquivos por dia pela conta contra 48 medidos no Drive em agosto.

A justificativa do método está em `fluxo_downloads.py`, na constante
`LIMITE_DIARIO_INSTAGRAM`, e repetida em `baixador_local/baixador.py`.

**5. Conferência de duas janelas na tela.** A integridade dos dados já está
provada com processos simultâneos de verdade (`teste_varias_pessoas.py`), e o
auditor já confirmou que mandar o mesmo endereço pelas duas gera um download
só. Falta o resto: se as duas janelas mostram o mesmo estado, se a contagem de
"em análise" bate, e se o "tirar da fila" lista só o que aquele nome pediu.

---

## O QUE VEM DEPOIS DA SUBIDA: cadastro, financeiro e alerta de cota

Levantado pelo auditor em 31/08/2026 como as próximas três coisas da ferramenta.
**Nada disso foi implementado**, por decisão dele: entram depois da subida, para
a subida não atrasar. O que está aqui é o desenho e as MEDIÇÕES feitas nas
fontes reais, que é o que economiza tempo de quem retomar.

Ordem de dependência: **1 destrava 2, e 2 destrava 3.** Sem cadastro com a cota
contratada não há o que comparar, e sem comparação não há o que alertar.

Nenhum dos três depende da resposta sobre a conta única do Instagram.

### 1. Cadastro de influenciadores

**Não precisa de banco de dados, e também não precisa criar cadastro.** A aba
`Dados_influ` da Monitoramento real JÁ É o cadastro: medida em 31/08, tem **203
influenciadores e 20 colunas**, incluindo ESCOPO (preenchida em 180 de 203),
STATUS (203), CATEGORIA (203), RESPONSAVEL (194) e INÍCIO e FIM de contrato (172
cada). Construir outro do zero seria copiar 20 colunas que já existem, e a cópia
envelhece sozinha.

**NÃO tem número de contrato do Netlex.** Conferido coluna por coluna.

**O contrato é campo OPCIONAL, nunca chave.** Decisão do auditor, com três
motivos, e os dois primeiros são dele: no Sankhya nem todos os influenciadores
têm contrato amarrado; renovação muitas vezes não encerra o anterior, então "o
contrato vigente" pode ser ambíguo; e a consulta `Resultado_da_Query555` amarra
contrato ao PAGAMENTO, não ao influenciador, já registrando "Não vinculado no
Sankhya" quando falta.

**Chave: influenciador, marca e período**, que é a mesma âncora de ciclo que a
auditoria já usa. Assim quem não tem contrato não fica fora, e renovação
sobreposta fica visível em vez de virar escolha silenciosa do programa.

Campo vazio deve dizer o motivo na tela, algo como "sem número no Netlex".
Célula em branco em ferramenta de auditoria lê como "ninguém olhou".

**CUIDADO COM DADO PESSOAL:** a `Dados_influ` tem quatro colunas sem função na
auditoria de publicidade, `ID_CONTA`, `CONTA`, `CONTATO_AGENTE` e `ENDERECO`.
Ler o que precisa na hora que precisa evita trazer isso para a nossa base
(princípio da necessidade, LGPD art. 6º, III). Copiar a aba inteira traria junto.

### 2. Aba de financeiro: escopo contratado contra entregue

**Já existe, feito à mão.** A planilha ULTIMA_VERSAO, na pasta PAPEL DE TRABALHO
do Drive, tem a aba `Achado01_EntregaEComprovacao` com 260 linhas e exatamente
estas colunas: Influenciador, Período, Ciclo, **Escopo Contratado (Completo)**,
Entregue, Não Entregue, Status Escopo, Status Comprovação, Observação, Status
Pagamento, Validação Data NF.

RESSALVA DO PRÓPRIO AUTOR, e ela importa: aquela planilha foi montada para
**apresentar** a auditoria ao Marketing, então não é especificação. Aproveitar o
método (escopo contratado, entregue, não entregue, status) e descartar a forma.
Os ícones ✅🚫⏳ não vão para a ferramenta, pela regra de não usar símbolo nem
jargão em tela e planilha.

**A planilha do Marketing também já tem uma aba Financeiro**, com cabeçalho na
**linha 4**, e colunas ESCOPO, @doinflu, CICLO, TIPO, OBS, POST, DATA_POST,
HORAS_LIVE.

ARMADILHA MEDIDA NELA: é preenchida em **blocos**. O @ e o escopo aparecem só na
primeira linha do bloco, e as de baixo trazem apenas POST e DATA_POST. Contar
sem preencher para baixo primeiro atribui entrega ao influenciador errado.

### 3. Alerta de cota cumprida

**O escopo é o risco do projeto, e foi medido:** 260 linhas em **69 formatos
distintos**, 44 caracteres em média, do tipo "12 COMBOS DE STORIES" e "7 COMBOS
DE STORIES + 2 REELS + 4 TWEETS". Cinco armadilhas presentes nos dados:
maiúsculas e minúsculas juntas, conectivo variando entre mais, vírgula e a
palavra "e", espaço duplo, itens não contáveis (participação em eventos, link na
bio) e unidades diferentes na mesma coluna (50 HORAS LIVE contra 12 COMBOS).

POR ISSO o escopo deve entrar **estruturado** na ferramenta, uma linha por item
com tipo de lista fechada e quantidade em número, e não como frase digitada.
Cumprir cota passa a ser subtração em vez de interpretação de texto perto de um
pagamento. As 69 variações servem como CASO DE TESTE, não como formato de
entrada.

**Decisões já tomadas pelo auditor:**

- **só peça validada como CONFORME conta como entrega.** Evita avisar que a cota
  fechou contando peça que está Não Conforme. Custo aceito: o aviso chega depois
  de a análise rodar
- **canal Slack.** WhatsApp exige a interface oficial da Meta, com número,
  modelo de mensagem aprovado e custo, e passa por outra área. A URL do webhook
  é CREDENCIAL: fora do Git e nunca em conversa
- **a conferência mora no trabalhador**, não na tela. O laço dele já tem o padrão
  de tarefa periódica (o passo 5, da limpeza do histórico). Na tela, o aviso
  dispararia por quem abriu a página e não dispararia se ninguém abrisse
- **o aviso é uma TAREFA NA FILA**, não um envio solto. A `fila_trabalho` já tem
  trava, as quatro situações e `recuperar_orfas`, então herda de graça o que é
  difícil: não repetir, não perder, e guardar histórico de quem foi avisado

**A CONSEQUÊNCIA MAIS IMPORTANTE da regra "só Conforme", e é fácil de perder:**
existem TRÊS situações, não duas, e a do meio é a que mais interessa à auditoria.

  1. cota completa e todas as peças Conforme: é o aviso ao financeiro
  2. cota completa em quantidade, porém com peça Não Conforme ou Requer
     Verificação. NÃO é cumprimento, e **desaparece** se o programa só olhar a
     situação 1: a cota fica aberta para sempre e o aviso simplesmente nunca
     sai, sem ninguém saber por quê. É achado, e vai para o auditor, não para o
     financeiro
  3. cota incompleta, e nada acontece

**Pendências antes de prometer o envio:** testar no servidor se ele alcança o
Slack com o certificado corporativo (se falhar, instalar a cadeia corporativa,
NUNCA desligar a verificação), e decidir se entrega fora da janela do contrato
conta como cumprimento, que é regra de negócio e toca no achado de datas.

**E uma questão de papel, que não é técnica.** Aviso automático da ferramenta de
auditoria dizendo ao financeiro que a cota foi cumprida será lido como liberação
para pagar. Se isso acontecer, a auditoria interna passa a integrar o circuito de
aprovação de pagamento e deixa de poder auditar esse mesmo circuito com
independência. O texto precisa dizer que é acompanhamento e que o atesto continua
com o gestor do contrato. Vale validar com Compliance antes de ligar.

### Onde estão as fontes

Pasta **PAPEL DE TRABALHO** no Drive, 16 itens:

    https://drive.google.com/drive/folders/15brhcHKeeiR6P72yw7FC6WVlB8ItbsC3

O que importa nela: `Auditoria_Influenciadores_Pagamentos_e_Comissoes_ULTIMA_
VERSAO.xlsx` (7 abas: Resumo, Achado01 a Achado05, Cobertura_Programa) e o
documento `Consultas ao Sankhya (v1.2, 21/08)`, que explica de onde vem cada
número, inclusive o contrato do Netlex.

Do documento de consultas, o que é fato e não se deduz de outro lugar: a
extração principal tem **1.554 pagamentos**, de setembro de 2025 a 19/08/2026, e
os achados testam apenas **01/05 a 31/07/2026**, três meses fechados. A base é
mais ampla de propósito, porque o teste de datas precisa achar a primeira parcela
ou renovação de cada contrato, a âncora do ciclo, mesmo antes da janela.

Ler essas fontes com a credencial SOMENTE LEITURA
(`_drive_credenciais/drive_token.json`), nunca com o token de escrita.

### Duas ressalvas de método, para não usar número errado

**As contagens por coluna não são população testada.** Contar células
preenchidas inclui legenda e totalização. Por isso os 260 da `Achado01` e os 387
da `Achado02` não devem ser lidos como "quantos foram testados", e não batem com
os números das versões vigentes dos achados (225 e 385). Reconciliar contra a
fonte antes de usar em texto ou tela.

**A divergência de contagem de influenciadores não é achado.** O Drive tem 266
com pasta e a `Dados_influ` tem 203 cadastrados. O auditor esclareceu que muitos
não pertencem mais à casa, então a diferença não deve ser tratada como material
publicado sem cadastro sem apuração própria.

---

## O QUE MUDOU EM 30/08

Dia longo, 12 commits. O que importa saber antes de mexer em qualquer coisa:

**O @ do influenciador é descoberto sozinho no Instagram.** Vem do endereço
quando ele traz, senão dos dados que o Instagram devolve junto com o vídeo, e
só depois do que foi digitado. O digitado é o último de propósito. O campo da
tela deixou de ser obrigatório para Instagram; em YouTube e TikTok continua.

**O OCR estava lendo português com modelo de inglês.** O Tesseract não reclama
quando o idioma pedido falta: cai para o inglês em silêncio. Medido com as
regex do próprio programa: só com inglês, **duas das três frases obrigatórias
do Ministério da Fazenda nunca eram encontradas em texto pequeno**. Peça que
tem o aviso seria classificada como se não tivesse. O pacote foi instalado e o
`verificar_ambiente.py` acusa quando falta.

**O cache de análises foi zerado**, com cópia em
`resultados_backup_20260830_162925.json`. Nenhuma das 14 análises guardadas
tinha sido produzida pelo código atual: 12 rodaram em 29/08 entre 18h25 e
21h53, e o primeiro commit é de 22h50, então elas são de código que não existe
no git. As 15 linhas da Monitoramento de teste foram reprocessadas em 30/08.

**A bet ficou obrigatória** e o programa passou a ENCONTRAR pasta no Drive em
vez de criar, com comparação tolerante em todos os níveis do caminho. Motivo
medido: das 18 pastas de mês de 2026 no Drive do Marketing, três não batem
letra por letra (`01. Janeiro ` e `03. Março ` com espaço no fim, `08. AGOSTO`
em maiúsculas na ONA). Isso está DORMENTE: só vale com
`LAYOUT_PASTAS_DRIVE=marketing`, que está desligado, e só funciona de verdade
com conta de serviço.

**Os caminhos fixos de máquina saíram.** A cópia da Monitoramento e o
Tesseract são descobertos: variável de ambiente, lugar conhecido, PATH.

**Login pronto e não ligado.** Ver item 2 acima.

**Teto de 12 para 20**, e o baixador local ganhou teto (estava sem nenhum).

**A cópia local de conferência vem desligada** por padrão (eram 495 MB em
poucos dias com uma pessoa). Liga com `COPIA_LOCAL_DE_TESTE=1`.

**A entrada na fila de downloads ficou travada.** Duas pessoas mandando o
mesmo endereço ao mesmo tempo criavam duas linhas, ou seja, duas chamadas ao
Instagram para o mesmo vídeo. Provado com 4 processos simultâneos.

### Testes automatizados: 14, todos passando (conferido em 31/08/2026)

O título dizia 12 e a lista abaixo já tinha 13. Conferido contando os arquivos
em `testes\`: são 14 com o de 31/08, e os 14 passaram na íntegra.

    py testes\teste_acesso.py                  quem pode abrir o programa
    py testes\teste_caminhos_do_servidor.py    nada de caminho fixo de máquina
    py testes\teste_contagem_do_baixador.py    a contagem do dia não se perde
    py testes\teste_download_em_duas_etapas.py o mecanismo de download
    py testes\teste_envio_em_lote.py           o envio chega inteiro
    py testes\teste_fila_sem_duplicar.py       mesmo endereço, um download só
    py testes\teste_handle_do_baixador.py      o @ no baixador local
    py testes\teste_handle_do_servidor.py      o @ no servidor
    py testes\teste_identidade.py              nome declarado
    py testes\teste_pastas_do_marketing.py     encontrar pasta, nunca criar
    py testes\teste_sinais_do_instagram.py     bloqueio x perfil sem story
    py testes\teste_varias_pessoas.py          a fila com 5 pessoas
    py testes\teste_video_reaproveitado.py     repetido gera linha, não silêncio
    py testes\teste_manutencao_e_atalhos.py    encerrar avisa que alcança todos,
                                               e falha não aparece como sucesso

Rodar todos antes de qualquer commit. Vários deles nasceram de defeito que
passou despercebido em revisão e só apareceu no uso real.

---

## O QUE MUDOU EM 29/08: o trabalho saiu da aba do navegador

Motivo: a pergunta "dá pra 5 pessoas usarem isso?". A resposta foi que o
Streamlit dá conta da tela, mas o desenho de então não dava, e quebraria em
qualquer ferramenta. Três defeitos, todos confirmados no código:

1. O lote vivia em `st.session_state`. Cada aba abria o **seu próprio** grupo
   de processos, então cinco pessoas viravam dez análises disputando o mesmo
   modelo de visão, que é um servidor só. Fechar a aba deixava o lote órfão.
2. O estado da conta do Instagram, o mapa de números de perfil e o registro de
   análises eram gravados em ciclo de ler, alterar e gravar **sem trava**.
   Medido em 29/08 com seis processos: **48% das gravações se perdiam**. O que
   se perde ali é o contador de chamadas e a pausa do Instagram, ou seja, o
   freio deixa de valer sem erro nenhum na tela.
3. Não há login, e o token do Google no servidor é pessoal, então toda escrita
   aparece como sendo de uma pessoa só. Isso continua em aberto.

### O que foi feito

Arquivos novos:

| Arquivo | Para que serve |
|---|---|
| `trava.py` | trava de arquivo entre processos, Windows e Linux, sem biblioteca de fora |
| `fila_trabalho.py` | fila em disco, uma pasta por situação, um arquivo por tarefa |
| `trabalhador.py` | o único processo que baixa e analisa |
| `painel_trabalhador.py` | bloco de tela que avisa se o trabalhador está de pé |
| `iniciar_trabalhador.bat` | atalho para subir o trabalhador |

Agora são **dois programas**: a tela (`streamlit run painel.py`) e o
trabalhador (`py trabalhador.py`). Os dois precisam estar de pé. Se o
trabalhador não estiver, a tela avisa em vermelho.

### Descobertas do dia, medidas

- **Sem trava, 115 de 240 gravações concorrentes se perderam (48%). Com trava,
  nenhuma.** Teste com 6 processos.
- **No Windows, `os.replace` falha com "acesso negado"** quando outro processo
  está com o arquivo de destino aberto, mesmo só para ler. No Linux não
  acontece. Apareceu no primeiro teste. Tratado em `trava.substituir` e
  `trava.ler_insistindo`, usados no registro de análises e nos arquivos de
  tarefa.

### O que já foi testado

- Trava: 6 processos, 240 gravações, nenhuma perdida.
- Fila: 5 processos disputando 30 tarefas, nenhuma pega duas vezes, nenhuma
  perdida. Ciclo de concluir, falhar, reenfileirar e recuperar órfã.
- Trabalhador: sobe, dá sinal de vida, encerra sem cortar trabalho.
- Importação cruzada de todos os módulos, com as 469 análises guardadas
  intactas e o estado da conta legível.

### O que NÃO foi testado ainda

**O ciclo completo de ponta a ponta com a nova arquitetura.** Nenhum vídeo de
verdade passou pelo trabalhador. É o próximo passo: subir o trabalhador,
reiniciar o Streamlit e mandar analisar a linha 7 (a que está com `SEM ACESSO
À PASTA`, veredito antigo).

### Cuidados que mudaram

- **Reiniciar o Streamlit não basta mais.** Alterar código exige encerrar o
  trabalhador também, pelo botão em Manutenção no fim da tela de Downloads.
- `processar_lote_cli.py` está **travado de propósito**: escrevia na planilha
  antiga e concorria com o trabalhador. Só roda com
  `--sei-que-esta-desatualizado`.
- O teto de produção **não mudou**: um trabalhador, duas análises ao mesmo
  tempo, cerca de 33 vídeos por hora somando todo mundo. Cinco pessoas não
  produzem cinco vezes mais.

### Desempenho: o que foi medido em 29/08 (e o que caiu por terra)

A máquina é um **i5-1335U**, processador de notebook de 15W, 15,7 GB, gráficos
Intel integrados e **sem placa de vídeo dedicada**. O `minicpm-v` (7,6B, Q4)
roda inteiro em CPU, a 7,4 tokens por segundo no processamento da imagem.

**O custo do modelo de visão é POR IMAGEM, não por pergunta:**

| Chamada no mesmo quadro | Tempo |
|---|---|
| 1ª pergunta | 73,0s |
| 2ª a 5ª pergunta | 3,6 a 4,8s cada |

Duas hipóteses minhas caíram na medição: o modelo **não** gera resposta longa
(responde em 2 tokens, limitar não muda nada) e reduzir o número de perguntas
quase não adianta. **Reduzir o número de imagens distintas é que adianta.**

**O tamanho da imagem manda, em degraus:**

| Largura enviada | Tokens | Tempo |
|---|---|---|
| 1080 | 658 | 119,8s |
| **768 (hoje)** | **525** | **92,9s** |
| 640 | 327 | 56,1s |
| 512 | 260 | 43,0s |
| 448 e abaixo | 260 | ~43s |

**Mas encolher o quadro inteiro perde o texto miúdo**, que é justamente o que a
visão foi chamada para achar. Em quadro difícil sintético (rodapé corpo 22,
cinza sobre cinza), o 768 de hoje respondeu NÃO para um aviso que estava lá.
**Recortar a faixa do rodapé acertou e ainda foi 40% mais rápido** (61,1s
contra 101,5s). Um quadro sintético só, precisa ser repetido em quadros reais.

### Correção aplicada em 29/08: filtro por data nas perguntas de visão

A lista de perguntas em `analisar_visual` trazia os 5 elementos sem olhar a
data, mas a portaria **substitui** um aviso pelo outro em 17/07/2026, não
acumula. Uma pergunta era sempre jogada fora.

Como o custo é por imagem, num post em que o OCR leu tudo o que a data exige, o
aviso que ela **não** exige era o único item faltando e sozinho disparava os
73s inteiros, para produzir uma observação que a classificação descarta.

Medido depois da correção, com peça atual em conformidade:

| Regime | Perguntas à visão | Tempo |
|---|---|---|
| **Post atual (a partir de 17/07/2026)** | **nenhuma** | **1,1s** |
| Post antigo (antes de 17/07) | `extra`, que é exigida | 30,4s |
| Post sem data na planilha | nenhuma | 1,0s |

Antes da correção o post atual perguntaria `extra` do mesmo jeito, ou seja,
pagaria os 73s. **Post conforme passa a não chamar a visão nenhuma vez.**

**Importante para daqui pra frente:** a auditoria de vídeos antigos acabou. O
programa passa a analisar **vídeos atuais**, então o exigido é 18+, portaria,
#publi e a **frase do Ministério da Fazenda**. "Jogue com responsabilidade" não
é mais exigido, e é ele a pergunta que a correção acima elimina.

### Onde o tempo vai, medido etapa por etapa em 29/08

Um vídeo de 37,2s **sem conteúdo de aposta**, sozinho na máquina, com o modelo
já carregado e o reaproveitamento do Ollama limpo: **240,7s**.

| Etapa | Tempo | Fatia |
|---|---|---|
| Modelo de visão (6 perguntas) | 117,5s | 49% |
| Transcrição do áudio | 59,8s | 25% |
| EasyOCR (3 quadros) | 39,5s | 16% |
| Baixar do Drive | 12,9s | 5% |
| RapidOCR (3 quadros) | 7,3s | 3% |
| Tesseract (3 quadros) | 2,3s | 1% |

Da visão, **a primeira pergunta sozinha custou 91,0s** e as outras cinco
somaram 26,5s. O áudio custa **1,6x a duração do vídeo**.

**Vídeo sem nada de aposta é o PIOR caso do programa**, não o mais leve: nenhum
atalho funciona, a escada de OCR sobe até o fim, a visão recebe todas as
perguntas e o áudio é transcrito. É também o caso de "baixei errado".

**Cuidado ao medir o modelo de visão:** o Ollama guarda o processamento de
imagens já vistas, e de mais de uma por vez. Duas medições minhas saíram
erradas por isso (130s e 147s onde o certo era 240s). Para número limpo é
preciso derrubar o processo `llama-server` e recarregar o modelo com uma
pergunta sem imagem antes de cronometrar.

**E o "81% é visão" de 28/08 não vale mais:** aquela medição foi com a checagem
de criança ligada. Hoje a visão é 49%.

### Corrigido em 29/08: os quadros vinham todos do primeiro 0,7s

`extract_frames` pedia 3 quadros por segundo e ficava com os 3 primeiros. Agora
tira um quadro no meio de cada fatia do vídeo: num vídeo de 30s com 3 quadros,
sai um aos 5s, um aos 15s e um aos 25s.

**Não era só desperdício, era acusação indevida.** Aviso obrigatório que
aparecesse depois do primeiro segundo não era encontrado, e a peça ia para NÃO
CONFORME por falta de um aviso que estava lá. A correção anda na direção
segura. O custo é o mesmo: continuam três quadros e três leituras.

Existe `QUADROS_POR_VIDEO` para subir o número. Cada quadro a mais custa cerca
de 13s de EasyOCR no pior caso e **nada** no caso conforme, porque a escada
para assim que acha tudo o que a data exige.

### Próximos passos de desempenho, em ordem

1. **Placa de vídeo no servidor.** É a única coisa que muda a ordem de
   grandeza. Medido 7,4 tokens/s aqui; uma placa modesta fica na casa dos
   milhares. Estimativa, não medição: não há placa aqui para medir.
2. **Recorte da faixa em vez de encolher o quadro.** Medido 40% mais rápido e
   mais preciso, pendente de validação com quadros reais que tenham a frase do
   Ministério da Fazenda em corpo pequeno.
3. **Remedir o tempo por linha na arquitetura nova.** Os 110s por vídeo foram
   medidos com link de PASTA, média de 2,5 arquivos por linha, e cada arquivo
   paga um processamento de imagem próprio. Agora a coluna X aponta para um
   arquivo só, então o número já deve ter caído sem ninguém mexer em nada.

### Ainda em aberto da conversa sobre robustez

- ~~**Login**~~ **FEITO em 31/08/2026**, e funcionando com conta Google na
  máquina de trabalho. As tarefas passaram a gravar o e-mail verificado de quem
  pediu, no lugar do usuário do computador, sem mexer em mais nada, como estava
  previsto. Ver a seção "O QUE MUDOU EM 31/08, À NOITE".
- **Conta de serviço** no lugar do token pessoal. Reduz escopo, mas não
  substitui o login: quem fez o quê tem que vir do registro do app.

---

## Quem sou e o que estamos construindo

Sou auditor interno da EGB (Esportes da Sorte, Onabet, Lottu). Estamos
construindo um programa em Streamlit que cobre o ciclo da auditoria de
publicidade de influenciadores, em duas partes:

1. **Downloads**: baixa o material publicado, organiza no Drive e registra na
   planilha de Monitoramento.
2. **Validação Regulatória**: confere automaticamente se cada peça traz os
   avisos obrigatórios e devolve o veredito na mesma planilha.

Vamos subir isso num servidor para 5 pessoas do Marketing usarem, **na semana
de 01/09/2026**.

---

## REGRAS QUE NÃO PODEM SER QUEBRADAS

- **Nunca escrever na Monitoramento real do Marketing**
  (`13uLhupENDl6bSHfRioaQz0mcZUio_IOojp1_c1CFhQU`). Ler é permitido e já foi
  feito com autorização. Toda escrita vai para a **cópia de teste**.
- **Nunca apagar arquivo do Drive de forma permanente.** Usar sempre a lixeira
  (`files().update(trashed=True)`). Em 26/08 dois arquivos foram apagados de vez
  com `files().delete()` e não houve como recuperar.
- **Não editar arquivo nenhum enquanto um lote estiver rodando.** Já aconteceu.
  Desde 29/08 quem roda é o trabalhador, então o jeito certo é encerrar ele
  antes, pelo botão em Manutenção no fim da tela de Downloads. Conferir com
  `Get-CimInstance Win32_Process` procurando `trabalhador` ou `spawn_main`.
- **O recarregamento automático do Streamlit está desligado de propósito**
  (`fileWatcherType = none`). Toda alteração de código exige **reiniciar o app**.
- **Nunca colar dados pessoais de apostadores**, credenciais, tokens ou cookies
  na conversa.
- **Nunca desligar a verificação de certificado** para fazer alguma conexão
  funcionar. A rede da empresa inspeciona o tráfego HTTPS, e desligar abriria
  de verdade a brecha que a revisão de segurança de 28/08 concluiu não existir
  neste programa. Quando o disfarce de navegador falha por certificado, o
  programa RECUA sozinho e segue sem ele (ver `opcoes_de_disfarce`).
- **Não subir o teto do Instagram sem a semana de observação.** Cada etapa
  precisa de uma semana limpa antes da próxima. O raciocínio inteiro está em
  `LIMITE_DIARIO_INSTAGRAM`. Subir "só para ver" desfaz a única evidência que
  existe de que o programa é disciplinado.
- **Nunca abrir a tela para a rede antes de o login existir.** Atrás dela
  estão as credenciais do Google, de escopo amplo, e a conta do Instagram. O
  programa trava sozinho se detectar essa combinação, mas isso é o plano B, e
  não o procedimento.

---

## Como rodar

São dois programas desde 29/08, e os dois precisam estar de pé.

```
cd C:\Users\auditor\Documents\Auditoria\producao\analises

py trabalhador.py                              (janela 1, deixe aberta)
py -m streamlit run painel.py --server.port 8501   (janela 2)
```

Abre em `http://localhost:8501`, com três abas: **Downloads**, **Validação
Regulatória**, **Monitoramento**. O `painel.py` é só o roteador que dá nome às
abas; a configuração de página mora só nele.

Se o trabalhador não estiver de pé, a tela avisa em vermelho e o que for
pedido fica esperando na fila até alguém subir ele.

---

## Identificadores

| O quê | Identificador |
|---|---|
| Monitoramento **TESTE** (onde escrevemos) | `1T4xV2oSDoae6Ahe4nNLIoI2CrqpZtZtmSRBna7y3fG0` |
| Monitoramento **REAL** (só leitura) | `13uLhupENDl6bSHfRioaQz0mcZUio_IOojp1_c1CFhQU` |
| Fila de downloads (teste) | `1uYOFMlB53l02uifgVFkFrxVm_EChUPkC_WOOd7IaRA8` |
| Planilha antiga de validação (**fora do fluxo**) | `1Uzxi3K1o6Nq7bgUhLZNBIYm5Qw7hD9Y7FOtLxr4-V9w` |
| Drive de teste (raiz) | `1JjS57THuerSw0YnlsprkIOAbSqKxOoxT` |
| Drive do Marketing (VÍDEOS INFLUENCIADORES) | `1_tKB4uZsscPdzhKH8Oi9SNb1hiriwEt0` |

Os identificadores de planilha e da raiz do Drive **vêm de arquivos** em
`teste_watch_folder/`, não do código. Trocar de destino é trocar o conteúdo
desses arquivos.

---

## Arquitetura atual (decidida em 28/08)

A planilha antiga de validação **saiu do fluxo**. A **Monitoramento é a fonte
única**:

```
link do post → baixa → sobe pro Drive → grava a linha na Monitoramento
   → a SITUACAO da linha é o gatilho → validação pega a linha
   → veredito volta pra MESMA planilha
```

### Bloco de colunas da automação (só a automação escreve)

CORRIGIDO EM 31/08/2026, conferindo contra a planilha de teste e contra
`COL_MON` em `fluxo_downloads.py`. Esta tabela dizia W até AB e incluía a coluna
LINK_ARQUIVO, que saiu em 29/08. Todas as letras depois de W estavam erradas em
uma casa, e quem seguisse a tabela escreveria na coluna vizinha. São **cinco
colunas, de W a AA**:

| Coluna | Título | Conteúdo |
|---|---|---|
| W | DATA_DOWNLOAD | quando o material foi capturado (≠ data do post) |
| X | SITUACAO | `SEM ARQUIVO` / `AGUARDANDO VALIDAÇÃO` / `VALIDADO`. É daqui que sai a fila, desde que LINK_ARQUIVO saiu |
| Y | VALIDACAO | veredito, juntando texto e áudio na mesma coluna |
| Z | EVIDENCIA | o que faltou e em qual arquivo |
| AA | VALIDADO_EM | quando a análise rodou |

Conferido na planilha de teste em 31/08/2026: os títulos de W a AA estão
exatamente nessa ordem. E a Monitoramento REAL tem **22 colunas com título, A
até V**, então o bloco da automação não fica em cima de coluna nenhuma do
Marketing. Isso era suposição do desenho e passou a ser medição.

Colunas A a V são do Marketing: a automação **só lê**. Os títulos do bloco são
criados sozinhos e **nunca sobrescrevem** título existente.

A automação **só escreve em célula vazia**. Para reprocessar uma linha, apaga-se
a célula VALIDACAO dela.

---

## DECISÕES PENDENTES (travam o próximo passo)

Revisado em 30/08/2026. O que caiu está marcado, para ninguém reabrir discussão
já encerrada.

1. **O número do POST na planilha é o mesmo número da TELA no arquivo?**
   Isso permitiria casar uma linha da Monitoramento com o arquivo certo dentro
   da pasta do mês, para as linhas que o Marketing preenche à mão.
   **CONTINUA ABERTA**, e é pergunta para o Marketing.

2. ~~A estrutura de pastas passa a ser a do Marketing?~~
   **RESOLVIDA em 30/08**: sim, é a deles, e o programa passa a ENCONTRAR em
   vez de criar. Implementado e testado, mas dormente: depende de
   `LAYOUT_PASTAS_DRIVE=marketing` e da conta de serviço.

3. ~~Tirar a coluna X (LINK_ARQUIVO)~~
   **FEITA**, com `migrar_tirar_coluna_link_arquivo.py`.

4. **Regressão conhecida**: linhas que o Marketing preencheu à mão têm link de
   **pasta** e ficam fora da fila. Proposta aceita mas não implementada:
   procurar o arquivo dentro da pasta pela data do post e, se ficar ambíguo,
   marcar para conferência em vez de chutar. **CONTINUA ABERTA**, e depende da
   resposta do item 1.

5. **Qual notebook será o servidor**, e se dá para conseguir um melhor.
   **PARCIALMENTE RESOLVIDA em 31/08/2026**: é Windows, confirmado, e é mais
   robusta que o notebook do auditor. Falta a capacidade exata, principalmente
   se tem placa de vídeo dedicada. Ver o item 1 da lista do começo deste
   documento.

6. **Onde fica o repositório.** Por ora fica só na máquina do auditor, com
   cópia de segurança do histórico no Drive
   (`copiar_historico_para_o_drive.py`). Guardar código de auditoria interna em
   conta pessoal do GitHub passa por Segurança da Informação e pelo Jurídico.

---

## Estrutura de pastas do Marketing (mapeada em 28/08)

```
INFLUENCIADORES > VÍDEOS INFLUENCIADORES
  > 01. EDS | 02. ONA | 03. LOTTU | 04. EDSCAP
    > 2025 | 2026
      > 01. Janeiro ... 12. Dezembro
        > @influenciador
          > "DD/MM - bruto" (pastas) + vídeos soltos
```

- **266 influenciadores** distintos, e **105 aparecem em mais de uma bet**.
- Existe grafia duplicada (`@andreasantosof` e `@andreasantosof_`).
- **Consequência importante**: o link que o Marketing cola na planilha aponta
  para a **pasta do mês**, então o mesmo link em várias linhas **é o desenho
  deles, não erro**. Isso reinterpreta um achado nosso: dos 147 casos de link
  duplicado, os **126 de "mesmo influenciador reaproveitado" provavelmente não
  são erro**; os **17 de "influenciador diferente" continuam de pé**. O achado
  precisa ser refeito.

---

## Nomenclatura dos arquivos

Adotado o padrão do Marketing: **`DD/MM - @handle - tela N.mp4`**.

Isso não é estética: como o link aponta para a pasta do mês, **data e número de
tela no nome são a única forma de ligar uma linha da planilha ao arquivo**.

**A barra quebrou o programa três vezes no mesmo dia**, sempre pelo mesmo
motivo: no Drive é nome válido, no Windows é separador de pasta. Já existe
tratamento nos dois lugares que gravam em disco (`nome_para_disco` em
`fluxo_downloads.py`, `_nome_gravavel` em `pipeline_influenciadores.py`). **Se
aparecer um "caminho não encontrado" novo, suspeite disso primeiro.**

---

## Instagram: o que funciona e o que não funciona

### Descoberto em 28/08, com medição

- **Acesso anônimo morreu.** Página pública de perfil devolve só o esqueleto do
  aplicativo, sem o número. Post anônimo devolve "resposta de mídia vazia":
  medido em 16 links, **14 falharam**.
- **Com cookies funciona.** O mesmo link responde na hora. Ou seja, o contorno
  do "link de Reel" existe, mas **deixou de ser anônimo** e agora conta no teto
  diário.
- Baixar Story exige o **número interno do perfil**. Descobrir esse número, para
  quem ainda não tem, é o gargalo real: levou **429 com apenas 3 chamadas** numa
  conta nova.

### Freio (graduado desde 28/08)

| Sinal | Pausa |
|---|---|
| 429, "too many requests", "rate limit", "invalid request" | **1h**, dobrando a cada repetição no dia, até 24h |
| challenge, checkpoint, 401, unauthorized | **24h** |

Se o erro trouxer os dois, manda o severo. Existe `fluxo.liberar_conta()` para
tirar a pausa manualmente, **sem botão na tela de propósito**: um botão de
"ignorar bloqueio" convida ao clique por impaciência, que é o comportamento que
marcou duas contas em agosto.

**Falha de consulta de perfil não pausa mais a conta** (classe
`PerfilDesconhecido`): é falha de um influenciador, não da conta, e o endereço
que recusa é outro.

### Outros limites

- **20** chamadas por dia **por conta** (regra nossa, não do Instagram). Este
  item dizia 12 até 31/08/2026, o que contradizia a subida registrada em 30/08.
  O valor vigente está em `LIMITE_DIARIO_INSTAGRAM`, em `fluxo_downloads.py`,
  e é de lá que sai o número, não daqui.
- 3 links do Instagram por rodada, com pausa de 45 a 120s entre eles
- **Uma conta por dia por máquina**: a primeira conta que usar prende a máquina
  até o dia virar. Isso existe porque o contador era por conta e trocar de conta
  o zerava sem querer.
- A fila **não tem limite**: pode enfileirar quantos quiser, o programa
  distribui.

---

## FASE DE TESTES: o que usar

### Perfis com número guardado (Story baixa direto, sem consultar nada)

```
@dendele_fc
@dudafreiret
@feijhonys
@jojotodynho
@lomma
@recifeordinario
@ruivinhademarte
@wandre.rochaa
```

**DESATUALIZADO DESDE 29/08, e a ressalva importa.** Aquela lista existia
porque o Story passava pelo instaloader, que precisa do número do perfil.
Desde 29/08 o caminho principal é o yt-dlp, que **não precisa do número**, e
qualquer influenciador com story no ar funciona. A lista só vale para o
caminho de reserva, que roda quando o principal falha.

Influenciadores usados nos testes de 30/08, todos com download bem-sucedido:
@dudafreiret, @cassinha.161, @leosantana, @calema507, @juremafox, @lomma,
@bahiadohype, @astrox.ofc, @luquet4, @rachaxp, @miltinhooalves, @jojotodynho.
O @kevinho falhou, e falhou justamente por cair no caminho de reserva.

### Conta em uso

- `USUARIO_DOS_COOKIES = "candyboxconfeitaria"` — **conta descartável**, o
  usuário não a utiliza para mais nada. Bloqueio nela não tem importância.
- **A sessão vem do Firefox aberto**, e não mais do arquivo de cookies. O
  arquivo é uma fotografia que envelhece sozinha; a sessão viva não. O
  navegador configurado é o Firefox porque é o único cuja sessão dá para ler.
  Num servidor não há navegador, e lá o programa cai no arquivo, o que deixa
  uma manutenção recorrente registrada para o procedimento de lá.
- **O nome no código PRECISA bater com a conta dos cookies.** Se não bater, a
  biblioteca trata a sessão como anônima **sem avisar**, e os limites ficam bem
  mais duros. Foi o que provavelmente causou o primeiro bloqueio.

### Situação da conta em 30/08 ao fim do dia

- Teto subiu de 12 para **20**, primeira etapa de uma subida medida.
- 8 de 20 usadas no caminho do servidor, sem pausa ativa.
- Baixador local: 4 no dia, teto também em 20 (estava sem teto nenhum).
- Uso por dia, do registro: 21/08 → 5, 24/08 → 4, **25/08 → 34**, 26/08 → 15,
  27/08 → 10, 28/08 → 9, 29/08 → 7, 30/08 → 8.
- **O dia 25 não foram 34 downloads.** Foram 34 chamadas, das quais só 10
  deram certo; 24 falharam, boa parte repetindo em cima de perfil sem story no
  ar, e três na consulta por @. Não foi volume, foi insistência num endereço
  sensível. Quem for reavaliar o teto precisa saber disso, senão conclui a
  coisa errada olhando só o número.

---

## Desempenho da análise (medido em 28/08)

> ATENÇÃO, SEÇÃO SUPERADA EM PARTE. Marcado em 31/08/2026 porque dois números
> daqui foram derrubados por medição de 29/08, mais acima neste arquivo, e quem
> abrisse direto nesta seção concluiria errado:
>
> 1. **"O modelo de visão é 81% do tempo" não vale mais.** Aquela medição foi
>    com a checagem de aparição de criança ligada. Desligada, a visão é 49%.
> 2. **O defeito do `extract_frames` foi CORRIGIDO em 29/08.** O texto no fim
>    desta seção o descreve como conhecido e não corrigido, e não é mais o caso:
>    os quadros são espalhados pelo vídeo.
>
> O resto da seção continua valendo.

| Configuração | Por vídeo |
|---|---|
| 1 análise por vez | 185s |
| **2 ao mesmo tempo** | **110s** (1,68x) |
| 3 ao mesmo tempo | 107 a 129s (sem ganho) |

Fixo em **2**, sem campo na tela: não é decisão de quem usa, é característica da
máquina.

**O modelo de visão é 81% do tempo.** OCR, áudio e ffmpeg somam 18,9%, então
qualquer otimização de OCR tem teto baixo. O modelo roda num **servidor único
compartilhado**, e é por isso que mais processos param de ajudar.

Ganhos já aplicados: redução da imagem enviada à visão (5,8x na etapa, respostas
idênticas) e **retirada da checagem de aparição de criança** (era 50,3% do tempo
e nunca gerou um alerta em 445 linhas). A coluna dela agora diz **"não
verificado"** em vez de ficar vazia, porque vazio seria lido como "conferido e
sem criança". Religar é trocar `CHECAR_CRIANCA_VISUAL` para `True`.

### Escada de OCR (três degraus, do mais rápido ao mais demorado)

| Degrau | Tempo/quadro | Por que existe |
|---|---|---|
| Tesseract | 1,5s | resolve banner nítido |
| RapidOCR | 5,9s | melhor em 18+, portaria e #publi (22 contra 4) |
| EasyOCR | 11,3s | único bom no "jogue com responsabilidade" miúdo |

Depois vem a visão local (Ollama, `minicpm-v`), só para o que faltar.

**~~Defeito conhecido e não corrigido:~~ CORRIGIDO EM 29/08/2026.** O texto
original fica como registro do que era: `extract_frames` usava `fps=3` e pegava
os 3 primeiros quadros, então todos saíam do primeiro 0,7 segundo do vídeo, e
mais de 98% de um vídeo de 60s nunca era analisado. Hoje sai um quadro no meio
de cada fatia do vídeo. Ver "Corrigido em 29/08: os quadros vinham todos do
primeiro 0,7s", mais acima. Consequência que continua valendo: **análise feita
antes de 29/08 não vale**, porque podia acusar falta de aviso que estava no
vídeo depois do primeiro segundo.

---

## Regra de ouro da classificação

**Só o texto lido conta como prova.** A visão local já alucinou um "18+" numa
imagem que era print de conversa. Quando ela sugere algo que nenhum OCR
confirmou, o post vai para **Requer Verificação**, nunca para Conforme.

Classificações: `Conforme` / `Não Conforme` / `Requer Verificação`.

Elementos exigidos: 18+, menção à portaria, #publi sempre; **"jogue com
responsabilidade"** antes de 17/07/2026; **frase do Ministério da Fazenda** a
partir dessa data (substitui, não acumula).

### A RÉGUA DA LEGIBILIDADE, decidida pelo auditor em 02/09/2026

Palavras dele, e valem para TODOS os itens exigidos, não só para o publi:

> "se estiver na tela, ainda que pequeno, É OK; se não estiver na tela, é
> problema"

Ou seja: **o critério é PRESENÇA, não perceptibilidade.** Item pequeno, de baixo
contraste ou meio ilegível, mas presente na tela, é CONFORME naquele item, e a
conferência segue para os outros. Item ausente da tela é achado, e faltar
QUALQUER um dos exigidos torna a peça Não Conforme.

O QUE ISSO ENCERRA: a pergunta que estava aberta sobre um aviso ilegível poder
ser considerado ostensivo. Não é critério. O auditor decidiu, e a razão dele:
parte da ilegibilidade vem da captura, não da peça, e o que importa é a
ferramenta conseguir capturar o que está na tela.

O QUE ISSO **NÃO** RESOLVE, e é a parte que fica: o programa continua sem
conseguir distinguir "está na tela e o OCR não leu" de "não está na tela". Os
dois casos chegam nele idênticos. Então o caso indeciso continua saindo como
**Requer Verificação**, e agora com a pergunta na forma exata que a régua pede:
está na tela, sim ou não. Quem responde é olho humano.

**CONFIRMADO PELO AUDITOR na mesma conversa**, depois de ele mesmo levantar e
descartar a hipótese contrária. Ele perguntou se "muito pequeno" poderia virar
Não Conforme, já que nesse caso nem o OCR nem a visão pegam, e concluiu:

> "se ele ficar na dúvida deve continuar como REQUER ANÁLISE"

POR QUE A HIPÓTESE CONTRÁRIA NÃO FECHA, e vale registrar porque ela é tentadora:
"não detectado" não implica "pequeno". Tem pelo menos sete causas, e DUAS JÁ
ACONTECERAM NESTE PROJETO, as duas com o aviso presente e em tamanho normal:

  - os quadros saíam todos do primeiro 0,7 segundo do vídeo (corrigido em
    29/08/2026), então banner que aparecia depois era invisível
  - o Tesseract lia português com modelo de inglês (corrigido em 30/08/2026), e
    duas das três frases do Ministério da Fazenda eram invisíveis

Se a regra fosse "não detectou, logo é pequeno, logo Não Conforme", nas duas
épocas o programa teria produzido uma onda de achado falso, contra influenciador
e contra o Marketing, dentro de relatório de auditoria. As outras causas
conhecidas: baixo contraste, movimento e compressão, oclusão por outro elemento
da tela, item gráfico em vez de texto (o selo 18+), e o próprio limite do OCR.

E O CASO DO @andersonneiff NÃO ERA DE TAMANHO, o que o auditor esclareceu em
seguida: o rodapé estava "consideravelmente legível", e o OCR leu CINCO itens
naquele clipe (18+, portaria, jogue com responsabilidade, Ministério da Fazenda e
conteúdo de aposta). **O publi não foi lido porque não estava lá.**

Isso derrubou a segunda versão da frase, escrita na mesma manhã: ela dizia
"(texto pequeno ou baixo contraste)" como explicação de por que o item não foi
lido. Ou seja, a correção da manhã trocou uma frase que ESCONDIA o achado por
outra que AFIRMAVA causa desconhecida. Mesmo defeito de fundo, a ferramenta
dizendo mais do que sabe, duas vezes no mesmo trecho no mesmo dia.

A frase agora diz só fato, e termina na pergunta que a régua pede:

> publi (identificação de publicidade): NÃO CONFIRMADO por nenhum motor de OCR, e
> a IA de visão sugere que está presente. A sugestão não confirma nem crava
> ausência, e o programa NÃO sabe a causa de não ter lido. Neste mesmo clipe o
> OCR leu: 18+, portaria, jogue com responsabilidade, Ministério da Fazenda,
> conteúdo de aposta. Precisa de conferência humana: está na tela?

A lista do que o OCR LEU no mesmo clipe é a parte que permite a quem confere
julgar sozinho: se o OCR leu cinco itens ali, "não deu para ler" perde força como
explicação. Coberto por `teste_ordem_da_frase_do_veredito.py`, que agora proíbe a
frase de afirmar causa.

O QUE TORNARIA A PERGUNTA RESPONDÍVEL POR MEDIÇÃO, e não por suposição: guardar,
quando a visão sugere presença e o OCR não confirma, as propriedades medíveis do
quadro, como altura do texto detectado em relação ao quadro e contraste. Hoje o
programa guarda só "não foi lido" e a lista do que leu. Com os números, "muito
pequeno" deixa de ser suposição e vira fato. NÃO ESTÁ FEITO.

E FICA UM DADO SOBRE A IA DE VISÃO, que vale para quem for confiar nela: ela tem
**falso positivo confirmado no publi**, neste caso do @andersonneiff, num clipe
em que o OCR estava funcionando bem. Já havia o outro registrado, o "18+"
confirmado numa imagem que era print de conversa. Duas alucinações confirmadas,
as duas em itens que precisam estar escritos.

MEDIDO EM 02/09/2026: das 44 entradas do cache, 10 dependem de uma sugestão da
IA de visão, e 8 delas são sobre o publi. São essas que esperam a resposta.

FALTA NA FERRAMENTA, e é o que torna a régua operável: não existe como registrar
"conferi, está na tela, item conforme". A tela de Validação tem "Mandar
analisar", "Tirar da análise", "Tirar da fila" e "Devolver para a análise". Hoje
a única forma de registrar a conferência é digitar na planilha à mão, o que perde
o rastro de quem conferiu e quando.

E UMA HIPÓTESE DELE JÁ ESTAVA MEDIDA E DESCARTADA: a ilegibilidade não vem da
qualidade do nosso download. O programa pede `format: "best"` nos dois caminhos,
e a medição de 30/08/2026 com 54 vídeos mostrou que o Instagram entrega um
formato só, 720x1280, igual pelo servidor e pelo baixador local.

---

## Segurança (levantado em 28/08 com o colega de cibersegurança)

- **Não há falha de man in the middle no código.** Nenhum `verify=False`,
  `CERT_NONE` ou substituição de autoridade certificadora. As chamadas ao Google
  usam a biblioteca oficial, com validação de certificado.
- **O risco real são as credenciais em texto puro**: três tokens do Google com
  `refresh_token` e `client_secret`, sendo dois de escopo amplo
  (`drive.readonly` e `spreadsheets`, que alcançam tudo que a conta enxerga), e
  os cookies do Instagram.
- **Não existe `.gitignore` e a pasta não é repositório.** No dia que virar, os
  segredos vão junto.
- **Correção de fundo recomendada**: trocar token de usuário por **conta de
  serviço**, compartilhando com ela apenas as pastas e planilhas específicas.
- A extensão de cookies instalada (`Get cookies.txt LOCALLY`) é a de código
  aberto, a de menor risco. O **Tampermonkey** que existia em dois perfis foi
  **removido pelo usuário** em 28/08.
- Recomendação em aberto: **perfil de navegador dedicado** só para o Instagram
  do trabalho, sem sistema corporativo logado.

Tudo isso é **análise sujeita a validação pela Segurança da Informação e pelo
Jurídico**, não declaração de conformidade.

---

## Pendências combinadas

Revisado em 30/08/2026. O que caiu fica marcado, para ninguém reabrir.

1. ~~Tirar a coluna X (LINK_ARQUIVO), redundante.~~ **FEITA.**
2. Resolver a regressão das linhas com link de pasta. **ABERTA**, depende da
   resposta sobre POST e TELA.
3. ~~Decidir o layout de pastas.~~ **DECIDIDO**: o do Marketing, encontrando
   pasta em vez de criando. Dormente até a conta de serviço.
4. ~~Decidir a amostragem de quadros.~~ **FEITA em 29/08**: os quadros são
   espalhados pelo vídeo. Antes saíam todos do primeiro 0,7 segundo.
5. ~~Atualizar o checklist de subida.~~ **FEITO em 30/08**, versão 2, publicada
   também como página em
   `https://claude.ai/code/artifact/381d4d92-8638-494d-aae5-79b3b4534330`.
6. Avaliar resolver os ~260 números de perfil em lote com a conta descartável.
   **PERDEU BOA PARTE DO SENTIDO**: desde 29/08 o Story vem pelo yt-dlp, que
   não precisa do número. Só serve para o caminho de reserva. A ressalva
   original continua valendo se alguém retomar: o risco não é só da conta, o
   Instagram também marca por endereço de rede, e isso pode respingar nas
   contas reais.

7. **Guardar o histórico diário do contador da conta** (anotado em 31/08/2026,
   a pedido do auditor, para fazer depois).

   Hoje `estado_conta_instagram.json` guarda SÓ o dia corrente e sobrescreve na
   virada: o "usados: 8" de hoje desaparece amanhã. O histórico existe apenas
   indiretamente, no `log_fluxo_completo.csv`, e foi de lá que saíram os números
   de uso por dia usados nas decisões de 30 e 31/08.

   Dois problemas com depender do CSV:

   a) ele registra só o que passou pela fila do programa. Chamada feita por
      fora não aparece, e isso JÁ ACONTECEU: em 29/08 vários testes chamaram o
      mecanismo direto, por fora do contador, e o consumo real do dia foi maior
      que o registrado.

   b) contador e CSV podem divergir, e quando divergem não há como saber qual
      está certo.

   Proposta: uma linha por dia por conta, em CSV, escrita pelo próprio
   contador. Custa quase nada, responde "quanto essa conta usou na terça
   passada" sem reconstruir, e faz os dois se conferirem.

   POR QUE IMPORTA MAIS QUE PARECE: é essa a evidência que protege a ferramenta
   se uma conta for bloqueada. A extensão que eles usam hoje não deixa rastro
   nenhum, e o Marketing já perdeu uma conta com ela. O contador já guarda o
   bloqueio quando acontece, com a mensagem do Instagram e a hora, e existe um
   registrado hoje para a conta chico45235.

8. ~~**Escolher QUAIS vídeos mandar analisar, e tirar vídeo baixado por
   engano.**~~ **AS DUAS FEITAS EM 29 e 30/08.** A tela tem tabela com seleção
   por linha (`on_select="rerun"`), e existe "Tirar da análise" com motivo, que
   escreve na coluna VALIDACAO e deixa registro em vez de sumir com a linha. O
   texto abaixo fica como registro do raciocínio, que continua valendo se
   alguém for mexer nessa parte.

   (levantado pelo usuário em 29/08, durante o teste)

   O problema: uma vez baixado, o vídeo entra na lista de pendentes da
   Validação e não sai mais de lá até receber um veredito. Não existe como
   dizer "esse não deve ser analisado". Caso real do teste: havia 3 vídeos de
   ontem e 2 de hoje, e a intenção era analisar só os 2 de hoje.

   Piora porque a tela só pergunta **quantos** analisar e pega os primeiros da
   lista, sem deixar escolher quais.

   São duas necessidades diferentes, e convém não misturar:

   a) **Escolher quais mandar.** Trocar o campo "quantos vídeos" por uma
      tabela com seleção, mostrando influenciador, data, tipo e link. É a
      mudança mais simples e não mexe em dado nenhum, só em qual tarefa é
      criada. Resolve o caso "quero só os 2 de hoje".

   b) **Tirar da lista de vez o que foi baixado por engano.** Precisa deixar
      registro, não sumir com a linha em silêncio: numa ferramenta de
      auditoria, material que entrou e saiu tem que ter motivo, quem tirou e
      quando. Proposta: escrever na coluna VALIDACAO algo como
      `FORA DA ANÁLISE (baixado por engano)`, com quem e quando na EVIDENCIA.
      A linha sai da fila sozinha, porque a automação só escreve em célula
      vazia, e volta se alguém apagar a célula.

      Se o caso for tirar o arquivo também, reaproveitar o caminho que já
      existe em `remover_material_de_teste`, que manda para a **lixeira** do
      Drive, nunca exclusão permanente. Hoje essa função só funciona por
      influenciador inteiro, precisaria funcionar por vídeo.

   **Enquanto não é feito**, o contorno é escrever qualquer coisa na célula
   VALIDACAO das linhas que não devem entrar. Elas somem da lista de pendentes
   na hora, e voltam se a célula for apagada.

9. ~~**A tela conta errado quantos estão sendo analisados.**~~ **CORRIGIDO**,
   está em `app_validacao_influenciadores.py:412`. O texto fica porque explica
   um comportamento do trabalhador que não é óbvio e que vai confundir de novo
   quem olhar a fila.

   (achado em 29/08 ao olhar a fila durante o teste). Ela mostrava 3, mas só 2
   estavam de fato em análise: o trabalhador entrega uma tarefa a mais ao grupo
   de processos para nenhum deles ficar parado esperando a próxima volta do
   laço (`ANALISES_ENTREGUES = TRABALHADORES_PADRAO + 1`).

   Isto é uma **regressão minha**: a versão antiga tinha essa correção e o
   motivo estava escrito no código. Ao mudar o acompanhamento para ler da fila
   em disco, o limite se perdeu. Corrigir é mostrar
   `min(len(em_analise), pipeline.TRABALHADORES_PADRAO)` em
   `app_validacao_influenciadores.py`, e contar o resto como esperando.
   Não afeta a análise, só o número na tela.

---

## Como eu gosto de trabalhar

- **Português do Brasil**, conclusão primeiro.
- **Sem travessão** em texto de metodologia, observação ou recomendação.
- **Sem jargão** em texto que aparece na tela ou em planilha.
- **Medir antes de afirmar.** Já houve três estimativas erradas seguidas neste
  projeto por não medir.
- **Corrigir-se explicitamente** quando um teste derrubar uma afirmação anterior.
- **Documentar no próprio código** o porquê das decisões, com data, para não
  serem desfeitas por engano depois.
- **Citar a fonte de cada número** e dizer quando algo não foi verificado.
- Para validar números da auditoria, usar o agente `verificador-auditoria`, que
  é somente leitura.

---

## Arquivos do projeto

```
producao/analises/
  painel.py                        roteador das abas
  estilo.py                        identidade visual (design system do EGB)
  .streamlit/config.toml           tema e ajustes do Streamlit
  fluxo_downloads.py               motor de download e organização
  pipeline_influenciadores.py      orquestração da análise
  validar_avisos_portaria136.py    motor de análise (OCR, visão, áudio)
  app_validacao_influenciadores.py aba Validação Regulatória
  pages/1_Downloads_e_Organizacao.py
  pages/2_Monitoramento.py
  trabalhador.py                   quem baixa e analisa de verdade (29/08)
  fila_trabalho.py                 fila de tarefas em disco (29/08)
  trava.py                         trava de arquivo entre processos (29/08)
  painel_trabalhador.py            bloco de tela com a situação dele (29/08)
  iniciar_trabalhador.bat          atalho para subir o trabalhador (29/08)
  processar_lote_cli.py            DESATUALIZADO e travado desde 29/08
  README.md                        documentação completa
  _drive_credenciais/              clientes e tokens do Google
  teste_watch_folder/              estado, cookies, identificadores, log
    fila_trabalho/                 as tarefas, uma pasta por situação (29/08)
```

Há também uma página publicada com o README:
https://claude.ai/code/artifact/abe82f80-9a77-4fb7-812f-dbcf9ca2d10f
