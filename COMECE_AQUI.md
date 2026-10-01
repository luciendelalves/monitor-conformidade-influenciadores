# Comece aqui: automação da auditoria de publicidade de influenciadores

**Versão 2 · 07/09/2026, fim do dia.**

**Para quem o programa é:** ele vai ser entregue à equipe de Marketing de
Influência para uso no dia a dia, em análise **nova**. Não é ferramenta de
reprocessar a base histórica. Quando um número deste arquivo vier da base
antiga, isso está dito na linha, porque o banner da peça mudou em 17/07/2026 e
número tirado de peça velha descreve uma geração que não existe mais.

Este arquivo existe para um chat novo entender o programa **sem ler o histórico
inteiro**. Ele descreve o estado de hoje. O diário cronológico, com o porquê de
cada decisão passada, está em `PROMPT_CONTINUACAO.md` (2.474 linhas, organizado
por data). Leia o diário só quando precisar do motivo de algo específico.

---

## Os primeiros cinco minutos

```
cd C:\Users\auditor\Documents\Auditoria\producao\analises
py verificar_ambiente.py                       # o ambiente está completo?
py baixadores.py                               # a peça que baixa está velha?
for %f in (testes\*.py) do py "%f"             # os 57 testes passam?
```

Para abrir o programa, **dois cliques, nesta ordem**:

1. `iniciar_trabalhador.bat` (janela "1 de 2 · TRABALHADOR · NÃO FECHE")
2. `iniciar_validacao_influenciadores.bat` (janela "2 de 2 · TELA · pode fechar")

Guia de instalação numa máquina nova: `INSTALAR.md`, versão 3.

---

## 1. O que o programa faz, e para quem

A EGB (Esportes da Sorte, Onabet, Lottu) paga influenciadores para divulgar
apostas. A Portaria SPA/MF 136 e as normas seguintes exigem avisos obrigatórios
em cada peça publicada. O programa:

1. **baixa** a peça do Instagram a partir de um link
2. **organiza** no Drive do Marketing, na pasta certa
3. **cria a linha** na planilha de Monitoramento
4. **analisa** se os avisos obrigatórios estão na peça (a "régua")
5. **cruza** o escopo contratado com o que foi entregue no ciclo
6. **gera** o aviso que a pessoa cola no WhatsApp do Financeiro

**Quem usa:** hoje o auditor (Auditor, Auditoria Interna). A partir de agora
uma analista do Marketing, em teste, até 30/09. Depois vai para um servidor
Windows.

**Quem construiu:** a auditoria. O programa automatiza uma auditoria de
influenciadores que era feita à mão.

---

## 2. Onde as coisas estão, e de onde vieram

```
C:\Users\auditor\Documents\Auditoria\      ← abra o VS Code AQUI, sempre
├── .claude\          11 agentes, 13 skills, comandos /painel e /setup
├── .genesis\          o motor do painel do "Genesis Studio"
├── contexto\
│   ├── referencia\templates\    os 4 templates oficiais de RA
│   ├── design-system.html       lido por producao\analises\estilo.py
│   ├── perfil.md  fonte.md      lidos pelo .genesis por caminho fixo
│   ├── dados\                   entrada da skill `analisar`
│   ├── Auditoria-MKT de influencers\   ← A FONTE DESTE PROJETO
│   └── (7 outras pastas de auditorias passadas)
└── producao\
    ├── analises\      ← O PROGRAMA. Git próprio, sem remoto
    ├── auditorias\avisos-influenciadores-portaria136\   ← saída e cache (453 MB)
    ├── scripts\excel_tecnico\   98 scripts do papel de trabalho
    ├── queries-sql-sankhya\     SQL por achado
    ├── backup\        o zip do backup do João (105 MB)
    ├── resumos-executivos\  sankhya-espelho-contabil\
```

**Origem, porque isso já gerou dúvida:** `.claude\` e `contexto\` vieram
**cheias** do backup do Auditor Anterior, ex-auditor sênior, de 07/08/2026.
`producao\` veio como **esqueleto vazio**. A prova está em
`..\..\LEIA-ME-ORIGINAL-JOAO.md` e `..\..\GUIA-DE-SETUP.md`. O auditor herdou o
setor no fim e não construiu essa estrutura.

**A estrutura não é decorativa.** `.genesis\painel_backend.py` linha 93 lê
`contexto/perfil.md` e `contexto/fonte.md` por caminho relativo à raiz, e a skill
`nova-auditoria` lê `contexto/dados/` e `contexto/referencia/`. Renomear isso
quebra as skills herdadas.

**Padrão para auditoria nova**, decidido em 07/09: uma subpasta em
`contexto\<Nome>\` para a fonte e uma em `producao\auditorias\<nome>\` para a
saída, com a raiz compartilhada. **Não** criar uma pasta `contexto` paralela.

**Três coisas ficam fora de `producao\analises` e a cópia não leva:**

| o que | onde | sem ela |
|---|---|---|
| a cópia da Monitoramento em Excel | `contexto\Auditoria-MKT de influencers\` | **todo vídeo cai em "Ciclo A CONFIRMAR"**, sem erro |
| o `oauth_client.json` | `Documents\COAF`, de outro projeto | não dá para autorizar credencial nova |
| o cache das análises | `producao\auditorias\` | nada, é criado sozinho |

---

## 3. Arquitetura: dois processos, e o Streamlit é casca

**São dois programas e os dois precisam estar de pé.** Desde 29/08 o trabalho
pesado saiu de dentro da aba do navegador, senão fechar a aba matava o download
no meio.

```
  painel.py  (Streamlit)  ←→  fila_trabalho.py  ←→  trabalhador.py
      a tela                  fila em disco          quem baixa e analisa
                              + trava.py (trava entre processos)
