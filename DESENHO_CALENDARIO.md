# Ligar o programa ao Calendário Geral de Divulgações

**Versão 3 · 11/09/2026.** Desenho aprovado pelo auditor e **implementado no
mesmo dia**. A versão 3 acrescenta a leitura de volta, o cronograma do ciclo no
texto do Financeiro (última seção). O plano de execução, com o que foi feito
tarefa por tarefa, está em [PLANO_CALENDARIO.md](PLANO_CALENDARIO.md).

O que existe no código, e onde:

| parte | onde |
|---|---|
| normalizar, achar a aba, achar a linha, ler e escrever | `calendario_divulgacoes.py` |
| ler as linhas do ciclo de um influenciador | `calendario_divulgacoes.linhas_do_influenciador` |
| de quando até quando vai o ciclo | `fluxo_downloads.janela_do_ciclo` |
| juntar o Calendário com o que foi baixado | `escopo_e_entrega.montar_cronograma` |
| a hora do post, que antes era descartada | `fluxo_downloads.hora_de_brasilia` |
| escrever depois do download | `fluxo_downloads.registrar_no_calendario` |
| marcar quem não postou | `fluxo_downloads.marcar_nao_postou` |
| campo Jogo e seção de não postou | `pages/1_Downloads_e_Organizacao.py` |
| o cronograma na tela e no texto | `pages/3_Financeiro.py` |
| qual Calendário está valendo | `verificar_ambiente.py` |

Cópia de teste criada em 11/09/2026:
`1CSmGX0GId8obQaDZ6fstYyXo_1_KjG3IWlT_dLu4Vh0`, identificador em
`teste_watch_folder\calendario_teste_id.txt`. Provado contra ela: o par
repetido do `andersonneiff` preencheu a linha 5 e depois a 6, a terceira
tentativa foi recusada com o motivo certo, e `giroquue/EDSCAP` casou com
`@Giroquue/EDS CAP`.

---

## Por que existe

O Marketing mantém uma segunda planilha, o **CALENDÁRIO GERAL DIVULGAÇÕES -
INFLUENCERS.26**, separada da Monitoramento. Elas preenchem à mão, todo dia,
uma linha por post planejado: influenciador, marca, responsável e data.

Quatro colunas dessa planilha só podem ser preenchidas **depois** que o vídeo
existe, e é isso que o programa passa a fazer: `Jogo`, `Status`, `Horário` e
`Monitorado por`.

Pedido do auditor em 11/09/2026: "a ideia é que elas postam esse cronograma
todo dia preenchendo manualmente cada linha com os influencers e tal, porém o
jogo, o status, horário e monitorado por, são coisas que são preenchidas
depois de baixar o vídeo".

---

## O que foi medido antes de desenhar

Lido direto das abas `AGO.26` e `SET.26` com as credenciais do próprio
programa, em 11/09/2026, **1.984 linhas**. Sem isso o desenho seria palpite.

**Estrutura:** uma aba por mês (`DEZ.25` até `DEZ.26`). Cabeçalho na **linha
2**, dados a partir da **linha 3**. A linha 1 é vazia. Colunas A a I:
Influenciador, Marca, Responsável, Jogo, Status, Data da postagem, Horário,
"Monitorado por:", "Coluna 1".

**A chave repete, e é o caso do auditor.** Influenciador + marca + data
identifica uma linha só em 97% dos casos: em `AGO.26`, 1.047 chaves distintas
para 1.082 linhas (35 repetem); em `SET.26`, 878 para 902 (24 repetem). Sempre
2 linhas, nunca mais. A repetição se concentra em quem posta dois stories no
mesmo dia: `andersonneiff` (LOTTU) quase diariamente, `eduardagutierrez`
(EDS CAP), `weslleyof_`.

**O nome da marca muda de aba para aba:** agosto escreve `EDSCAP`, setembro
escreve `EDS CAP`. As quatro marcas são LOTTU, EDS, EDSCAP e ONA.

