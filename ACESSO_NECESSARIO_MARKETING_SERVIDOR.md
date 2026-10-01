# O que pedir ao Marketing, e o que criar nós mesmos, antes de subir no servidor

Preparado em 23/09/2026. Serve para a conversa com quem administra a Monitoramento
e o Drive do Marketing, quando chegar a hora de ligar o programa aos sistemas
reais deles no servidor. Levantado direto do código, não por suposição.

**Regra que vale enquanto isso não estiver combinado e assinado:** nunca criar
nem preencher os três arquivos de autorização (seção 3) sem confirmar direto
com quem administra a Monitoramento e o Drive do Marketing. Sem os três, o
programa cai sempre em teste, sem avisar, e é assim que tem que continuar até
o combinado existir de verdade.

---

## 1. Acesso que precisamos pedir a eles

| Recurso (deles) | Nível de acesso | Por quê |
|---|---|---|
| **Dados_influ** (planilha de Cadastro) | Leitura | O programa só consulta. Confirmado pela API (`canEdit: False` na conta atual). Nunca escreve nela. |
| **Monitoramento** (planilha deles) | Escrita | Só entra em vigor com os três arquivos da seção 3. Sem eles, cai sempre em teste. Precisa também da mudança de formato da seção 2. |
| **Calendário Geral de Divulgações** | Escrita, mas limitada por código a duas colunas (JOGO e STATUS), e só quando a célula está vazia (nunca sobrescreve o que já está preenchido) | Mesmo gatilho da seção 3. As colunas em si já existem na planilha deles, não precisam ser criadas. |
| **Pasta raiz no Google Drive** (onde ficam os vídeos e peças, organizados por marca / ano / mês / influenciador) | Escrita (criar pasta, subir arquivo) | Mesmo gatilho da seção 3. |
| **Histórico de Fechamentos do Financeiro** (planilha NOVA, decidido em 23/09/2026 que nasce no Drive deles, não no nosso) | Editor, na planilha que eles criarem (ou numa pasta deles com permissão de escrita, se preferirem que o programa crie) | Não existe hoje nem do lado deles nem como planilha definitiva nossa: a cópia local usada até aqui é só de desenvolvimento, e vai ser abandonada quando esta nascer de verdade. Decisão: mais simples nascer direto no Drive deles do que manter mais um lugar separado. |

Falta decidir e confirmar com eles: qual conta Google vai receber esse acesso.
O login do programa é OAuth (não é conta de serviço), hoje é uma conta
pessoal; no servidor precisa ser uma conta fixa e única, compartilhada por
quem usa o servidor, não uma por pessoa. E se dá para compartilhar só o
arquivo e a pasta específicos com essa conta, em vez de acesso à Drive
inteira do Marketing.

Fora desta lista, de propósito: Netlex e Sankhya. O programa não fala com
nenhum dos dois em tempo real, são dados trazidos manualmente para planilhas
nossas.

---

## 2. Mudança de formato que precisa de acordo explícito com eles

A Monitoramento real do Marketing vai de A a V, e todas as 22 colunas já têm
dono (contrato, seguidores, cronograma, pagamento, horas de live,
observação). O que a automação produz não cabe ali, então ela usa um bloco
próprio de colunas novas, de W a AD, que hoje só existe na planilha de
TESTE (criado em 28/08/2026):

| Coluna | Nome | Para que serve |
|---|---|---|
| W | DATA_DOWNLOAD | Quando o material foi capturado (diferente da data do post: conteúdo de rede social muda e some) |
| X | SITUACAO | Em que ponto do fluxo a linha está: N/A, AGUARDANDO VALIDAÇÃO ou VALIDADO. É por aqui que a análise sabe onde há arquivo para conferir |
| Y | VALIDACAO | Veredito da análise |
| Z | EVIDENCIA | O que faltou e em qual arquivo, para quem contestar o veredito ter como conferir |
| AA | VALIDADO_EM | Quando a análise rodou |
| AB | MARCACAO | ORGANICO ou LINK, escolhido por uma pessoa na hora de baixar |
| AC | PEDIDO_POR | Quem pediu aquele download, pela identidade do login |
| AD | ARQUIVO | Endereço do arquivo exato daquela peça no Drive (a coluna LINK deles aponta para a pasta do post, não para a peça) |

Isso é mudança no FORMATO da planilha deles, não só no conteúdo, e por isso
precisa de acordo explícito antes de escrever na planilha real. Sem essas
colunas criadas (por eles, ou por nós com autorização deles) na posição
certa, escrever na real com o código de hoje escreveria por cima de
qualquer coisa que já exista em W a AD, ou erraria de coluna.

A Calendário Geral de Divulgações NÃO precisa dessa mudança: as colunas que o
programa preenche lá (JOGO e STATUS) já existem na planilha deles.