```

**Medido em 07/09:** 11.185 linhas de lógica em Python puro contra 4.361 de tela.
O motor da auditoria (`escopo_e_entrega.py`, `validar_avisos_portaria136.py`,
`fluxo_downloads.py`, `pipeline_influenciadores.py`, `registro_fechamentos.py`,
`baixadores.py`) **não importa Streamlit**. 55 dos 57 testes rodam sem ele (só
`teste_acesso.py` e `teste_as_telas_abrem.py` precisam dele, e é o esperado).

Consequência que importa: **o Streamlit é trocável.** Se um dia não servir,
reescreve-se a tela, não o programa. Foi a conclusão da pergunta "deveria ter
sido Django ou Node?": não, e o motivo de Node é técnico, todo o processamento
é Python (Tesseract, EasyOCR, RapidOCR, faster-whisper, Ollama, openpyxl,
google-api-python-client, yt-dlp, instaloader).

**Sinais de que seria hora de sair do Streamlit** (nenhum ocorreu ainda): mais
de dez pessoas ao mesmo tempo; permissão diferente por pessoa (já pressiona,
existe `acesso.PAPEL_SUPERVISAO`); acesso de fora da rede; a planilha virar
gargalo. Se acontecer, o caminho é FastAPI, não Django, porque a lógica já está
em módulos puros.

**O que o Streamlit já cobrou:** cerca de 600 linhas de encanamento
(`fila_trabalho.py` 436 + `trava.py` 172) que existem só porque ele reexecuta o
script a cada clique e amarra o trabalho à aba. Django com Celery daria isso de
graça.

---

## 4. As quatro telas

**ATUALIZADO EM 14-15/09/2026** (a versão do cabeçalho deste arquivo não
acompanhou; a seção 20 tem o detalhe da reforma). `painel.py` é o roteador e o
**único** ponto de entrada. Cada tela chama `acesso.exigir_login()` por conta
própria, porque dá para abrir página direto.

| tela | arquivo | o que faz |
|---|---|---|
| Downloads | `pages/1_Downloads_e_Organizacao.py` | cola o link (com o **Jogo**), baixa, organiza no Drive, cria a linha, preenche o Calendário, marca quem **não postou**, envio de arquivo à mão |
| Monitoramento | `pages/2_Monitoramento.py` | mostra as linhas e a evidência; também acompanha a análise, tira da análise, devolve e tenta de novo |
| Financeiro | `pages/3_Financeiro.py` | escopo x entrega, nota de consulta sobre o escopo (fechamento de ciclo continua desligado) |
| Cadastro | `pages/4_Cadastro_de_Influenciadores.py` | consulta ao cadastro. Sem Netlex, e desde 14/09 também corrige campo, célula por célula, pelo módulo `cadastro.py` (não é mais só leitura) |

**A Validação Regulatória saiu do menu em 14/09/2026, e `app_validacao_influenciadores.py`
foi apagado.** O motor (`pipeline_influenciadores.py` + `trabalhador.py`)
continua rodando fora do Streamlit, sem depender dessa tela.

**DUAS PLANILHAS DO MARKETING RECEBEM ESCRITA, DESDE 11/09/2026.** A
Monitoramento é a evidência da auditoria, e vem primeiro. O **CALENDÁRIO GERAL
DIVULGAÇÕES** é o segundo destino: o programa preenche Jogo, Status, Horário e
Monitorado por na linha que o Marketing já criou, nunca cria linha e nunca
sobrescreve célula preenchida. Falhar ali avisa e segue, e não derruba o
download. Ver `calendario_divulgacoes.py` e `DESENHO_CALENDARIO.md`.

Se a barra lateral mostrar **nome de arquivo** em vez desses títulos, subiu pelo
arquivo errado. O comando certo é `py -m streamlit run painel.py`.

---

## 5. A planilha é o banco de dados

Não há banco. A planilha do Marketing é a camada de guarda. Isso é decisão do
auditor, não limitação.

| planilha | id | acesso |
|---|---|---|
| Marketing de Influência (real) | `13uLhupENDl6bSHfRioaQz0mcZUio_IOojp1_c1CFhQU` | **SOMENTE LEITURA. Nunca escrever.** |
| cópia de teste da Monitoramento | em `teste_watch_folder\monitoramento_teste_id.txt` | leitura e escrita |
| fila de downloads | `fila_downloads_id.txt` | leitura e escrita |
| cadastro (Dados_influ) | `cadastro_planilha_id.txt` | leitura |
| fechamentos de ciclo | `fechamentos_planilha_id.txt` | escrita, por acréscimo |

A planilha real tem as abas `Sumário`, `Financeiro`, `Responsáveis`,
`Monitoramento` (24.334 linhas, 41 colunas), `entregas`, `CICLOS`, `Dados_influ`
(205 linhas).

**Cinco arquivos de identificador**, todos em `teste_watch_folder\`, mais o
`netlex_contratos.csv` e o `conta_instagram.txt`. O `verificar_ambiente.py`
confere todos desde 07/09.

**Falta de identificador que NÃO dá erro, e por isso é pior:**
`drive_teste_pasta_raiz_id.txt` ausente faz o programa **criar uma pasta nova**
no Drive e os vídeos vão para onde ninguém olha.

### Duas armadilhas da planilha, aprendidas na prática

**O Sheets reformata data na leitura.** Gravar `06/09/2026` devolve `06/09/26`.
**Nunca comparar data como texto.** Use `data_de_planilha.py`, que é o único
lugar onde essa regra mora.

**Injeção de fórmula.** Texto começando com `=`, `+`, `-` ou `@` é neutralizado
com apóstrofo por `_neutralizar_formula()`.

**Escrita com proteção de colisão.** Antes de gravar, relê a célula e recusa se
mudou (`valor_esperado_antes`).

**Fórmula HYPERLINK com `;` corrompe o xlsx.** Escrita via openpyxl precisa
vírgula, mesmo com Excel em pt-BR.

---

## 6. Credenciais

Três tokens em `_drive_credenciais\`, e os escopos **não** são todos mínimos:

| token | escopo | alcança |
|---|---|---|
| `drive_token.json` | `drive.readonly` | **todo** o Drive da conta |
| `drive_file_token.json` | `drive.file` | só o que o programa criou |
| `sheets_write_token.json` | `spreadsheets` | **qualquer** planilha da conta |

A restrição à cópia de teste é **convenção do código**, não limite da
credencial.

**Instagram:** a sessão vem do **Firefox** (Chrome e Edge cifram os cookies
desde a versão 127). `teste_watch_folder\cookies_instagram.txt` é a reserva. O
nome da conta vem de `conta_instagram.txt`, depois da variável
`USUARIO_INSTAGRAM`, e por último de **um @ real escrito fixo no código**. Se o
nome não bater com a sessão, a biblioteca trata como anônimo **sem avisar** e a
conta corre risco de bloqueio. Foi assim que uma conta foi bloqueada em 25/08.

**Login do programa:** `.streamlit\secrets.toml` com **cinco** chaves
(`client_id`, `client_secret`, `server_metadata_url`, `redirect_uri`,
`cookie_secret`), listadas na constante `acesso.CHAVES_DO_LOGIN`. Faltando
qualquer uma, o programa **abre sem pedir login**, ao contrário do esperado.

**Achado aberto de segurança:** `producao\scripts\google_sheets_conector\`
tem `credentials.json` (21/07/2026, antes da herança) e `token.json` com
`refresh_token` e escopo `spreadsheets.readonly`. Estão **fora** da pasta
protegida pelo `.gitignore`. Precisam ser **revogados** no console do Google
antes de apagar, porque o `credentials.json` guarda o `project_id` necessário
para achar o projeto.

---

## 7. O motor da régua (`validar_avisos_portaria136.py`, 1.797 linhas)

### O princípio, definido pelo auditor em 02/09

**Presença, não perceptibilidade.** A régua confere se o aviso **está** na peça.
Julgar se está legível o bastante é competência de quem lê a peça, não do
programa.

### A escada de detecção

| degrau | motor | quando |
|---|---|---|
| 1 | Tesseract (`ocr_image_rapido`) | sempre |
| 2 | RapidOCR (`ocr_image_medio`) | se o degrau 1 não resolveu |
| 3 | EasyOCR (`ocr_image_forte`) | se o 2 não resolveu |
| 4 | Tesseract na faixa crua do topo | **só para o `#publi`**, só se ele não foi lido |
| 5 | visão local, Ollama `minicpm-v` | itens que o OCR não confirmou |
| 6 | áudio, faster-whisper | quando o OCR sozinho não fecha |

Sai assim que o aviso completo é confirmado, quadro por quadro.

### Os recortes, e por que são diferentes para OCR e visão

Isto foi **medido** e é contraintuitivo:

| consumidor | imagem | resultado medido |
|---|---|---|
| visão, rodapé | faixa de baixo (14%) ampliada 4x | passou a **ler** em vez de chutar |
| OCR, rodapé | recorte ampliado | **piorou**, e a hipótese foi descartada |
| OCR, publi | faixa do topo (25%) **crua**, em união com o quadro inteiro | quadro 14, recorte 8, união **19** de 160 quadros |
| OCR, publi | faixa do topo ampliada | 5 de 160, pior |

**Não é contradição:** o OCR precisa de caractere nítido e ampliar borra; a
visão precisa de resolução relativa e ampliar entrega isso.

### Onde cada aviso fica, medido em 450 quadros do cache

| item | posição vertical (0 = topo, 1 = base) |
|---|---|
| rodapé (portaria, 18+, responsabilidade, Ministério da Fazenda) | 86% das ocorrências acima de 0,80. Mediana 0,908 |
| `#publi` | **bimodal**: 69% no topo até 0,25 (mediana 0,091), 25% na base acima de 0,80, quase nada no meio |

Por isso o publi recebe as **duas** faixas, e basta uma responder sim: são dois
lugares possíveis do mesmo item, não dois requisitos.

### A regra do bloco do rodapé

Provado o bloco (pelo menos 2 das 4 linhas lidas, `rodape_esta_na_tela`), os
itens **ambíguos daquele bloco** deixam de ser pendência. Foi o que fez as três
peças da @jojotodynho fecharem CONFORME em 06/09, depois de o auditor chamar o
resultado anterior de inadmissível.

### A regra do `#publi`, definida pelo auditor em 07/09

**O publi é obrigatório**, em qualquer forma: `#publi`, `publicidade`,
`parceria paga`. Ele fica em outro canto da tela, longe do rodapé, e **ler o
rodapé não prova nada sobre ele**.

Rodapé completo sem publi é **NÃO CONFORME**. Publi sozinho sem o rodapé
também.

**O veredito depende de o programa SABER, não de qual item falta:**

| situação | veredito |
|---|---|
| publi lido por OCR | cumprido |
| não lido, e a visão diz que **não** viu | **NÃO CONFORME** (ausência confirmada por dois motores) |
| não lido, e a visão diz que **viu** | **REQUER VERIFICAÇÃO** (não dá para afirmar ausência) |

**Contraprova que fundamenta isso, registrada no próprio arquivo:** o Tesseract
acha o publi em 4 de 40 quadros e a visão "responde sim com facilidade". Até
07/09 a régua absolvia o publi com base nesse sinal e a peça fechava CONFORME.
Isso foi removido: absolver assim é declarar conforme uma peça em que ninguém
leu a identificação de publicidade.

### A pergunta da visão sobre o publi, corrigida em 08/09/2026

O "responde sim com facilidade" tinha causa, e ela não era o modelo. A pergunta
do publi era a **única** do dicionário `_PERGUNTAS_VISAO` que perguntava por
CONCEITO, "um selo ou marca indicando publicidade", enquanto portaria, extra,
ministério da fazenda e 18+ todas citam a frase literal que procuram. A faixa
legal do rodapé é, literalmente, uma marca que indica publicidade autorizada,
então o modelo dizia sim sempre que ela caía no recorte. Ele respondia a
pergunta que recebeu.

Medido em 27 peças com verdade conhecida, 17 com publi (12 confirmadas pelo
próprio OCR, 5 a olho) e 10 sem publi (a olho):

| pergunta | acha o publi que existe | não inventa o que não há | geral |
|---|---|---|---|
| conceitual (até 07/09) | 17/17 (100%) | **1/10 (10%)** | **67%** |
| nomeando o texto (hoje) | 17/17 (100%) | **10/10 (100%)** | **100%** |

Um controle sustenta o diagnóstico: perguntando na faixa do MEIO, onde o publi
quase nunca está e não há faixa legal, o modelo dizia não em 20 de 20. E a única
peça em que ele dizia não na faixa de baixo era justamente aquela em que a faixa
legal caía acima do recorte.

Com a pergunta nomeando o texto, os positivos passaram a ser confirmados na
**faixa de cima**, que é onde o publi de fato está. A resposta virou locacional
em vez de reflexo do rodapé.

**Refazer com `py ferramentas\avaliar_pergunta_do_publi.py`.** O conjunto é todo
do banner anterior a 17/07/2026, e os rótulos a olho são de quem mediu, não de
quem audita a peça.

**O que reduz conferência humana é o OCR ler mais, não a régua perdoar.**

### Peça orgânica

Peça marcada como orgânica **não passa pela régua** e é contada à parte. Decisão
de 03/09, depois de conversa com o Marketing.

### Outras decisões da régua

- checagem de imagem de criança **desligada** em 28/08: era 50,3% do tempo e deu
  0 alerta em 445 linhas
- amostragem de quadros por relógio, espalhada pelo clipe. Até 29/08 todos os
  quadros saíam do primeiro 0,7 segundo, o que invalida análise anterior a essa
  data
- PySceneDetect testado e **rejeitado**: com o mesmo número de quadros (8), a
  amostragem por relógio e a por cena acharam exatamente o mesmo
- a visão é o gargalo, 81% do tempo, não o OCR

---