**O handle é escrito de qualquer jeito:** com e sem `@`, com espaço no fim
(`nathanqueiroz  `), em maiúscula (`@Giroquue`), e às vezes dois handles na
mesma célula (`@bianquinha182/ bianquinha`).

**Status tem três valores de fato:** `Publicada` (946), `Não Postada` (415) e
vazio (623). **`Apagada` não existe** em nenhuma das 1.984 linhas.

**Horário é quase todo `HH:MM`** (687 em agosto), com sujeira ocasional que o
programa não precisa entender, só não destruir: `-`, `POSTADO NA LIVE`,
`16:012`, `18:40.`, e três em `HHhMM`.

**`Responsável` e `Monitorado por` são pessoas diferentes** em 394 das 1.082
linhas de agosto e 618 das 902 de setembro. São papéis distintos: um cuida do
influenciador, o outro conferiu a entrega.

---

## O que o programa escreve, e o que ele nunca toca

| coluna | quem preenche |
|---|---|
| A Influenciador, B Marca, C Responsável, F Data da postagem | o Marketing, à mão. O programa **só lê** |
| D Jogo, E Status, G Horário, H Monitorado por | o programa |

Três regras que valem sempre:

1. **Nunca cria linha nova.** Se não achar linha que case, avisa na tela. O
   programa não inventa entrega que o Marketing não planejou.
2. **Nunca sobrescreve célula que já tem conteúdo.** Vale inclusive para a
   sujeira medida acima: `POSTADO NA LIVE` fica onde está.
3. **Nunca escreve em coluna do Marketing.** É a mesma separação que já vale
   na Monitoramento (ver `BLOCO_AUTOMACAO` em `fluxo_downloads.py`).

---

## Como o programa acha a linha certa

1. **A aba sai da data do post**, não é fixa: post de setembro vai para
   `SET.26`.
2. **Casa três campos, normalizados:**
   - handle: sem `@`, sem espaço nas pontas, minúsculo
   - marca: sem espaço, maiúscula (resolve `EDSCAP` x `EDS CAP`)
   - data: comparada como data, nunca como texto (ver `data_de_planilha.py`,
     que é o único lugar onde essa regra mora)
3. **Entre as linhas que casam, escolhe a primeira com `Status` vazio.** É o
   que faz o primeiro story cair na primeira linha e o segundo na segunda, sem
   precisar saber qual é qual.
4. **Zero linhas casando:** avisa na tela, com o que procurou, e não escreve.
5. **Todas as linhas que casam já preenchidas:** avisa, e não sobrescreve.

---

## De onde vem cada valor

**Jogo.** Campo novo na tela de Downloads, digitado junto com o link. Viaja na
fila, em coluna nova. Não é reconhecido por visão: foi decisão do auditor em
11/09/2026, e é o que tira do projeto a parte cara e incerta.

**Status = `Publicada`.** Consequência de o download ter concluído.

**Status = `Não Postada`.** Vem da tela nova (abaixo), sem baixar nada.

**Horário.** Do próprio Instagram. O dado já chega hoje e é jogado fora pelo
`.date()` em três lugares: story (`item.date_utc`), post
(`post.date_utc`) e o caminho do yt-dlp (`timestamp`). Convertido de UTC para
horário de Brasília e escrito como `HH:MM`. **Sem a conversão sairia 3 horas
adiantado**, que é erro que ninguém percebe olhando a tela.

**Monitorado por.** O nome declarado na barra lateral (`identidade.quem_sou_eu`),
**mas só se ele já existir naquela coluna da planilha deles**. A planilha é a
fonte do vocabulário, como já é feito com as listas da Monitoramento. Nome
desconhecido, ou e-mail vindo do login, deixa a célula **vazia**: melhor vazio
do que sujar a coluna com um valor que ninguém usa.

---

## A tela de "não postou"

Na própria tela de Downloads, que é o mesmo momento de trabalho. Recebe handle,
marca e data, acha a linha pela mesma regra acima e escreve `Não Postada`.