---

## 3. O gatilho que liga tudo (já existe no código, só falta a decisão)

Três arquivos, todos em `producao\analises\marketing_producao\` (fora de
`teste_watch_folder` de propósito, para não misturar identificador de
produção com pasta de teste):

1. `AUTORIZO_ESCREVER_NOS_SISTEMAS_REAIS_DO_MARKETING.txt` (o nome já é a
   autorização, o conteúdo não importa)
2. `monitoramento_id.txt` (identificador da Monitoramento real)
3. `drive_pasta_raiz_id.txt` (identificador da pasta raiz real no Drive)

Faltando qualquer um dos três, o programa escreve sempre na cópia de teste,
sem avisar. Isso é o comportamento seguro, e só muda por decisão explícita.

---

## 4. O que é nosso: parte já existe e só precisa ser LEVADA para o servidor, parte é para criar do zero

**CORRIGIDO EM 23/09/2026, duas vezes.** Primeiro achei que nem tudo nesta
lista era "criar do zero", porque `teste_watch_folder` é só o nome da pasta
onde TODOS os arquivos de identificador ficam neste projeto (a Cadastro
real também é apontada por um arquivo lá dentro), e não diz se a planilha é
de teste ou definitiva. Isso valia para Perfis_Instagram e Estado_Instagram.
Já o Histórico de Fechamentos, o auditor esclareceu: as linhas de hoje não
são registro de auditoria real, foram criadas a pedido dele mesmo, de
desenvolvimento, testando a funcionalidade. Não existe planilha assim nem
do lado do Marketing, e a decisão foi essa planilha nascer no Drive DELES,
não no nosso nem no servidor (ver seção 1). A cópia local de teste vai ser
abandonada quando a de verdade existir lá.

### 4a. Já existem, e são definitivas: NÃO recriar, só levar o mesmo identificador

Estas nasceram para serem a ÚNICA cópia, compartilhada por todo mundo desde
o primeiro dia, exatamente para sobreviver a qualquer troca de máquina ou
de servidor:

- **Perfis_Instagram** (mapa de perfis, para não pagar de novo pela
  chamada que já bloqueou conta em agosto).
- **Estado_Instagram** (contador de chamadas do Instagram, pausa e
  revezamento entre máquinas).

### 4b. Cópias de teste de verdade: criar do zero no servidor, sem prejuízo

- **Monitoramento de teste**
- **Fila de downloads de teste**
- **Cadastro, cópia de teste** (a que espelha a Dados_influ real antes de
  abrir a tela, criada em 23/09/2026, e se recria sozinha a cada 10 minutos)

Para estas três, criar do zero no servidor (ou deixar o próprio programa
criar na primeira vez que precisar) não perde nada, porque nenhuma delas
guarda conclusão de auditoria.

### 4c. Histórico de Fechamentos do Financeiro: SAIU desta lista

Vira item de acesso, não de criação nossa. Ver seção 1: planilha nova,
decidido que nasce no Drive do Marketing.

---

## 5. Perguntas abertas para levar à conversa com o Marketing

- Quem administra a Monitoramento e o Drive, e quem decide a autorização de
  escrita real (seção 3)?
- Eles preferem criar as colunas W a AD (seção 2) do lado deles, ou
  autorizam o programa a criar, com a posição e o formato acordados antes?
- Qual conta Google vai ser a fixa do servidor, para receber o
  compartilhamento dos arquivos e da pasta (seção 1)?
- Compartilhamento por arquivo/pasta específico, ou por Drive inteira?
- **Colunas sem título na Dados_influ, com dado real dentro (levantado em
  23/09/2026, conferido célula a célula até a linha 209):**

  | coluna | conteúdo | preenchida em |
  |---|---|---|
  | U | "E-mail enviado em: DD/MM/AAAA HH:MM:SS" | 52 de 208 |
  | V | número de seguidores por extenso, como a pessoa digitou (ex.: "1,3 milhões", "125 mil") | 154 de 208 |
  | W | mesmo formato de U, uma segunda coluna | 24 de 208 |
  | X | mesmo formato de U, uma terceira coluna | 19 de 208 |

  Nenhuma tem título na linha 1, e por isso o programa não vê esse dado hoje
  (a tela de Cadastro monta a tabela só com as colunas que o cabeçalho
  declara). Perguntar: o que é cada uma, e se vale colocar título nelas.
  Se a Marketing puser título na V (seguidores por extenso), o programa já
  está pronto para passar a mostrar, sem precisar de outra investigação
  manual como esta. U, W e X parecem ser a MESMA informação (e-mail enviado
  numa data) repetida em coluna nova a cada vez, em vez de reaproveitar uma
  só: vale perguntar se é isso mesmo, e se dá para juntar numa coluna só.