## 8. O motor de escopo e entrega (`escopo_e_entrega.py`, 1.044 linhas)

Módulo **puro**. Importa só `re` e `data_de_planilha`. Isso é propriedade a
preservar: não importar tela, rede nem Google aqui.

### Três níveis, e só o do meio tem cota

| nível | o que é | pagamento |
|---|---|---|
| link / tela | um post | coluna PAGAMENTO da Monitoramento, `Realizado`/`Pendente`, à mão |
| **ciclo** | **a cota.** É o que `fechar_ciclo` fecha | o rádio do Financeiro |
| contrato | só define período e quais ciclos existem | não tem cota |

**Medido, 156 de 156:** o escopo da `Dados_influ` é a cota de **um ciclo**, não o
total do contrato. Não existe "escopo total do contrato" a fechar nem a pagar.

**Medido em 07/09, e não reabrir:** a coluna ESCOPO da Monitoramento **não é
foto congelada**. Ela bate com o cadastro atual em **1.053 de 1.053** ciclos, sem
variar dentro de nenhum. As duas fontes são a mesma fonte. Limitação que fica, e
é do dado: se o Marketing editar o escopo numa renovação, os ciclos passados
passam a mostrar o escopo novo, e o programa não tem como saber o histórico.

### Contagem de POST

A cota é contada em **POSTS**, e um pacote de story do mesmo dia é **um** post.
Por isso a chave é `(tipo, dia, número do post)` e o dia passa pelo leitor de
data. Peça orgânica tem contagem própria e não herda a do link.

### Só peça CONFORME conta para a cota

Decisão de 31/08: "evita avisar que a cota fechou contando peça que está Não
Conforme". O custo aceito foi o aviso chegar depois de a análise rodar.

### Situações

Escopo: `CONFORME`, `INCOMPLETO`, `NÃO CONFORME`.
Pagamento: `NÃO PAGO`, `PARCIALMENTE PAGO`, `PAGO`.

**`PARCIALMENTE PAGO` é vocabulário da auditoria, criado no papel de trabalho.**
A coluna PAGAMENTO do Marketing só tem `Realizado` e `Pendente`. **Nunca gravar
`PARCIALMENTE PAGO` na planilha deles.** Ele vive só no registro de fechamentos.

### O achado de pagamento

`achado_de_pagamento(pagamento, situacao)` devolve
`"PAGAMENTO SEM A ENTREGA FECHADA"` quando houve pagamento e a entrega não
fechou. **Essa frase exata é gravada na coluna de achado do registro de
fechamentos**, e é por ela que esses casos vão ser contados depois. Mudar o texto
na tela quebraria a contagem.

---

## 9. O que é manual, de propósito

**`CRONOGRAMA` (`SIM`/`NÃO`) e `PAGAMENTO` (`Realizado`/`Pendente`) são
preenchidos à mão na planilha, linha por linha.** Decisão do auditor em 05/09,
depois de uma tela de edição ter sido construída e apagada. O programa **lê e
mostra** as duas, e **não escreve nenhuma** em momento nenhum. Existe teste
provando a ausência (`teste_automacao_nao_escreve_cronograma_e_pagamento.py`).

**O que CRONOGRAMA significa nunca foi confirmado com o Marketing.** Hipótese de
composição foi testada em 04/09 e **derrubada** pelo cruzamento real. Pista
melhor, ainda não confirmada: atraso de diária ou de gravação.

**E desde 11/09 essa pergunta virou testável, mas não foi testada.** Com o
Calendário ligado, as datas agendadas existem de um lado e a coluna CRONOGRAMA
do outro, então dá para cruzar as duas e ver se `SIM` é "postou na data
agendada". Ninguém fez esse cruzamento ainda.

---

## 10. Fechamento de ciclo

> **"Fechar o ciclo" está DESLIGADO desde 11/09/2026**, a pedido do auditor:
> "não era pra excluir a aba de financeiro, mas sim a parte do ciclo fechado".
> A aba Financeiro continua no menu e continua conferindo situação, escopo x
> entrega, posts do ciclo e o cronograma do Calendário. O que está fora do ar é
> só o fim da tela: justificativa, botão "Solicitar pagamento", texto para o
> WhatsApp e a gravação no registro de fechamentos. Nada foi apagado: é a
> constante `FECHAMENTO_DE_CICLO_ATIVO` em `pages/3_Financeiro.py`, e religar é
> trocar `False` por `True`. O resto desta seção descreve a tela como ela é com
> a chave ligada.

Na tela do Financeiro, o auditor confirma a entrega e informa a situação de
pagamento. Gera:

1. um registro em **planilha própria** (`registro_fechamentos.py`, aba
   `Fechamentos`), append-only, com coluna dedicada ao achado
2. um CSV local (`teste_watch_folder\fechamentos_ciclo.csv`)
3. o **texto para colar no WhatsApp do Financeiro**

O texto não autoriza pagamento e não afirma conformidade regulatória. Termina na
assinatura de quem conferiu. Não leva dado pessoal de apostador: só o @ do
perfil, a marca, o ciclo e as quantidades.

**O texto é o cronograma do ciclo desde 11/09, e não mais só a lista de
entregas.** Ele sai do Calendário de Divulgações, então tem também as datas em
que o influenciador não postou (❌), que a Monitoramento não tem. O ✅ continua
sendo do que a auditoria baixou e validou: quando o Calendário diz uma coisa e
a auditoria tem outra, **a linha mostra a diferença em vez de copiar a
marcação deles**. As divergências aparecem em faixa própria na tela antes de
alguém mandar o texto. Ver a última seção de `DESENHO_CALENDARIO.md`, com as 4
divergências medidas que motivaram a regra.