Não baixa nada e **não gasta chamada do Instagram**, porque não há o que baixar:
a pessoa não postou.

---

## Teste antes do real

Reaproveita o mecanismo que já existe (`fluxo_downloads.modo_real_autorizado`):
mais um arquivo, `calendario_id.txt`, dentro de `producao\analises\marketing_producao\`.

- **Sem o arquivo:** escreve na cópia de teste do Calendário, sempre.
- **Com o arquivo, e com os outros três já exigidos hoje:** escreve no
  Calendário real.

Vale a regra que já está no `CLAUDE.md`: nunca criar esses arquivos sem
confirmar direto com quem administra a planilha do Marketing.

---

## O que ficou de fora, de propósito

- **`Apagada` como status.** Não existe na planilha deles (0 em 1.984 linhas).
  Criar vocabulário novo na planilha de outra área é decisão deles, não nossa.
  Decidido com o auditor em 11/09/2026.
- **Reconhecer o jogo por visão.** Vira campo digitado.
- **Escrever em `Responsável`.**
- **"Há quanto tempo está no ar", medido no download.** Parece responder à
  pergunta do auditor ("tem influencer que apaga antes de dar 24 horas") e não
  responde: baixar 10 minutos depois da postagem só diz "10 minutos", e não diz
  nada sobre o post ter sido apagado depois.

---

## O que vem depois, e por que não agora

**Reconferir se o post continua no ar.** É o que de fato pega quem apaga cedo,
e é projeto próprio porque esbarra na cota, que é o recurso escasso:

- o teto é 20 chamadas por dia por conta (`LIMITE_DIARIO_INSTAGRAM`)
- o uso real medido em 05/09/2026 foi 18 influenciadores por dia, 15 com story
- uma reconferência por influenciador seria +15, ou seja, 30 num teto de 20.
  **Não cabe hoje**

Dois detalhes já levantados, para quem for desenhar isso:

- o custo é **por influenciador**, não por post: a consulta de stories devolve
  todos os stories ativos daquele perfil de uma vez
- a reconferência precisa acontecer **antes das 24h** (tipo 18 a 20 horas
  depois). Story some sozinho em 24h, então depois disso sumir não prova nada

Decisão que fica em aberto para esse projeto: reconferir só um subconjunto
(quem já deu problema) ou subir o teto antes, o que o próprio código explica
como fazer com segurança (uma semana limpa em 20 autoriza ir a 30).

---

## Testes que vão junto

- casamento com `@` e sem `@`, com espaço no fim, em maiúscula
- marca com e sem espaço (`EDSCAP` x `EDS CAP`)
- aba escolhida pela data do post
- duas linhas iguais: a primeira entrega preenche a primeira, a segunda a segunda
- zero linhas achadas: avisa e não escreve
- célula já preenchida: não sobrescreve
- horário convertido de UTC para Brasília
- nome desconhecido em `Monitorado por`: fica vazio
- sem `calendario_id.txt`: escreve na cópia de teste, nunca na real

---

## A leitura de volta: o cronograma do ciclo no texto do Financeiro

Acrescentado em **11/09/2026**, depois de o auditor corrigir uma premissa do
texto do Financeiro: "a parte de financeiro não está de acordo com como
funciona, na verdade essa mensagem é de acordo com essa planilha do calendário
que automatizamos agora. a cada rodada de post eles marcam o check na data que
consta na planilha do calendário que é anteriormente preenchida por eles".

Até aqui o Calendário só recebia escrita. Agora ele também é lido, e é dele que
saem as datas ❌, que a Monitoramento não tem porque nelas não houve download.

### A conferência que motivou o desenho

Um cronograma real de `@lucasguimaraes` (ciclo 6), comparado linha a linha com
a aba `AGO.26` do Calendário real em 11/09/2026:

**Onze das quinze datas batem exatamente**, inclusive a ausência de 19/08 nos
dois lados. **Quatro divergem**, e cada uma de um jeito:

| data | no cronograma | no Calendário |
|---|---|---|
| 16/08 | ✅ 1º entregue | `Não Postada`, com Horário `-` |
| 17/08 | ✅ 2º, marca LOTTU | `Publicada`, marca **EDS** |
| 27/08 | ✅ 6º entregue | Status **vazio** |
| 14/08 | não aparece | `Não Postada` |

Não dá para saber de que lado está o erro: a mensagem pode ter sido mandada
antes de alguém corrigir a planilha, ou depois. Mas é achado por si só, porque
a numeração do ciclo (1º a 7º) sai desse cronograma.

### O que o programa faz com a divergência

**Decisão do auditor em 11/09/2026, entre copiar o ✅ deles e mostrar a
diferença: mostrar.** A evidência da auditoria é o vídeo baixado e validado,
não a marcação que o Marketing pôs na planilha. Copiar o ✅ deles faria a nossa
mensagem repetir o erro em vez de pegá-lo.

Cada data do ciclo cai num de quatro estados (`escopo_e_entrega.montar_cronograma`):

| estado | quando | como sai |
|---|---|---|
| `ENTREGUE` | a auditoria tem o vídeo baixado naquela data | `1º - 16/08 LOTTU ✅`, numerado |
| `NAO_POSTADA` | sem vídeo, e o Calendário diz `Não Postada` | `20/08 ❌` |
| `DIVERGENCIA` | sem vídeo, e o Calendário diz `Publicada` | `05/08 ⚠️` com o motivo na linha |
| `PENDENTE` | sem vídeo, e o Calendário sem marcação | só a data, sem marca |

Uma entrega que discorda do Calendário continua sendo ✅, porque o vídeo existe,
e leva a diferença escrita na própria linha: `1º - 16/08 LOTTU ✅ (o Calendário
marcou Não Postada)`. As divergências também aparecem em faixa própria na tela,
antes de alguém mandar o texto, para dar chance de corrigir a planilha.

### A janela do ciclo, que é o pedaço difícil

As datas ❌ ficam **antes** do primeiro post do ciclo (13/08 e 15/08 vêm antes
do primeiro ✅ em 16/08), e **nenhuma das duas planilhas tem coluna de início e
fim de ciclo**. O número do ciclo só existe colado em linha que já virou post.

`fluxo_downloads.janela_do_ciclo` resolve com o que existe, e isso é **medido**:

- **começa** no dia seguinte ao último post do ciclo anterior
- **termina** na véspera do primeiro post do ciclo seguinte
- a janela nunca corta os próprios posts do ciclo, porque ciclos remontados se
  sobrepõem no dado real (há um que vai de 27/03 a 16/05)

**A ponta final do último ciclo é ESCOLHA, e não medida:** vai até o fim do mês
do último post. Sem ciclo seguinte não existe nada que diga onde parar. Quem
quiser mudar, muda nessa função, num lugar só.

Provado contra o Calendário real em 11/09/2026, com janela de 10/08 a 02/09: o
programa reproduz o cronograma do print, mais o 14/08 que a mensagem deles
tinha esquecido, mais as datas sem marcação no fim.

### Os dois horários do cabeçalho

O cronograma real abre com "Horário de postagem: entre 9h e 20h" e "Horário
limite para aprovação dos vídeos: 16h". Eles são **campo digitável na tela do
Financeiro**, não texto fixo, por decisão do auditor no mesmo dia: são termo de
contrato, não estão em planilha nenhuma que o programa leia, e fixar um valor
para todo influenciador seria escrever um número que não foi medido. Vazios,
não viram linha na mensagem.

### O que continua sem resposta

**Se o Calendário explica a coluna CRONOGRAMA da Monitoramento.** A hipótese de
que `CRONOGRAMA = SIM/NÃO` significa "postou na data agendada" agora é
**testável**, porque o Calendário tem as datas agendadas e a Monitoramento tem
a coluna. O cruzamento não foi feito.

---

## Como o Marketing trabalha quando o influenciador não posta

Medido em **11/09/2026** direto na planilha real, abas `AGO.26` e `SET.26`,
**1.989 linhas**, a pedido do auditor. A pergunta que motivou: se eles remarcam
uma data, o ❌ da nossa mensagem viraria ruído.

Status nas 1.989 linhas: `Publicada` 947, `Não Postada` 416, vazio 626.

### 1. `Não Postada` é registro conferido, não plano esquecido

Das 416 linhas `Não Postada`:

| campo | preenchido |
|---|---|
| Responsável | 416 de 416 (100%) |
| **Monitorado por** | **401 de 416 (96,4%)** |
| Jogo | 220 de 416 (52,9%) |
| Horário | 5 de 416 (1,2%) |

**As 401 com "Monitorado por" são a pista mais forte:** alguém do Marketing
conferiu aquela data e assinou. Isso não é linha de planejamento que sobrou, é
conclusão registrada por uma pessoa com nome. E o Horário quase sempre vazio
confirma o óbvio pelo dado: sem post, não há hora.

### 2. Eles NÃO costumam reabrir a mesma peça em outra data

Das 220 linhas `Não Postada` com Jogo e data preenchidos, comparando o nome do
jogo com o que aquele mesmo influenciador publicou **depois**:

- **189 (85,9%) nunca reaparecem publicadas.** A peça não foi remarcada, ela não
  aconteceu.
- 31 (14,1%) têm o mesmo jogo publicado depois.

**E as 31 não provam remarcação.** Olhando uma a uma, parte é rótulo genérico
que se repete sozinho (`ORGÂNICO` para `@andersonneiff`, `Live` para
`@rachaxp`), e parte é campanha rodando em vários influenciadores ao mesmo
tempo (`CHICKEN HIGHWAY + RANCHO DO MAIA` aparece em 24/08 e 25/08 para
`@andersonneiff` **e** para `@nathanqueiroz`, o que é calendário de campanha e
não reagendamento individual).

Sobram poucos casos com cara de remarcação de verdade, sempre de 1 a 3 dias:
`@nathanqueiroz` com `CHUTE PREMIADO + AVIATOR` em 03/08 para 06/08,
`@felipekersch` com `JOGO DO CHAPÉU + FORTUNE RABBIT` em 14/08 para 15/08.

### 3. A mesma data com dois status é raro, e não é remarcação

Chaves influenciador + marca + data repetidas: **60 em 1.989**. Dessas, só
**10 têm status diferentes entre si**, por exemplo `@andersonneiff` LOTTU 21/08
com uma linha `Publicada` e outra `Não Postada`.

Isso **não** é a mesma entrega marcada de dois jeitos: é quem posta **dois
stories no mesmo dia** e entregou um só. Já estava medido no desenho original
(`andersonneiff` quase diariamente, `eduardagutierrez`, `weslleyof_`).

**Limitação do modelo atual, que fica escrita aqui:** o cronograma da mensagem
é por DATA e o Calendário é por POST planejado. Numa data com dois posts
planejados, um entregue e um não, a data sai como entregue e o post que faltou
não aparece. São ~10 casos em dois meses. Corrigir exige o cronograma contar
post, e não data.

### 4. O que isso diz sobre ligar a chave

O risco que motivou desligar era o ❌ cair numa data que foi apenas remarcada.
O dado diz que **isso é a minoria**: `Não Postada` é assinado por gente em 96,4%
dos casos e a peça não volta em 85,9% deles.

**O que continua sem prova:** nada aqui mostra se uma linha `Não Postada` chegou
a ser mudada depois. A leitura pela API devolve o estado de agora, não o
histórico. Quem quiser fechar essa ponta olha o histórico de revisões do Drive,
ou pergunta a quem administra o Calendário.

---

## "Fechar o ciclo" está desligado (11/09/2026)

O pedido anterior tinha sido entendido errado: a primeira versão desta
correção tirou a **aba inteira** do Financeiro da navegação. O auditor corrigiu:
"não era pra excluir a aba de financeiro, mas sim a parte do ciclo fechado". A
aba voltou ao menu.

**O que saiu de fato:** só o fim da tela, atrás da constante
`FECHAMENTO_DE_CICLO_ATIVO = False` em `pages/3_Financeiro.py`. Isso cobre a
justificativa obrigatória, a chave e os horários do cronograma, o botão
"Solicitar pagamento", o texto para o WhatsApp e a gravação no registro de
fechamentos.

**O que continua funcionando com a chave desligada:** a faixa de situação do
ciclo, os indicadores, a tabela "Escopo contratado x entrega", "Os posts deste
ciclo" e a nova seção "Cronograma do ciclo", incluindo o aviso de divergências.
A tela continua sendo conferência, só deixou de produzir a solicitação.

**Nada foi apagado.** O código do fechamento inteiro continua no arquivo,
dentro de `if FECHAMENTO_DE_CICLO_ATIVO:`, e volta trocando `False` por `True`
na mesma linha.

---

## A janela virou anos de largura por causa de número de ciclo reaproveitado (11/09/2026)

A tela mostrou o cronograma cheio de erro técnico repetido: "não consegui ler
o Calendário inteiro... aba ABR.26: HttpError 400... aba MAI.26... aba
JUN.26... aba JUL.26". O auditor perguntou por que, com a condição de tirar a
seção se não tivesse conserto.

**Causa raiz, investigada na própria cópia da Monitoramento (1.032 ciclos
reais):** o número do ciclo se repete em períodos bem separados do mesmo
influenciador. `@lucasguimaraes` ciclo 6, por exemplo, tinha posts de
`2024-05-09` a `2026-08-17`, o MESMO rótulo "Ciclo 6" usado de novo mais de dois
anos depois. Isso não é o "ciclo remontado" já documentado (que junta datas com
um vão de semanas no meio, como o caso de 27/03 a 16/05); é o rótulo sendo
reaproveitado para um período totalmente diferente.

Medido antes da correção: 54% dos ciclos tinham até 30 dias de posts, mais
19,7% até 60 dias (a faixa normal, incluindo remontados de verdade), mas
**12,6% passavam de 365 dias**, alguns chegando a 32 meses. `janela_do_ciclo`
herdava esse reaproveitamento sem questionar, e a janela explodia para anos,
tentando ler aba de ano que o Calendário real nunca teve (ele começa em
`DEZ.25`).

**A correção, em `fluxo_downloads.janela_do_ciclo`:** duas travas, as duas
justificadas pelo próprio dado medido.

1. Se os posts do PRÓPRIO ciclo já passam de 90 dias de largura, o número foi
   reaproveitado e a função devolve `(None, None)`, mesmo comportamento de
   handle sem ciclo. É honesto: existe dado, mas não dá para confiar nele.
2. A vizinhança com o ciclo anterior e o seguinte nunca estica mais que 45 dias
   além do que foi medido NESTE ciclo, não importa o que o vizinho diga. Um
   vizinho também contaminado não estica a janela deste.

**Efeito medido nos 1.032 ciclos reais, antes e depois:**

| | antes | depois |
|---|---|---|
| maior janela | 32 meses | 5 meses |
| janelas com mais de 4 meses | (não se aplica, a maioria era maior) | 1 |
| ciclos sem janela segura (`None, None`) | 0 (a função nunca recusava) | 265 (25,7%) |

Os 265 que agora ficam sem cronograma são exatamente os que tinham posts
espalhados por mais de 90 dias sob o mesmo número: a tela mostra "Sem o
cronograma: não dá para determinar com segurança as datas deste ciclo" e a
mensagem do Financeiro sai só com as entregas, como sempre saiu.

**E de brinde, aba que não existe parou de assustar.** Mesmo com a janela
contida, um ciclo perto da borda do que o Calendário cobre ainda pode pedir um
mês sem aba. `calendario_divulgacoes._aba_nao_existe` reconhece a mensagem
específica da API do Sheets para "esta aba não existe" (`Unable to parse
range`) e trata como limite esperado, não como problema de leitura: só falha de
verdade (rede, permissão) continua aparecendo na tela.

---

## O texto do WhatsApp é independente de "Fechar o ciclo" (11/09/2026)

Entendimento corrigido pelo auditor: "fechar ciclo é uma coisa, essa mensagem
não existe, a de fechamento de ciclo não existe, o Financeiro olha a própria
planilha de monitoramento para efetuar o pagamento... o que eu quero é que vc
gere, cada post confirmado na planilha de calendário, aquele texto que dá o
check nas datas, que vai gerar o texto que vai pro whatsapp do próprio
marketing".

Ou seja: o texto de solicitação de pagamento (com escopo x entrega, situação
do ciclo e justificativa) nunca foi um documento real. O que existe de
verdade é o cronograma que o próprio Marketing já manda no grupo deles, o
mesmo print mostrado no início deste trabalho (Júnior EDS, "CRONOGRAMA DE
POSTAGENS | EDS | LUCASGUIMARÃES | CICLO 6/12").

**Nova seção em `pages/3_Financeiro.py`, "Texto do cronograma para o WhatsApp
do Marketing"**, logo depois da tabela "Cronograma do ciclo" e **fora do guard
`FECHAMENTO_DE_CICLO_ATIVO`**: continua funcionando com aquela chave desligada,
porque não tem relação nenhuma com ela.

O que ela gera, e o que não gera:

- cabeçalho `CRONOGRAMA DE POSTAGENS | <marcas> | <HANDLE> | CICLO <N>`
- os dois horários (postagem, aprovação), campo digitável, vazios se não
  preenchidos
- uma linha por data já **confirmada** no Calendário (`cronograma_resolvido`,
  Publicada ou Não Postada); data ainda sem marcação não entra
- **nada** de escopo contratado, situação do ciclo ou justificativa

Duas escolhas que ficam registradas, porque não são medição:

- **A marca do cabeçalho é a lista de marcas que aparecem no cronograma**, não
  uma escolhida. No dado real o mesmo ciclo mistura marcas (medido em
  `@lucasguimaraes`), e a mensagem real mostrou "EDS" no cabeçalho com posts
  "LOTTU" no corpo, uma inconsistência que o programa não tem como reproduzir
  com segurança. Inventar uma só seria decidir no lugar de quem lê.
- **Sem o total de ciclos do contrato** ("/12" na mensagem real): essa
  contagem não existe em nenhuma fonte que o programa lê. Só o número do
  ciclo desta tela.

Provado contra o Calendário real (`@lucasguimaraes`, janela 10/08 a 02/09): o
texto reproduz o cronograma do print, mais o 14/08 que a mensagem real tinha
esquecido, mais as divergências entre o Calendário e o que a auditoria baixou.

**A JANELA INTEIRA ENTRA NO TEXTO, e não só o já confirmado (11/09/2026).**
Primeira versão usava só `cronograma_resolvido` (Publicada ou Não Postada), e
o auditor corrigiu: "seria possivel colocar todas as datas pra pessoa ir
preenchendo a medida que forem postando? pq assim que eles fazem, e ai caso a
data futura mude no calendário, deve mudar na mensagem tbm". É como o
Marketing já usa esse texto na prática: a lista existe inteira desde o início
do ciclo, e o check chega depois, um por um. Data ainda sem marca (`PENDENTE`)
sai só com a data, sem ✅ nem ❌, pronta para ser preenchida.

**E como o texto é montado na hora a partir do Calendário**, uma mudança lá
(o Marketing marcando `Publicada`, ou remarcando uma data) aparece aqui na
próxima leitura, sem exigir nada além de abrir a tela de novo. A defasagem
máxima é o cache de `carregar_cronograma`, 120 segundos.
