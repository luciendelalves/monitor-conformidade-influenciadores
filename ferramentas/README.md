# Ferramentas de conferência

Perguntas que voltam, respondidas em segundos em vez de num script novo.

Criadas em 02/09/2026. No dia anterior foram escritos cerca de quinze scripts
descartáveis para responder perguntas de conferência, e metade delas são
perguntas recorrentes. Pior que o tempo: duas medições do mesmo Drive no mesmo
dia deram números diferentes, porque uma contava influenciador que já saiu da
casa e a outra não. **Ferramenta versionada responde sempre a mesma pergunta**,
com o recorte escrito no código em vez de na memória de quem rodou.

Todas rodam de dentro de `producao\analises`.

---

## Regras desta pasta

**Tudo aqui é somente leitura, com uma exceção**, que está no nome e no cabeçalho
dela: `limpar_teste.py`. Ferramenta de conferência que escreve por acidente é
pior que ferramenta nenhuma.

**Nenhuma fala com o Instagram.** A chamada ao Instagram é o recurso escasso do
programa, e conferência não pode gastá-lo. As que precisam de arquivo baixam do
Drive, pelo identificador que o cache de análise guarda.

---

## `ver_registros.py` — comece por aqui

O estado do programa agora: planilha, fila, log, cache, trabalhador e conta.

```
py ferramentas\ver_registros.py                  visão geral
py ferramentas\ver_registros.py @maumauzk        tudo o que existe dele
```

É a primeira a rodar quando algo parece estranho, porque ela responde **o que
existe** antes de qualquer teoria sobre o porquê. E mostra sempre as três coisas
que não podem ser apagadas por engano: a contagem de chamadas do dia, a conta
configurada e o mapa de perfis.

## `ver_analise.py` — o que a análise decidiu, e por quê

```
py ferramentas\ver_analise.py                    resumo por causa e por dia
py ferramentas\ver_analise.py @andersonneiff     item por item
py ferramentas\ver_analise.py causas             só o agrupamento por causa
```

O agrupamento **por causa** é o modo principal, e existe por um motivo medido: a
proporção de Requer Verificação não mede qualidade enquanto a amostra tiver
material que não é publicidade. Em 02/09/2026 a proporção estava em 100% e a
causa mostrou que 24 de 34 casos eram material de teste sem aposta.

## `ver_drive.py` — o que existe no Drive

```
py ferramentas\ver_drive.py arvore               árvore do Drive configurado
py ferramentas\ver_drive.py arvore @maumauzk     só as pastas dele
py ferramentas\ver_drive.py grafias              conta nomes de pasta, só ATIVOS
py ferramentas\ver_drive.py grafias todos        inclui quem saiu da casa
py ferramentas\ver_drive.py procurar story       onde há pasta com esse nome
```

O modo `grafias` é o que **decide nome de pasta** neste projeto, porque nome de
pasta sai de medição e não de escolha. Foi ele que mostrou que o padrão do
Marketing é `story`, minúsculo e no singular.

## `ler_com_ocr.py` — o programa errou, ou a peça não tem o aviso?

```
py ferramentas\ler_com_ocr.py @maumauzk              todos os arquivos dele
py ferramentas\ler_com_ocr.py "Tela 1"               por pedaço do nome
py ferramentas\ler_com_ocr.py C:\caminho\video.mp4   arquivo local
py ferramentas\ler_com_ocr.py @maumauzk rapido       só Tesseract
```

Mostra o que cada motor leu, quadro por quadro, e quais itens do aviso foram
reconhecidos. Em 02/09/2026 ela derrubou uma suspeita de defeito de leitura em
cinco arquivos de uma vez.

O EasyOCR é lento, cerca de 13 s por quadro no pior caso, e disputa CPU com o
trabalhador. Use `rapido` quando só quiser saber se há texto.

## `levantar_termos.py` — o mesmo termo em todas as peças

```
py ferramentas\levantar_termos.py portaria       qual número as peças citam
py ferramentas\levantar_termos.py publi          quais termos de publicidade
py ferramentas\levantar_termos.py fazenda        qual das três frases aparece
py ferramentas\levantar_termos.py "18\+"         qualquer expressão
```

Relê cada peça do cache e agrupa. O cache não responde isso sozinho porque ele
guarda só o pedaço que casou com o regex: a evidência diz `portaria: 'PORTARIA'`
e nunca o número.