**Os dois horários do cabeçalho** ("horário de postagem" e "horário limite para
aprovação") são campo digitável, e ficam de fora quando vazios: são termo de
contrato e não estão em planilha nenhuma que o programa leia.

**Aberto:** o módulo espera a aba `Fechamentos` existir e **não a cria**. Numa
planilha nova, toda gravação falha e cai em silêncio para o arquivo local. E
`registro_fechamentos.ler()` nunca é chamado, então o histórico na tela sai só do
CSV local e um fechamento feito em outra máquina fica invisível.

---

## 11. Os freios do Instagram

| constante | valor | por quê |
|---|---|---|
| `LIMITE_DIARIO_INSTAGRAM` | 20 **por conta** | teto do dia, contado por `USUARIO_DOS_COOKIES`, de segunda a sexta |
| `LIMITE_DIARIO_INSTAGRAM_FIM_DE_SEMANA` | 30 **por conta** | teto do dia no plantão de sábado e domingo (criado 12/09), quando 1 pessoa cobre sozinha o que os outros dias dividem em 6 contas; ver `limite_diario_vigente()` |
| `LIMITE_INSTAGRAM_POR_RODADA` | 3 | |
| `PAUSA_INSTAGRAM_MIN/MAX_SEG` | 20 a 45 | espaçamento entre links (era 30 a 180 até 11/09) |
| `PAUSA_ENTRE_RODADAS_MIN/MAX_SEG` | 180 a 420 | entre rodadas, só quando a rodada bateu no limite |

Um lote de 6 links passa por 2 rodadas de 3: dentro da rodada, 20 a 45 segundos
entre um link e o outro; entre as rodadas, 180 a 420 segundos. **Isso não é
lentidão, é o que evita o bloqueio.**

**Link colado no meio do trabalho não paga a pausa de rodada** (11/09). A pausa
longa só entra quando a rodada foi barrada pelo limite de 3, que é o caso de
rajada. Colar dois links seguidos espera só o intervalo curto.

**Uma conta por dia por máquina**, gravado na chave `#maquina-do-dia` dentro de
`estado_conta_instagram.json`. Duas contas falando com o Instagram no mesmo dia
do mesmo IP é o padrão que levou a bloqueio em 27/08.

**12/09: teto próprio para o plantão de fim de semana.** No sábado e domingo,
uma pessoa cobre sozinha, na própria conta, o que nos dias de semana seis
contas dividem. `limite_diario_vigente()` decide o teto do dia (20 de segunda
a sexta, 30 no fim de semana); os dois nomes de constante continuam existindo,
mas ninguém mais deve ler `LIMITE_DIARIO_INSTAGRAM` direto para saber "o teto
de hoje", só `limite_diario_vigente()`. O 30 é ESCOLHA, não medição, o mesmo
próximo degrau já autorizado desde 30/08 se uma semana em 20 não desse sinal
de alerta; nunca houve medição de volume de fim de semana. O freio contra
insistência (pausa, recuo em bloqueio) não muda. Teste:
`teste_teto_fim_de_semana.py`.

**Medido em 05/09:** 18 influenciadores por dia, 15 com story. O teto de 20 é
**por conta**, então sobra folga de 7x. A projeção anterior de 32 a 40 era
teórica e está errada.

**O endpoint de descobrir o userid pelo @ (`web_profile_info`) é o mais
limitado** e responde 429 com facilidade. Por isso o cache
`instagram_userids.json` (handle → userid numérico, informação pública) **vale
copiar** entre máquinas. Só **Story** precisa desse número; Reel e post o yt-dlp
resolve sozinho.

**Nunca zerar o contador do dia por cosmética.** Foi feito uma vez e removeu o
freio enquanto a conta estava sendo limitada.

### O disfarce de navegador, alinhado em 22/09/2026

Os freios acima cuidam de **quantas** chamadas saem. Isto cuida de **com que
cara** elas chegam. São três caminhos falando com o Instagram, e até 22/09
cada um dizia ser um navegador diferente:

| caminho | dizia ser | hoje |
|---|---|---|
| yt-dlp com disfarce | Chrome 146, macOS | Firefox 147 |
| yt-dlp sem disfarce | Chrome 149, Windows | Firefox 147 |
| instaloader | Chrome 142, **Linux** | Firefox 147, e com conexão de navegador |

Os cookies saem de um **Firefox**, então dizer Chrome era contradição que
navegador de gente não produz. Agora os três leem de `PERFIL_DE_DISFARCE` e
`IDENTIFICACAO_DO_NAVEGADOR`, no topo de `fluxo_downloads.py`. **O texto do
navegador foi medido contra um servidor local, não copiado de lugar nenhum**,
e medir de novo é o passo obrigatório antes de mexer nele.

**O instaloader ganhou o disfarce em 22/09, e ele é o que mais importa:** é
quem busca Story e quem descobre o número do perfil, os dois endereços mais
vigiados. Até essa data ele falava por biblioteca de Python comum, e o que
denuncia Python está **abaixo do HTTP**, na forma como a conexão segura é
aberta. Nenhum cabeçalho resolve isso. `disfarcar_sessao_do_instaloader()`
troca a sessão depois do `load_session`, **sempre depois, nunca antes**.

Três coisas que essa troca precisa continuar fazendo, e o teste
`teste_disfarce_do_instaloader.py` guarda cada uma:

- **Adaptar os cookies.** A biblioteca do disfarce entrega só o nome, em
  texto, e o instaloader espera percorrer objetos com nome e valor para achar
  o `csrftoken`. Foi assim que a primeira tentativa quebrou.
- **Recuar em erro de certificado, repetindo pela sessão de sempre.** A rede
  da empresa inspeciona tráfego seguro de forma **intermitente**: medido em
  22/09, o mesmo endereço recusou numa chamada e passou na seguinte. Nessa
  recusa a chamada nem chegou ao Instagram, então repetir não custa nada.
- **NÃO recuar em recusa do Instagram.** Se recuasse, uma recusa viraria duas
  chamadas, que é exatamente o padrão que marcou duas contas em agosto.

**Cada máquina diz o Firefox dela.** O perfil que a biblioteca oferece é de
Firefox no **macOS**, e nenhuma versão dela traz Firefox no Windows
(conferido em 22/09 na instalada e na mais nova, atualizar não resolve). Mas o
que vai escrito dá para acertar: `_montar_identificacao_do_navegador()` lê a
versão do Firefox instalado, sem abrir o navegador, e monta o texto dele.
Nesta máquina deu Firefox 155 no Windows.

O formato foi medido, não deduzido: o Firefox daqui foi aberto sem janela
contra um servidor local e mandou `rv:155.0 ... Firefox/155.0`, enquanto o
arquivo de instalação dizia `Version=155.0.1`. Daí a regra, só o número
principal seguido de `.0`. O `Windows NT 10.0` é assim mesmo em Windows 11, o
Firefox congelou esse pedaço.

**O que continua torto:** a forma como a conexão segura é aberta ainda é a do
perfil de macOS, porque essa parte quem decide é a biblioteca. Some se um dia
ela publicar Firefox no Windows.

**Se alguém trocar o navegador dos cookies**, o teste quebra de propósito:
`NAVEGADOR_COOKIES`, `PERFIL_DE_DISFARCE` e o texto do navegador precisam
continuar falando do mesmo navegador. Quem navega em Chrome fora do programa
não muda nada disso, porque o programa lê a sessão do Firefox, não a do
navegador que a pessoa está usando.

---

## 12. Manutenção dos baixadores (`baixadores.py`)

Três bibliotecas vigiadas: `yt-dlp` (principal), `instaloader` (reserva do
Instagram), `curl_cffi` (faz o programa se apresentar como navegador).

`DIAS_ATE_ENVELHECER = 45`. Só o yt-dlp versiona por data, então só ele tem
idade calculável pela própria versão; para os outros o relógio é o tempo desde
que aquela versão apareceu nesta máquina.

**A versão travada no `requirements.txt` é `yt-dlp==2026.7.4`, de 04/07/2026.**
Uma instalação nova **já nasce** com o aviso de velha. Atualizar é o passo 11 do
`INSTALAR.md`.

**Detecção de quebra:** lê `log_fluxo_completo.csv` na janela de 7 dias, **sem
gastar chamada ao Instagram**. Só levanta suspeita com 8+ tentativas, 3+ falhas
sem causa conhecida, e essas sendo a maioria.

**Plano B, quando o download não funciona:** baixar à mão e usar o **envio de
arquivo** na tela de Downloads. Esse caminho não depende de nenhuma biblioteca
de download.

---

## 13. Como o auditor quer que se trabalhe

Estas regras vêm de correções dele e valem sempre:

- **Sempre reconciliar números.** Atualizar achados para bater com o dado real
  verificado a cada etapa, sem esperar confirmação a cada rodada.
- **Usar o agente `verificador-auditoria` para validações.** Não recomputar na
  mão nem delegar a agente genérico.
- **Conferir a escrita de agente por conta própria.** Já houve agente reportando
  validação aprovada quando não era. Sempre reler o arquivo salvo.
- **Documentar fonte e limitação por achado.** Citar a fonte do dado e explicar
  na própria linha quando algo não foi encontrado ou está incompleto.
- **Nunca usar travessão** em texto de metodologia, observação ou recomendação.
  Trocar por vírgula ou ponto.
- **Sem jargão em texto visível.** Nada de "balde", "parser", "fallback",
  "bucket". Linguagem corrente.
- **Menos aviso na tela.** Ele reclamou disso pelo menos quatro vezes. Só o
  essencial, e sem texto explicativo longo.
- **Nunca dado pessoal de apostador** na conversa nem nos artefatos.
- **Nunca desligar verificação de TLS.**
- **Nomear versão em duplicata no Drive** com "NOVO" ou "ÚLTIMA VERSÃO" quando
  não é possível sobrescrever original de outro dono.
- Entregáveis de auditoria: nomenclatura `RA Nº XX/AAAA`, documento formal com
  versão e data, planilha de controle com uma linha por requisito.

---

## 14. Medições que valem como fato, para não re-derivar nem contradizer

| fato | medido em |
|---|---|
| escopo é a cota do CICLO, 156 de 156 | 04/09 |
| a coluna ESCOPO da Monitoramento não é foto congelada, 0 de 1.053 divergem | 07/09 |
| 18 influenciadores/dia, 15 com story; teto de 20 é por conta | 05/09 |
| Monitoramento real: 24.334 linhas, 21.361 com influenciador e ciclo | 07/09 |
| 822 de 1.057 ciclos saíam com período invertido ao ordenar data como texto | 07/09 |
| `Dados_influ`: 205 linhas, 76 ATIVO, 121 INATIVO, 4 EM ELABORAÇÃO/RENOVAÇÃO | 07/09 |
| Responsável A tem 9 influenciadores ATIVO; 3 em cache | 07/09 |
| publi: 69% no topo, 25% na base, bimodal | 07/09 |
| união quadro inteiro + faixa do topo: 19 de 160 quadros contra 14 | 07/09 |
| ganho por peça da faixa do topo: 2 em 60 (modesto) | 07/09 |
| 110s por vídeo com 2 processos; 185s com 1; 3 não ganha nada | registrado em `pipeline_influenciadores.py` |
| 11.185 linhas de lógica contra 4.361 de tela | 07/09 |
| a pasta `producao\analises` tem 49 MB, não 535 MB | 07/09 |
| 17 pacotes fixados no `requirements.txt` | 07/09 |
| `minicpm-v` ocupa 5,5 GB | 07/09 |

### Medido em 07/09/2026, na segunda parte do dia

| fato | onde confirmar |
|---|---|
| o intervalo entre ciclos consecutivos do mesmo influenciador tem mediana de **32 dias**, em 854 pares | é a base do prazo de idade da cópia da Monitoramento |
| a cópia da Monitoramento tem **23.334** linhas contra 24.334 da planilha viva | a cópia é de 19/08 |
| o cache tem **552 peças**, e só **2** são posteriores a 17/07/2026 | `ferramentas\medir_leitura_do_publi.py` |
| das 286 peças medidas, **201** têm "jogue com responsabilidade" e **0** têm a frase do Ministério da Fazenda | o banner mudou junto com a regra |
| publi lido em **18,5%** das peças; somando cinco variantes de pré-processamento, 20,3% | ganho de 5 peças, não paga o custo |
| **172 de 286** peças têm o rodapé lido e nenhum publi | 6 conferidas a olho: nas 6 o publi não está na peça |
| na Monitoramento, **19.557** linhas são anteriores a 17/07/2026 e **1.079** posteriores | 95% da base está no regime antigo |
| os dois pacotes do OpenCV são **obrigatórios**: rapidocr exige `opencv-python`, easyocr exige o `headless` | e gravam na mesma pasta `cv2` |

**Hipóteses testadas e derrubadas, para não voltarem como verdade:** composição
como significado de CRONOGRAMA (04/09); recortar para o OCR do rodapé (06/09);
PySceneDetect (data no diário); a suspeita de foto do escopo por linha (07/09);
pré-processar contraste no recorte do topo para ler mais publi (07/09, cinco
variantes, no máximo +1 peça cada); **girar o quadro para ler rodapé na vertical
(07/09, 0 peças ganham em 46 medidas)**.

---

## 15. Armadilhas conhecidas

**O trabalhador guarda o código em memória.** Reiniciar o Streamlit não basta:
encerre e suba o trabalhador também depois de mexer em módulo. Já aconteceu de
a régua nova não valer porque o trabalhador tinha subido antes da mudança.

**A tela não recarrega sozinha.** `fileWatcherType = "none"` no
`.streamlit\config.toml`, de propósito.

**`gravar_veredito` só escreve em célula VAZIA**, por desenho. Para reprocessar,
apaga-se a célula.

**Apagar a coluna `SITUACAO` remove a linha da fila de análise**, porque essa
coluna é o gatilho. Para limpar um veredito, apague `VALIDADO`.

**Heredoc de bash estraga `\n`.** Escrever Python por heredoc com `\n` dentro de
string produz `SyntaxError`. Use a ferramenta de edição de arquivo, ou
`chr(10)`.

**`Start-Process` do PowerShell não abre janela neste ambiente.** Para subir os
processos, use o mecanismo de segundo plano do próprio terminal.

**Encoding do console é cp1252.** Prefixe `PYTHONIOENCODING=utf-8` ao rodar
Python que imprime acento, e nomes de arquivo com acento precisam ser tratados
em Python, não em bash.

**O teste que estuba função errada gasta cota do Instagram.** Já aconteceu:
mudar qual função é chamada tornou o stub antigo inerte e o teste bateu no
Instagram, gastando 11 chamadas. A bateria hoje consome **zero**.

**"SEM ACESSO À PASTA" logo depois do upload é janela de propagação do Drive,
não falta de permissão (medido em 22/09/2026).** O vídeo sobe pelo token de
ESCRITA (`drive_file_token.json`, escopo `drive.file`) e, segundos depois, a
análise tenta lê-lo pelo token de LEITURA (`drive_token.json`, escopo
`drive.readonly`), que é outra autorização. O Google leva alguns segundos
para tornar o arquivo recém-criado visível para uma autorização diferente da
que o criou, e nessa janela a leitura volta **404**.

O que transforma isso em rótulo permanente: `_com_retentativas`, em
`drive_client.py`, só repete em erro de rede (`SSLError`, `ConnectionError`,
`TimeoutError`, `OSError`). `HttpError` não herda de nenhum desses, então o
404 falha de primeira, sem nenhuma segunda tentativa. O resultado vira
"SEM ACESSO À PASTA" e, como `gravar_veredito` só escreve em célula vazia, a
linha nunca mais é reanalisada sozinha.

MEDIDO, na Monitoramento de teste, em 22/09/2026:

| linha | analisada às | arquivo criado às | resultado |
|---|---|---|---|
| 99 @dudafreiret | 15:05 | 15:05:18 (mesmo minuto) | SEM ACESSO À PASTA |
| 100 @dudafreiret | 15:07 | mesma máquina, mesmos tokens | CONFORME |
| 101 @felipekersch | 15:16 | idem | CONFORME |

O mesmo arquivo da linha 99 abre sem problema pelo token de leitura quando
consultado depois, o que descarta permissão quebrada.

CONSEQUÊNCIA PARA QUEM LÊ A PLANILHA: essa linha não é conforme nem não
conforme, ninguém examinou a peça. Ela exige conferência humana, e é
diferente de "REQUER ANÁLISE HUMANA", que significa que o material FOI
acessado e só estava degradado demais para ler.

CORRIGIDO EM 22/09/2026: `processar_linha`, em `pipeline_influenciadores.py`,
repete a busca do material até 3 vezes, esperando 5 segundos, quando o erro
é 404 ou 403 da API do Drive (`_e_janela_de_propagacao`). Qualquer outro erro
continua falhando de primeira, porque repetir não mudaria nada. Pasta
legitimamente vazia também não repete. Teste:
`testes\teste_retentativa_acesso_ao_drive.py`.

O que a correção NÃO faz: desfazer linha que já foi carimbada antes dela.
As que já estão com "SEM ACESSO À PASTA" continuam assim até alguém apagar a
célula de VALIDACAO para reprocessar, porque `gravar_veredito` só escreve em
célula vazia.

---

## 16. O que foi feito em 07/09/2026

Cinco commits, todos no `main` (o repositório não tem remoto):

| commit | o que |
|---|---|
| `552968c` | régua fecha CONFORME; data como data; instalação conferida por comando |
| `7d65e76` | título das duas janelas diz qual é e se pode fechar |
| `d13b923` | teste que abre as cinco telas |
| `f5cdd97` | a correção de data estava pela metade em três lugares |
| `e365fca` | o `#publi` ganha a faixa dele, e a visão para de absolvê-lo |

Detalhe do que mudou:

1. **A régua passou a fechar CONFORME** nas três peças da @jojotodynho: regra do
   bloco do rodapé, e a visão recebendo a faixa ampliada em vez do quadro
   inteiro.
2. **Data como data**, em quatro lugares. Dois de manhã (contagem de POST e
   período do ciclo) e dois achados pela revisão da tarde (a contagem dos outros
   dias e a chave da cota). A regra virou `data_de_planilha.py`, um módulo só
   dela, e o piso do número de série passou a ser 01/01/2000, senão um `6`
   digitado virava 05/01/1900.
3. **Sem teto de 20.000 linhas** nas leituras da Monitoramento. A planilha real
   tem 24.334.
4. **O atalho subia a tela errada.** `iniciar_validacao_influenciadores.bat`
   subia `app_validacao_influenciadores.py`, uma das cinco telas, em vez do
   `painel.py`. Ninguém notou por semanas.
5. **O verificador de ambiente** passou a cobrir as seis faltas que não davam
   erro: cópia da Monitoramento, as cinco chaves do login, identificador dos
   fechamentos, registro do Netlex, cache de perfis e biblioteca envelhecida.
6. **`preparar_copia.py`**, novo: substitui a tabela de doze linhas de "não
   copie" do manual por um comando que pergunta antes de apagar.
7. **`INSTALAR.md` versão 3**, reescrito como passo a passo do que fazer.
8. **O `#publi`**: faixa do topo medida, união no OCR, e a régua voltou a
   exigi-lo.
9. **Limpeza da pasta:** 848 MB para 841 MB. Apagados 5 bundles de git
   superados, 8 pastas `__pycache__`, uma sessão antiga do Instagram e uma pasta
   duplicada de auditoria de saldos (confirmada por hash).

### Segunda parte do dia, depois deste arquivo ter sido escrito

1. **Reel e post de feed passaram a respeitar o freio da conta** (pendência 12).
   A tentativa autenticada não contava no teto do dia nem respeitava pausa.
2. **Perfil já conhecido deixou de gastar a chamada mais limitada** (pendência
   10), inclusive com a conta no teto.
3. **O aviso do OpenCV estava errado e virou conferência de versão.** Os dois
   pacotes são obrigatórios, e o que quebra é divergirem. Os dois estão travados
   no `requirements.txt` e há teste impedindo que sejam atualizados em separado.
4. **A cópia da Monitoramento passou a ser conferida por IDADE.** Existir e estar
   velha erram de jeitos diferentes, e o da velha é pior: vídeo posterior ao
   último ciclo conhecido recebe o número do **ciclo antigo**, em silêncio.
5. **A pendência do publi foi medida e reenquadrada.** Ver o item 7 das
   pendências: as duas saídas propostas não pagam, o achado provável é ausência
   real do publi, e nada disso pode ser transportado para a peça nova.
6. **`ferramentas\medir_leitura_do_publi.py`**, novo, para a medição poder ser
   refeita com material novo em vez de discutida de memória. Ele avisa quando a
   amostra é de banner antigo.

### 08/09/2026

7. **Reel e post de feed passaram a respeitar o freio da conta** (pendência 12),
   e **perfil já conhecido deixou de gastar a chamada mais limitada**
   (pendência 10).
8. **A trava do cliente da planilha** (`sheets_client`), depois de o trabalhador
   morrer com Segmentation fault. A corrida era anterior: a thread principal
   escreve veredito e a linha de download escreve na Monitoramento, as duas com
   o mesmo cliente do Google, que não é seguro para uso simultâneo.
9. **Link que fica esperando na fila baixa sozinho.** O trabalhador confere a
   fila quando está ocioso e cria a tarefa ele mesmo, 60s depois de o lote
   parar de crescer, com freio contra laço.
10. **A tela passou a mostrar as DUAS pausas.** Ela citava só a de 30 a 180s
    entre links, e existe a de 180 a 420s entre rodadas. Em uso real a pausa
    foi de 356s e pareceu travamento.
11. **A pergunta da visão sobre o publi passou a nomear o texto**, e o acerto
    foi de 67% para 100% em 27 peças com verdade conhecida. Ver a seção 7.
12. **`ferramentas\avaliar_pergunta_do_publi.py`**, novo, para essa conta poder
    ser refeita.
13. **`CLAUDE.md` na raiz do repositório**, com as regras que causam dano se
    violadas. Não existia.
14. **A visão passou a ter TRÊS estados**, e "não respondeu" deixou de ser lido
    como "não viu". Era o defeito mais caro que estava em pé: como visão-não
    produz NÃO CONFORME desde 07/09, **Ollama fora do ar geraria acusação**
    contra influenciador. O docstring ainda prometia falha segura. A leitura da
    resposta ficou liberal no sim e estrita no não, de propósito, e passou a
    reconhecer resposta em inglês (13 de 81 respostas reais vieram em inglês).
15. **A lista de termos do publi ampliada**, com a lista do auditor. Entraram
    `publipost` solto e `#anúncio`. O `#anúncio` vale **só com cerquilha**:
    "anúncio" é palavra corrente e aceitá-la solta faria peça sem declaração
    passar como declarada, que é o erro que perde achado. O `#anúncio` também
    entrou na pergunta da visão, para a forma poder ser confirmada dos dois
    lados. Remedido depois da mudança: segue 27 de 27.

**57 testes, todos passando, nenhum gastando chamada ao Instagram.** Os dois
testes novos foram conferidos contra a versão anterior do código, para provar
que reprovam o defeito em vez de passar sozinhos.

---

## 17. Pendências abertas, em ordem de importância

### Precisa de ação do auditor, não minha

1. **Revogar as credenciais soltas** em
   `producao\scripts\google_sheets_conector\` no console do Google, e só depois
   apagar os arquivos.
2. **Decidir o destino do zip de 105 MB** em `producao\backup\`: é a única cópia
   intacta do que o João entregou. Recomendação: mover para arquivo morto, não
   apagar.
3. **Perguntar ao Marketing o que significa CRONOGRAMA, e a pergunta ficou
   muito melhor em 08/09.** Não pergunte "o que é": pergunte
   **"por que LIVE é sempre SIM e quase todo NÃO é story da LOTTU?"**. Quem
   preenche responde isso numa frase.

   **Este item passou a bloquear o Financeiro**, e não por motivo técnico: é o
   único campo que ainda obriga o analista a abrir a planilha do Marketing.
   Enquanto isso, não há como cortar o acesso de escrita dele.

   O que o dado diz, medido em 08/09 nas 21.387 linhas com ciclo:

   | fato | número |
   |---|---|
   | SIM / NÃO / em branco | 83,5% / 4,4% (1.074 linhas) / 12,1% |
   | dos NÃO são STORIES | 96,7% |
   | LIVE marcado como NÃO | **zero**, em 4.115 LIVE |
   | dos NÃO são da LOTTU | 83,5%, contra 56,7% na base de SIM |
   | dos NÃO estão com PAGAMENTO Pendente | 77%, contra 46% na base |
   | taxa de NÃO por responsável interno | de 1,2% a 8,2%, aplicação desigual |
   | influenciadores com algum NÃO | 113 de 179, os 10 maiores somam só 34,5% |

   **Quatro hipóteses testadas, nenhuma confirmada.** Composição (04/09,
   derrubada). Post atrasado no ciclo (08/09, derrubada: a mediana da posição do
   post é 7 nos dois). Entrega excedente por tipo (08/09, derrubada: 92% dos NÃO
   estão em ciclos SEM nenhum excesso). Troca entre tipos de entrega (08/09,
   **não testável nesta fonte**, ver o item 7 abaixo).

   **A auditoria nunca usou esta coluna:** zero menção no relatório, nos
   dashboards e nas 7 abas do papel de trabalho.
4. **Perguntar ao Compliance** se conta própria da marca (`@lottubet.br`)
   precisa de `#publi`.
5. **Pedir ao Marketing uma coluna de Netlex na `Dados_influ`.**
6. **Conferir se o agente `guardiao-normativo-coso` aparece no `/agents`.**
   FEITO em 08/09: ele não carregava porque a descrição tinha `(ex: CMP.FLX.001`,
   e dois-pontos com espaço quebra valor YAML sem aspas. Corrigido, e ele
   aparece.
7. **A TROCA DE TIPO DE ENTREGA NÃO TEM RASTRO, E PODE AFETAR O ACHADO 1 DA
   RA 16, QUE JÁ FOI ENTREGUE.** Levantado pelo auditor em 08/09: é prática
   comum e combinada trocar entregas no meio do ciclo (contratou 6 stories e 4
   lives, o story rende mais, fecham 8 stories e 2 lives). **O contrato não
   muda, a entrega muda.**

   O problema: a palavra "troca" não aparece em lugar nenhum da metodologia do
   Achado 1 nem do parecer. E o item 3 daquela metodologia descarta 7 suspeitos
   de falso positivo com o raciocínio de que "os itens faltantes são de
   categorias que o influenciador nunca postou em nenhum ciclo". Sob a prática
   da troca, isso é exatamente a assinatura de uma **troca permanente**. A mesma
   evidência sustenta as duas leituras, e a auditoria escolheu uma sem saber que
   a outra existia.

   Isso **não** significa que os 134 desvios estejam errados. Significa que uma
   parte pode ser troca aceita, e que dá para verificar: comparar o escopo
   original no **Netlex** contra o escopo atual no cadastro. Onde diferirem,
   houve troca. Decisão do auditor, porque a RA 16 já foi entregue.

   Por que não dá para medir na Monitoramento: a coluna ESCOPO carrega o escopo
   **atual do cadastro**. Se o Marketing atualiza o cadastro ao combinar a
   troca, a troca desaparece do dado.

### Bloqueia o modo real, achado em 24/09/2026 (não bloqueia subir a VM)

**O escopo `drive.file` da credencial de escrita não vê a árvore real do
Marketing, nem com os parâmetros certos de Drive Compartilhado.** Testado ao
vivo, contra a pasta real "VÍDEOS INFLUENCIADORES" (é um Drive Compartilhado,
tem `driveId`): a credencial de leitura (`drive_token.json`) vê o conteúdo
sem problema; a credencial de escrita (`drive_file_token.json`, escopo
`drive.file`, `_drive_credenciais/autorizar_drive_escrita_arquivo.py`)
devolve lista vazia, mesmo passando `supportsAllDrives`/
`includeItemsFromAllDrives`/`corpora=allDrives` na query.

**Por que, e por que não é bug de parâmetro esquecido:** `drive.file` foi
escolhido de propósito no parecer de segurança de 29/08/2026, exatamente
para essa credencial só enxergar o que o próprio programa cria, nunca a
árvore de quem não é o programa. Isso protege perfeitamente o modo teste (a
árvore ali É criada pelo programa, sempre). CONFERIDO PELO `verificador-
auditoria` EM 24/09/2026: `drive_client_upload.listar_arquivos` nem chega a
passar `supportsAllDrives`/`includeItemsFromAllDrives` na consulta, então o
código de produção falharia contra Drive Compartilhado por esse motivo
isolado, além do de escopo. No modo real, a bet e o restante
da árvore já existem, criados pelo Marketing, e por isso ficam invisíveis
para essa mesma credencial: `_descer_criando`/`descer_pelo_caminho`
(`fluxo_downloads.py`) usa `drive_client_upload.listar_arquivos` (escopo
`drive.file`) tanto para achar quanto para criar pasta, e "achar" é
exatamente o que esse escopo não consegue fazer fora do que ele mesmo
criou.

**Consequência se o modo real for ligado sem corrigir isso:** toda
organização de vídeo falharia achando que a pasta da bet não existe (não é
que não existe, é que esta credencial não pode vê-la).

**Caminho proposto, ainda não implementado nem testado contra o Drive real:**
usar a credencial de LEITURA (`drive_client.py`, escopo mais largo, já
comprovado que alcança esse Drive Compartilhado) para achar o ID de cada
pasta que já existe, e só entregar esse ID à credencial de escrita na hora
de criar o que falta ou subir o arquivo. Mantém a proteção original (a
escrita continua sem poder *listar* o Drive real por conta própria) e
resolve a navegação. Falta confirmar se `drive.file` aceita criar um filho
dentro de um ID de pasta que a própria credencial nunca viu antes; a
documentação do Google sugere que sim (a restrição é sobre listar/ler, não
sobre para onde criar), mas isso não foi testado aqui, de propósito, para
não escrever no Drive real fora do modo autorizado.

**Não trava a subida da VM nem os testes de hoje**, que continuam em modo
teste. Só precisa estar resolvido antes de alguém criar os três arquivos de
`marketing_producao\` e ligar a escrita de verdade.

### Trabalho técnico, com escopo claro

8. **O publi: as duas saídas propostas foram medidas e não pagam. A pergunta
   original continua sem resposta, e só peça nova pode respondê-la.**

   Medido em 07/09 sobre 286 peças do cache, com o teste reproduzindo a linha de
   base de 23% que estava escrita aqui. Cinco variantes de pré-processamento no
   recorte do topo, contraste puro, contraste com ampliação, contraste forte,
   binarização e nitidez: **cada uma acrescenta no máximo 1 peça**, e somando
   todas o ganho é de 5 peças, de 18,5% para 20,3%. Não vale o custo de cinco
   passadas de OCR. A outra saída, amostrar mais quadros só na faixa do topo,
   não é mensurável no cache, porque o vídeo de origem não fica guardado.

   **O que a medição achou no lugar:** em **172 das 286 peças** o programa lê o
   rodapé e não acha publi nenhum. O rodapé é o texto mais fino da tela, então
   nessas peças está provado que o OCR funcionou. Seis peças foram conferidas a
   olho, uma a uma: nas seis o publi **não está na peça**, e em quatro delas o
   rodapé está inteiro, nítido e legível. Isso aponta para ausência real, não
   para leitura fraca, e é matéria de conformidade, sujeita à validação de quem
   é da área, não defeito do programa.

   **O limite disto, e é o que importa mais:** essas 286 peças são de fevereiro
   a maio de 2026, do banner ANTIGO. Medido no mesmo lote: 201 peças trazem o
   "jogue com responsabilidade" e **0 trazem a frase do Ministério da Fazenda**.
   O cache inteiro tem só **2 peças** posteriores a 17/07/2026. O banner mudou
   junto com a regra, então nada disso pode ser transportado para a peça que o
   Marketing vai analisar agora. **A medição precisa ser refeita quando houver
   peça nova em volume**, e o script que faz isso já existe, é só apontar para o
   material novo.
9. **A aba `Fechamentos` não é criada** pelo `registro_fechamentos.py`, e
   `ler()` nunca é chamado, então o histórico na tela sai só do CSV local.

   **DESENHO DO FINANCEIRO: PARADO EM 08/09, ESPERANDO O MARKETING.** A conversa
   de desenho aconteceu e foi interrompida de propósito, porque construir sem a
   resposta do item 3 entregaria 90% e deixaria a trava principal de pé. O que
   já ficou decidido, e vale quando ela voltar:

   **Para que a tela serve**, dito pelo auditor: é o Marketing conferir se a
   entrega está sendo feita e se o prazo está sendo respeitado, e no fim
   **autorizar** o setor responsável a pagar. **O setor Financeiro só executa o
   pagamento, mais nada.**

   **Decidido: a troca de tipo de entrega passa a ser registrada**, com quem
   autorizou, e aí o ciclo fecha sem virar desvio. Hoje essa prática não deixa
   rastro nenhum (ver item 7).

   **Decidido por consequência: `PAGAMENTO` sai do caminho.** Se o Financeiro só
   paga, quem marca `Realizado` não é o analista de Marketing, e o dado real
   está no Sankhya. A tela produz autorização, não status de pagamento.

   **O caminho escolhido foi o A, dos três avaliados:** espelho diário completo
   das colunas que a tela precisa, a tela lê o espelho, e a permissão do
   analista na planilha do Marketing vira somente leitura. É o único dos três
   que **impede** edição por fora em vez de só desencorajar.

   **Duas coisas que a investigação de 08/09 derrubou e economizam trabalho:**
   o `sincronizar_planilha_marketing.py`, que já roda diariamente por Tarefa
   Agendada do Windows (`EGB_Auditoria_SincronizarPlanilhaMarketing`), **não
   serve** como esse espelho: ele copia só as colunas A a E e só linhas com
   link. E o lado da escrita **já está certo**: a tela só grava na planilha
   própria de fechamentos e num CSV local, nunca na Monitoramento, e há teste
   provando.

   **A régua de prazo já existe e está medida**, no Achado 2 da RA 16: o
   pagamento não é por ciclo nem por fim de mês, é por **janela de emissão de
   NF**, seis janelas por mês, complementar ao dia fixo do contrato. Medido:
   385 títulos, 174 desvios, 130 atrasos e 44 antecipados. A tela pode usar essa
   régua, mas a NF vive no Sankhya, fora da planilha.
10. **`use_container_width`**, 28 ocorrências, API anunciada para remoção em
   31/12/2025, data que já passou. Funciona no Streamlit 1.59.2 e quebra numa
   atualização. O teste `teste_as_telas_abrem.py` impede o número de crescer.
11. **FEITO em 07/09/2026. O perfil já conhecido deixou de gastar a chamada mais
    limitada.** A descrição antiga apontava para `aprender_perfil_por_link`, mas
    o buraco estava um nível abaixo, em `userid_e_handle_por_link_de_post`: no
    link curto (`instagram.com/p/CODIGO`, o que o botão de compartilhar gera) o
    @ não está no endereço, então não havia o que consultar no mapa de perfis.
    A tentativa anônima, que é de graça e acontece antes, costuma trazer o @
    mesmo quando não traz o número. Agora o mapa é consultado com esse @, e
    perfil conhecido responde sem falar com o Instagram, **inclusive com a conta
    no teto do dia**. Teste: `teste_perfil_conhecido_nao_gasta_chamada.py`.
12. **A releitura da fila no fim da rodada** pode não pegar link novo se a
    rodada encerrada não tinha link do Instagram.
13. **FEITO em 07/09/2026. Reel e post de feed passaram a respeitar o freio da
    conta.** Em `baixar_video`, a tentativa autenticada, que manda os cookies e
    portanto é a conta falando, não passava por proteção nenhuma: ignorava pausa
    ativa, não entrava no teto do dia, e o programa seguia achando que tinha
    folga. Era o **mesmo** buraco tapado no caminho do Story em 29/08/2026, que
    não chegou aqui porque Story tem função própria e Reel e post dividem esta
    com YouTube, TikTok e X. A tentativa anônima continua de graça, que é o
    certo, e o teto continua sendo só do Instagram. Teste:
    `teste_reel_e_post_passam_pelo_freio.py`.
14. **`producao\scripts\excel_tecnico\` tem 98 arquivos**, sendo 3 reutilizáveis
    e 95 correções pontuais, com 10 referenciados por outros arquivos. Merece
    organização cuidadosa, não exclusão: script que produziu número entregue é
    rastreabilidade.
15. **A mídia do cache tem 451 MB** em 326 pastas `linha_NNN`. Não foi
    confirmado se o programa reextrai os quadros ou reaproveita, então apagar
    pode deixar reanálise mais lenta.
16. **Aquecer o cache de 6 influenciadores da Responsável A**: `@oficialmaga`,
    `@eduardagutierrez`, `@lilisantanaoficial`, `@marimenezees_`,
    `@felipekersch`, `@inhuiii`. Precisa de um link de Reel ou post de cada um.

### Fase de servidor

17. Falta a capacidade exata da máquina e três dependências de outras áreas.
18. No servidor não há navegador, então o arquivo de cookies passa a ser o
    caminho único e alguém tem de renová-lo periodicamente.
19. `preparar_servidor.ps1` pede 16 GB de memória e 60 GB livres.
20. **CORRIGIDO EM 25/09/2026, em TRÊS rodadas, cada uma achada testando a
    anterior. `obter_ou_criar_pasta` (`_drive_credenciais/drive_client_upload.py`)
    e `descer_pelo_caminho` (`fluxo_downloads.py`) deixavam organizar o
    mesmo vídeo em árvores de pasta diferentes.** Descoberto ao investigar
    por que 2 links de @carlinhos geraram 3 linhas na Monitoramento:
    existiam DUAS pastas "03. LOTTU" na raiz de teste, criadas em DIAS
    diferentes (22 e 23/09, sobra de dois dias de teste que nunca se
    encontraram). Um arquivo achou a LOTTU errada, criou uma segunda árvore
    inteira só pra ele, e saiu "SEM ACESSO À PASTA" na análise.

    **PRIMEIRA RODADA:** busca e criação de `obter_ou_criar_pasta` passaram
    a ficar dentro do mesmo `trava.travar()`. Resolve corrida de verdade
    (duas chamadas ao mesmo tempo), mas o caso real medido não tinha
    corrida nenhuma no relógio, então não bastou.

    **SEGUNDA RODADA, minutos depois: aconteceu de novo.** Duas pastas
    "story" para @eduardagutierrez, criadas com 751 MILISSEGUNDOS de
    diferença, já dentro da trava. `obter_ou_criar_pasta` ganhou um cache
    persistente (`teste_watch_folder/pastas_conhecidas.json`): resolve uma
    vez, grava, nunca mais busca ao vivo para aquele par (pasta-mãe, nome).

    **TERCEIRA RODADA, outra vez minutos depois: o mesmo vídeo de
    @weslleyof_ caiu em duas árvores, mesmo com a trava E o cache das duas
    rodadas anteriores já ativos.** A causa real: o cache de
    `obter_ou_criar_pasta` só é consultado no caminho de CRIAR.
    `descer_pelo_caminho` acha pasta que JÁ EXISTE por uma busca ao vivo
    (`listar`/`files().list`) a cada chamada, sem nunca ler nem gravar
    nesse cache. Com "03. LOTTU" já duplicada, essa busca podia devolver
    uma pasta ou a outra em ordem diferente a cada chamada, e cada chamada
    corria o risco de escolher errado de novo, mesmo já tendo escolhido
    certo antes. Corrigido: `drive_client_upload` ganhou
    `pasta_conhecida()`/`lembrar_pasta()`, lendo e gravando o MESMO cache;
    `descer_pelo_caminho` consulta `pasta_conhecida` antes de listar, e
    grava com `lembrar_pasta` assim que acha algo por listagem, não só
    quando cria. Teste: `teste_cache_evita_escolha_inconsistente.py`,
    reproduzindo a listagem em ordem trocada a cada chamada e provando que
    a segunda chamada nem lista mais.

    **O que ainda fica sem solução, mesmo com as três rodadas:** as pastas
    DUPLICADAS que já existiam antes de hoje (a LOTTU de 22/09, e o que já
    foi organizado nas árvores erradas antes da correção) não são desfeitas
    por este código, só passam a não crescer mais a partir de agora. Juntar
    o que já existe continua precisando de ação manual, e mover ou apagar
    arquivo entre pastas continua bloqueado pelo achado do `drive.file`
    (seção "Bloqueia o modo real": nem `files.update` nem `files.delete`
    funcionam nessa credencial para conteúdo que ela não "reconhece" como
    seu).

    **Não é risco para a pasta de bet nem de ano NO LAYOUT DO MARKETING**,
    essas nunca são criadas pelo programa ali (`_descer_criando`), só
    navegadas. **NO LAYOUT DE TESTE, É RISCO SIM** (e foi o que aconteceu),
    porque ali "tudo é criado, porque a árvore é nossa": bet e ano entram
    na lista do que pode ser criado. No layout do Marketing, o cache ainda
    vale para o que sobra criável ali (a pasta do MÊS, e a pasta de um
    influenciador na primeira publicação), e agora também para os níveis
    que só são ACHADOS (bet, ano, mês quando já existem).

---

## 18. Comandos do dia a dia

```
py verificar_ambiente.py                    # o ambiente está completo
py baixadores.py                            # a peça que baixa está velha
py preparar_copia.py                        # limpar estado de outra máquina
for %f in (testes\*.py) do py "%f"          # os 70 testes (contagem desatualizada há tempo; conferido em 12/09)
py -m streamlit run painel.py               # a tela, pela porta certa
py trabalhador.py                           # quem baixa e analisa
py -m pip install --upgrade yt-dlp          # atualizar o baixador
py testes\teste_download_em_duas_etapas.py  # confirmar depois de atualizar
```

## 19. Terceiro layout de pastas, para a analista de FUTEBOL (12/09/2026)

O programa vai ganhar uma instalação separada para a pessoa que cobre sozinha
a categoria FUTEBOL. Ela usa Monitoramento, Dados_influ e Calendário
compartilhados com o resto do time, mas organiza o Drive dela do jeito dela,
num Drive à parte do Marketing.

**Estrutura medida (22 pastas de influenciador lidas, com acesso de leitura
concedido pelo auditor):**

```
[pasta do influenciador] / DIVULGAÇÕES / MM. MÊS / arquivo
```

Sem bet, sem ano, sem pasta de dia, sem tipo, sem marcação. `LAYOUT_PASTAS_DRIVE=futebol`
liga esse layout (`LAYOUT_FUTEBOL` em `fluxo_downloads.py`).

**A pasta do influenciador não tem relação com o @** (ex. "Rafa Lira" para
@rafalirarl, "Central do Timão" para @centraldotimao). A Dados_influ só guarda
o @ (coluna INFLU), sem nome de exibição, então o programa não tem como
adivinhar. Por isso existe um mapa próprio,
`teste_watch_folder/pasta_por_handle_futebol.json` (`ARQUIVO_PASTA_FUTEBOL`),
@ → nome exato da pasta. Sem entrada no mapa, o programa para e explica, nunca
inventa pasta nova. **O seed inicial com 21 entradas, construído lendo o Drive
dela em 12/09/2026, foi entregue fora do repositório** (o arquivo é local por
máquina, como todo identificador deste projeto) e precisa ser copiado para essa
instalação.

**Variação já medida, e por isso tolerada:** "DIVULGAÇÕES" e "DIVULGAÇÃO"
(Leo Lima, no singular), com e sem espaço sobrando no nome. Pastas irmãs
(CONTRATO, PLANEJAMENTO, DOCUMENTOS, e ao menos uma pasta ad-hoc) são
ignoradas, porque o programa só desce pelos segmentos que ele mesmo monta.

**Política de criação:** só o mês pode ser criado (`niveis_criaveis = 1` em
`_pasta_de_destino_drive`). A pasta do influenciador (achada pelo mapa) e a
DIVULGAÇÕES (estrutural, uma vez por pessoa) nunca são criadas sozinhas; se
faltarem, o programa para e diz qual falta, em vez de inventar a estrutura.

**PENDÊNCIA, precisa de ação do auditor ou dela:** `Renata Saporito` não tem
pasta DIVULGAÇÕES nenhuma (só CONTRATO e DOCUMENTOS), e não foi possível achar
o @ dela por não haver nenhum vídeo já baixado em nenhuma pasta dessa árvore.
Fica sem entrada no mapa até alguém confirmar o @ e ela ter o primeiro
conteúdo.

**O que ainda falta, fora do layout de pastas:** conta própria dela no
Instagram, fila de downloads própria, e o identificador da pasta raiz do
Drive dela (`drive_pasta_raiz_id.txt`, apontando para
`1tn5H0HXM_0zKOdOaFBiNP0gtmPsMCP-F`, "Planejamento Influ e Relatórios Social
Futebol 2025"). Teste: `teste_pastas_do_futebol.py`.

**Achado lateral, fora do escopo desta mudança:** a pasta raiz e várias
subpastas (incluindo `Luisinho`, `Formiga`, `Marcelinho Carioca`, `1.
Relatórios`, o atalho `DADOS GERAIS`) pertencem a `desligados@empresa.com`,
uma conta já desligada da empresa. Vale confirmar com quem administra o Drive
institucional se há risco de retenção, antes de depender dessa árvore a longo
prazo.

## 20. Reforma de telas antes da instalação na analista (14/09/2026)

Pedido do auditor, antes de instalar na máquina da analista de Marketing:
menos planilha crua exposta, menos jargão, e uma proteção nova contra
reprocessar vídeo já com veredito sem motivo. Plano completo em
`C:\Users\auditor\.claude\plans\rosy-marinating-puzzle.md`.

**Downloads:** "Baixar de novo" agora distingue sucesso de falha
(`fluxo.e_status_sucesso`). Falha continua reabrindo com um clique; linha que
já teve sucesso exige motivo, gravado em `ARQUIVO_REBAIXAMENTOS` e no log
geral (`estagio="reabertura"`). O campo Ciclo virou um texto e um placeholder
únicos nos quatro formulários (`fluxo.ajuda_campo_ciclo`,
`fluxo.PLACEHOLDER_CAMPO_CICLO`). Os atalhos "Abrir a Monitoramento"/"Abrir a
pasta" saíram, junto com a seção inteira "Organizado no Drive" (a limpeza de
teste continua por `ferramentas\limpar_teste.py`). O atalho do Calendário
ficou, sozinho, por ser feature própria de 11/09. A caixa "Analisar assim que
baixar" saiu: analisar virou sempre automático, porque desmarcá-la era um
jeito de um vídeo nunca ser analisado sem motivo nem registro, com a tela de
escolher manualmente saindo do programa (ver próximo item).

**Validação Regulatória saiu do menu.** `app_validacao_influenciadores.py`
foi apagado. O motor (`pipeline_influenciadores.py` + `trabalhador.py`)
continua rodando sozinho, fora do Streamlit; download já encadeia análise. O
que sobrava de essencial (acompanhar, tirar da análise, devolver, tentar de
novo) migrou pra dentro do Monitoramento, bem mais simples, junto com a
remoção da seção "Detalhe da validação" que já morava lá (não na tela que
saiu) e do botão "Abrir a planilha no Google Sheets".

**Financeiro** ganhou uma "Nota do Financeiro sobre este escopo", sempre
visível, sem gerar texto de WhatsApp nem "Solicitar pagamento" (isso
continua desligado, `FECHAMENTO_DE_CICLO_ATIVO = False`). Grava numa aba
nova, `Notas_Financeiro`, na mesma planilha de fechamentos
(`registro_fechamentos.py` ganhou parâmetro `aba=`).

**Cadastro** perdeu o Netlex inteiro (coluna calculada e consulta de
histórico; `contratos_netlex.py` continua existindo, só a exibição saiu) e
ganhou correção controlada de campo, célula por célula, num módulo novo
`cadastro.py` (`corrigir_campo_no_cadastro`), no mesmo padrão de
`corrigir_ciclo_na_monitoramento`: lê antes de gravar, só grava se mudou de
verdade, recusa coluna de dado pessoal por conta própria, registra no log.

**Testes:** os 70 continuam passando; `teste_cadastro_somente_leitura.py`
mudou de premissa (não é mais "nunca escreve", é "escreve só pelo caminho
golden") e ganhou duas seções de comportamento de verdade.

## 21. Correções de teste ao vivo e nova régua de quantidade (16/09/2026)

**Registro de link (Downloads):** um teste real com link do YouTube achou
cinco lacunas na mesma linha da Monitoramento, todas em `registrar_link_externo`
e `registrar_na_monitoramento`, `fluxo_downloads.py`. Corrigidas: VALIDACAO e
VALIDADO_EM passam a gravar "N/A", e EVIDENCIA o próprio link, quando a linha
nunca vai ser analisada (`analisavel=False`); PEDIDO_POR (coluna AC) estava
sempre vazio, porque a função nunca recebia `quem`; Horas de live (coluna U)
era descartada em silêncio sempre que o tipo escolhido não era LIVE, mesmo
com o campo preenchido, agora é gravada sempre que válida; e o Calendário de
Divulgações nunca era atualizado por este caminho (só pelo download), agora
`registrar_no_calendario` é chamado também aqui (Status e "Monitorado por").
**A coluna Horário do Calendário continua vazia neste caminho, de propósito**:
um campo novo para digitá-la foi tentado e descartado no mesmo dia, a pedido
do auditor, porque não fazia parte do pedido original e ninguém tem como
descobrir essa hora sem o vídeo. `normalizar_horas_live` passou a aceitar só
os dígitos, sem dois-pontos ("013000"). O campo Influenciador virou seletor
com as opções do
cadastro (`fluxo.handles_do_cadastro`), com um campo de texto de escape para
quem ainda não está lá.

**Financeiro, regra de quantidade do ciclo mudou para TOTAL** (era por tipo).
Depois de três exemplos reais puxarem em direções diferentes, a régua final
foi "qualquer coisa pode compensar qualquer coisa": a quantidade fecha
somando TODOS os tipos entregues contra TODOS os contratados, não mais tipo
por tipo. STORIES ganhou atenção própria, à parte: uma queda nela vira achado
e exige justificativa mesmo quando o total do ciclo fecha, porque "as
entregas principais são stories". `fora_do_escopo` (tipo entregue fora do
contrato) continua sendo outra pergunta, sobre composição, e continua
exigindo justificativa por conta própria. Ver `escopo_e_entrega.fechar_ciclo`
e `testes\teste_qualquer_tipo_compensa_o_total.py`.

**Financeiro, "Notas_Financeiro" virou "Historico_Entregas".** A aba tinha
nascido um dia antes (15/09) só para nota de consulta; agora guarda a
fotografia inteira do fechamento (situação, total contratado, total
entregue, o que faltou, quem e quando), com a nota de justificativa como só
mais um campo, que pode ficar vazio. O botão "Registrar no histórico" passou
a aceitar registro sem nota nenhuma quando não há nada a justificar (antes
exigia texto sempre), e uma tabela filtrada pelo influenciador selecionado
aparece embaixo, no mesmo padrão que a Monitoramento já mostra dentro do
Monitoramento.

**Cronograma pro WhatsApp: sem menção a "auditoria", e sem nota de
comparação.** A mensagem que vai para o Marketing parou de citar "a
auditoria" (a ferramenta passou a ser deles; quando a auditoria voltar a
examinar isto, será como conferência externa e independente) e parou de
levar a explicação entre parênteses de cada divergência (⚠️/❌/nota "o
Calendário marcou X"). A EXCEÇÃO é "sem linha no Calendário": essa nota
continua na mensagem, porque não é uma comparação, é avisar que não existe
linha com que comparar. A explicação completa de cada divergência continua
na tela interna do Financeiro, para quem confere antes de mandar; só não vai
mais para o texto que sai daqui.

## Documentos do projeto

| arquivo | o que é |
|---|---|
| `COMECE_AQUI.md` | este arquivo, o estado atual |
| `PROMPT_CONTINUACAO.md` | o diário cronológico, 2.474 linhas, para achar o porquê de decisão passada |
| `INSTALAR.md` | instalação numa máquina nova, versão 14 |
| `README.md` | visão geral |
| `ARQUITETURA.html` | documentação do código |
| `.gitignore` | lista de **permissão**, e o comentário no topo explica por quê |