Leva minutos com algumas dezenas de peças. Vale rodar em segundo plano.

## `limpar_teste.py` — **esta escreve**

```
py ferramentas\limpar_teste.py conferir           mostra o que existe, sem apagar
py ferramentas\limpar_teste.py tudo               apaga tudo
py ferramentas\limpar_teste.py @maumauzk          apaga só o material dele
```

Nunca apaga em definitivo no Drive: só lixeira, onde fica 30 dias. Guarda cópia
do log e do cache antes.

**Nunca apaga** a contagem de chamadas do Instagram do dia, o mapa de perfis, as
credenciais nem os identificadores. Zerar a contagem removeria a proteção contra
bloqueio de conta.

**Encerre o trabalhador antes.** Não é formalidade: ele guarda em memória os
identificadores das pastas do Drive, e com ele de pé o próximo download depois da
limpeza sobe **para dentro da lixeira**. A ferramenta recusa se detectar o
trabalhador trabalhando, e avisa se ele estiver de pé mas ocioso.

---

## `avaliar_pergunta_do_publi.py` — a pergunta à visão acerta quanto?

```
py ferramentas\avaliar_pergunta_do_publi.py
```

Mede a pergunta que está **em produção**, lida do próprio módulo, contra 27
peças com verdade conhecida: 12 positivos de graça (o OCR leu o publi, então a
marca está lá), 5 positivos conferidos a olho, e 10 negativos conferidos a olho.

Ela nasceu de um defeito de 08/09/2026. A pergunta do publi era a única do
dicionário que perguntava por **conceito**, "um selo ou marca indicando
publicidade", em vez de nomear o texto procurado como as outras cinco fazem. O
modelo respondia sim sempre que a faixa legal do rodapé caía no recorte, porque
ela é, literalmente, uma marca que indica publicidade autorizada. Ele respondia
a pergunta que recebeu.

| pergunta | acha o publi que existe | não inventa o que não há | geral |
|---|---|---|---|
| conceitual | 17/17 | 1/10 | **67%** |
| nomeando o texto | 17/17 | 10/10 | **100%** |

Rode ela quando alguém mexer na pergunta, trocar o modelo de visão, ou quando
houver volume de peça do banner novo: este conjunto é todo do banner anterior a
17/07/2026.

---

## `medir_leitura_do_publi.py` — vale mexer no OCR do publi?

```
py ferramentas\medir_leitura_do_publi.py                 as peças recentes
py ferramentas\medir_leitura_do_publi.py 2026-09-01      desde essa data
py ferramentas\medir_leitura_do_publi.py tudo            o cache inteiro
py ferramentas\medir_leitura_do_publi.py tudo 10         uma peça a cada 10
```

Roda sobre os quadros que a análise já deixou no cache, sem baixar nada. Leva
alguns segundos por peça, porque o OCR é a parte lenta.

Responde três coisas: quantas peças têm o publi lido hoje, quanto cada variante
de pré-processamento acrescentaria, e o cruzamento que decide a questão, que é
**em quantas peças o programa lê o rodapé e mesmo assim não acha publi**. O
rodapé é o texto mais fino da tela: onde ele foi lido, está provado que o OCR
funcionou, e a falta do publi ali aponta para peça sem publi, não para leitura
fraca.

**Ela diz de qual geração de banner é a amostra, e isso é o ponto.** O banner
mudou em 17/07/2026 junto com a regra, e medição feita em peça velha descreve
peça que não se publica mais. Quando a amostra é toda antiga, a ferramenta avisa
na cara antes de mostrar qualquer número. Foi assim que se descobriu, em
07/09/2026, que a pendência do publi estava apoiada em 286 peças de fevereiro a
maio, com **0** peças da regra nova.

---

## Uma armadilha destes arquivos, registrada porque morde em silêncio

Os textos de ajuda contêm caminhos do Windows, como `ferramentas\ver_drive.py`.
Em texto normal do Python, `\v` é **tabulação vertical** e `\l` é escape
inválido. A primeira versão destes arquivos teve o texto de uso corrompido: o
`\v` comeu a letra e virou `ferramentas\x0ber_drive.py`, sem erro nenhum.

Por isso **todo cabeçalho desta pasta é texto literal**, aberto com `r"""`. Há um
teste que falha se alguém tirar (`teste_ferramentas_de_conferencia.py`).
