# -*- coding: utf-8 -*-
r"""
Cruza o ESCOPO contratado com o que foi ENTREGUE, por ciclo.

O ESCOPO É A COTA DE UM CICLO, E ISSO FOI MEDIDO, NÃO SUPOSTO (04/09/2026)

Até aqui isto era só uma frase nesta docstring, e o auditor cobrou a diferença:
"vc não tá confundindo o pagamento do ciclo com o pagamento do escopo total?".
A pergunta é boa, porque o cadastro guarda UMA coluna de escopo por
influenciador, sem dizer se aquela quantidade é por ciclo ou o total do
contrato inteiro. Se fosse o total, comparar contra um ciclo só faria todo
ciclo parecer INCOMPLETO, e a régua estaria errada desde o começo.

A medição foi feita na Monitoramento real do Marketing (somente leitura,
autorizada): para os 156 influenciadores com 2 ciclos ou mais e escopo com
quantidade legível, comparou-se a quantidade contratada contra o que ele
entrega POR CICLO e contra o TOTAL somado de todos os ciclos.

    escopo mais perto do que se entrega por ciclo    156
    escopo mais perto do total de todos os ciclos      0

E em boa parte dos casos não é "mais perto", é exato: 18 contratados e 18 por
ciclo, 25 e 25, 12 e 12, 60 e 61. A conclusão é que o contrato NÃO tem cota
própria: ele define o período e quais ciclos existem, e a cota é do ciclo.

CONSEQUÊNCIA PARA QUEM LÊ ESTE ARQUIVO: não existe "escopo total do contrato"
a ser fechado nem pago. Há três níveis, e só o do meio tem cota: o link (uma
tela, com PAGAMENTO próprio na coluna S da Monitoramento), o ciclo (a cota, o
que fecha aqui) e o contrato (só o período). Onde o código diz "ciclo", é do
nível do meio que ele fala.

POR QUE ESTE ARQUIVO EXISTE, e por que ele é separado da tela (03/09/2026)

Pedido do auditor: uma aba de Financeiro que cruze as entregas com o ESCOPO da
Dados_influ e feche o ciclo com uma situação de pagamento. A conta é a parte que
tem regra, então ela fica aqui, testável sem abrir o Streamlit; a tela só mostra.

O MOLDE NÃO FOI INVENTADO. Ele é a aba `Achado01_EntregaEComprovacao` da planilha
de achados da própria auditoria (260 linhas), que já fazia esse cruzamento à mão:

    Influenciador | Período | Ciclo | Escopo Contratado (Completo) | Entregue |
    Não Entregue | Status Escopo | Status Comprovação | Observação (o que faltou) |
    Status Pagamento | Validação Data NF

E o vocabulário dela também é reaproveitado (✅ 🚫 ⏳), para as duas não
divergirem: quem lê o papel de trabalho e quem lê a tela têm que ver a mesma
coisa.

O QUE O DADO REAL OBRIGOU A TRATAR, medido no cadastro em 03/09/2026 (76 ativos,
69 com escopo preenchido, 59 textos distintos):

  1. o escopo é TEXTO LIVRE. O programa extrai a quantidade de 66 dos 69. Os
     três que sobram são "Não informado" e "Indefinido", que não são falha de
     leitura: ninguém preencheu.
  2. "COMBOS DE STORIES" aparece em 63 dos 69. O auditor definiu que 1 combo é
     1 POST DO DIA, o que casa com a coluna POST da Monitoramento, que desde
     03/09/2026 conta entrega do mesmo dia como um post só.
  3. PERIODICIDADE MISTURADA no mesmo texto: "MENSAL: 2 COMBOS DE STORIES /
     ANUAL: 6 POSTS NO FEED". O item anual não entra no fechamento do ciclo.
  4. ENTREGA ALTERNATIVA: "5 FEED (OU REELS)". Uma quantidade que pode ser
     cumprida por dois tipos.
  5. ITENS QUE DOWNLOAD NÃO MEDE: "2 diárias de gravação", "presença em
     eventos", "1 diária pra tráfego", "8 TWEETS". Eles NÃO são ignorados: vão
     para uma lista de conferência humana, senão o fechamento afirmaria
     conformidade sobre o que ele não olhou.

A REGRA DE QUANTIDADE MUDOU EM 16/09/2026: "QUALQUER COISA COMPENSA QUALQUER
COISA". Até aqui a régua era mais dura que a da planilha antiga: mudar a
composição (tipo do escopo sem nenhuma entrega, ou tipo entregue fora do
escopo) fechava a quantidade como incompleta mesmo com o total batendo. O
auditor testou dois exemplos que puxavam pra lados diferentes (falta de
stories coberta por sobra de feed/reels; depois 10 reels + 10 stories
contratados, entregou 9 reels e 11 stories, "isso está ok") e fechou a régua
pelo TOTAL: soma tudo que foi contratado contra soma tudo que foi entregue,
de qualquer tipo. Só o que sobrar depois dessa soma é falta de verdade
(INCOMPLETO). Ver `fechar_ciclo`, perto de "QUALQUER TIPO COMPENSA QUALQUER
TIPO".

TIPO FORA DO ESCOPO CONTINUA SENDO REGISTRADO (`fora_do_escopo`), e continua
pedindo justificativa: é outra pergunta, sobre COMPOSIÇÃO ("a pessoa entregou
algo que não é do contrato?"), não sobre volume. As duas perguntas convivem:
um ciclo pode fechar CONFORME em quantidade e ainda assim ter algo fora do
escopo para explicar.

STORIES PEDE ATENÇÃO À PARTE, mesmo com a régua de quantidade mais solta:
"as entregas principais são stories, por isso temos que ter atenção a isso".
Uma queda em stories vira achado próprio e exige justificativa, ainda que o
total do ciclo feche por outro tipo (ver "STORIES PEDE ATENÇÃO À PARTE" em
`fechar_ciclo`).

Na planilha antiga, 13 combos entregues contra 12 contratados fechou ✅. Isso
continua valendo: entregar MAIS DO MESMO tipo nunca foi problema, só faltar.

NADA AQUI ESCREVE EM PLANILHA. Este arquivo só calcula.
"""
import re

# O ÚNICO IMPORT DE MÓDULO DO PROJETO, e de propósito. Este arquivo é o motor da
# auditoria e não deve depender de tela, de rede nem do Google. O
# `data_de_planilha` importa só o `datetime` e existe justamente para a regra de
# leitura de data não ser escrita duas vezes.
import data_de_planilha

# ---------------------------------------------------------------------------
# O vocabulário do escopo, medido no cadastro
# ---------------------------------------------------------------------------
# Cada tipo aponta para os termos como eles aparecem escritos, do mais
# específico para o mais genérico. A ordem importa: "posts no feed" tem que ser
# testado antes de "post", senão o genérico captura o específico.
#
# O tipo é o mesmo vocabulário da coluna TIPO da Monitoramento (STORIES, REELS,
# FEED), de propósito: é por ele que os dois lados do cruzamento se encontram.
TERMOS_POR_TIPO = (
    ("STORIES", ("combos de stories", "combos stories", "combo de stories",
                 "combos", "stories", "storie", "story")),
    ("REELS", ("reels feed", "reels", "reel")),
    ("FEED", ("posts no feed", "post no feed", "publicações no feed",
              "publicacoes no feed", "feeds", "feed")),
    ("LIVE", ("horas de live", "horas live", "h de live", "hs de live", "live")),
    ("YOUTUBE", ("youtube", "video no youtube")),
    ("TIKTOK", ("tiktok",)),
    ("X/TWITTER", ("tweets", "tweet", "twitter")),
    ("FACEBOOK", ("facebook", "face")),
    ("THREADS", ("threads",)),
)

# TIPOS QUE A RÉGUA DA PORTARIA NÃO ALCANÇA, e isto NÃO é a mesma coisa que não
# existir a entrega (03/09/2026, medido no papel de trabalho).
#
# A entrega existe, é registrada na Monitoramento e pode ser contada. O que o
# programa não faz é VALIDAR: ele baixa e analisa peça do Instagram, e não post
# do X, vídeo do YouTube, TikTok ou Facebook. Na aba Achado03 do papel de
# trabalho isso está medido: 23 linhas de X/TWITTER com "NÃO FOI POSSÍVEL
# ANALISAR (LINK DE REDE SOCIAL)".
#
# POR QUE ISTO VIROU CATEGORIA PRÓPRIA: desde 31/08/2026 só peça CONFORME conta
# para a cota. Junte as duas regras e uma cota de 8 tweets NUNCA fecha, porque
# nenhum tweet vai receber veredito CONFORME. O ciclo ficaria eternamente
# incompleto sem ninguém entender por quê.
#
# O programa NÃO decide isso sozinho. Ele separa, conta, e quem fecha escolhe na
# tela se aquelas entregas contam. Decisão registrada, não inferida.
TIPOS_NAO_VALIDAVEIS = ("X/TWITTER", "YOUTUBE", "TIKTOK", "FACEBOOK", "THREADS")

# LIVE é medida em HORAS, e não em posts. "40 - Horas live" aparece 16 vezes na
# planilha de validação. Contar 40 como quantidade de posts faria a cota pedir 40
# entregas que nunca chegam, porque live não é post e não aparece na coluna TIPO
# da Monitoramento. Vai para conferência humana, com a quantidade à vista.
TIPOS_EM_HORAS = ("LIVE",)

# Itens que existem no escopo e que DOWNLOAD NÃO MEDE. Não são ignorados: viram
# lista de conferência humana. Medidos no cadastro e no papel de trabalho em
# 03/09/2026.
TERMOS_NAO_MENSURAVEIS = (
    "diária", "diarias", "diárias", "diaria", "gravação", "gravacao",
    "evento", "eventos", "viagem", "viagens", "tráfego", "trafego",
    "presença", "presenca", "disponibilidade", "marcação da logo",
    "marcacao da logo",
    # Achados no vocabulário real de Entrega-Contrato, em 03/09/2026.
    "cobertura", "collab", "collabs", "colab", "colabs",
)

# ESCOPO QUE PEDE PEÇA ORGÂNICA, COM QUANTIDADE. Aparece no dado real como "12
# POSTAGENS ORGÂNICAS", "14 postagens orgânicas mostrando a marca" e "14 - Post
# Orgânico". A peça orgânica é contada à parte porque não passa pela régua da
# portaria, então ela não pode entrar na mesma conta do link. Mas o contrato pede
# uma quantidade dela, e essa quantidade tem que ser comparada com o que veio.
TERMOS_ORGANICOS = ("orgânica", "organica", "orgânicas", "organicas",
                    "orgânico", "organico", "orgânicos", "organicos")

# TIPO GENÉRICO, que o contrato escreve sem dizer o formato: "20 - Videos",
# "4 VÍDEOS", "2 COLLABS". Não dá para saber se conta como reels, feed ou story,
# e chutar seria decidir a cota no lugar de quem tem o contrato. Vai para uma
# lista própria, com a quantidade, e a tela pede a escolha.
TERMOS_AMBIGUOS = ("vídeo", "video", "vídeos", "videos", "publicação",
                   "publicacao", "publicações", "publicacoes", "post", "posts")

# CONDIÇÃO ESCRITA NO ESCOPO. No dado real: "a partir do 2º mês 12 combos de
# stories". A quantidade só vale de um mês em diante, e o programa não sabe qual
# mês do contrato é o ciclo que está sendo fechado. Fica visível em vez de virar
# cota que cobra desde o primeiro ciclo.
REGEX_CONDICAO = re.compile(
    r"\b(a partir d[eo]|apos o|após o|do \d+º m[eê]s|somente|exceto)\b",
    re.IGNORECASE)

# Marca de periodicidade escrita no próprio texto. O item ANUAL não entra no
# fechamento do ciclo, e isso precisa ficar VISÍVEL em vez de virar silêncio.
REGEX_ANUAL = re.compile(r"\bANUAL\b", re.IGNORECASE)
REGEX_MENSAL = re.compile(r"\bMENSAL\b", re.IGNORECASE)

# "5 FEED (OU REELS)": uma quantidade cumprida por mais de um tipo.
REGEX_ALTERNATIVA = re.compile(r"\(\s*ou\s+([^)]+)\)", re.IGNORECASE)

# A OUTRA FORMA DE ESCREVER ALTERNATIVA, sem parênteses: "40 - Stories, reels ou
# feed". Achada no dado real em 03/09/2026, com 6 linhas na planilha de
# validação, e ela causava um erro grave: a vírgula partia o texto, o programa
# lia "40 STORIES" e jogava "reels ou feed" no lixo. Um ciclo que entregasse 40
# reels, dentro do que o contrato permite, fechava como NÃO CONFORME por mudança
# de composição, e ainda pedia justificativa de quem não fez nada errado.
#
# Precisa ser reconhecida ANTES de o texto ser partido por vírgula, e é isso que
# _achar_alternativas_em_lista faz.
REGEX_ALTERNATIVA_LISTA = re.compile(
    r"(\d{1,3})\s*[-–—:]?\s*"                      # a quantidade
    r"((?:[A-Za-zÀ-ÿ/]+\s*(?:,|\bou\b)\s*)+[A-Za-zÀ-ÿ/]+)",   # tipo, tipo ou tipo
    re.IGNORECASE)

# O TAMANHO DO COMBO, quando o contrato o declara. Achado no dado real em
# 03/09/2026: o escopo da @perlladecassia diz "18 COMBOS STORIES COM 3 TELAS
# CADA".
#
# POR QUE ISTO NÃO PODE SER IGNORADO EM SILÊNCIO. O auditor definiu que 1 combo
# é 1 post do dia, e a contagem usa a coluna POST. Isso casa com um combo de 3
# telas SE as três saírem no mesmo dia. Se saírem duas num dia e uma no outro, a
# contagem por post vê dois combos onde o contrato reconheceria um incompleto.
#
# O programa NÃO tenta resolver isso sozinho: ele conta por post, como o auditor
# definiu, e AVISA que aquele contrato declara tamanho de combo, para quem fecha
# conferir. Decidir se o combo partido em dois dias vale um ou dois é leitura de
# contrato, não de programa.
REGEX_TELAS_POR_COMBO = re.compile(
    r"com\s*(\d{1,2})\s*telas?\s*(?:cada)?", re.IGNORECASE)

# "12 COMBOS DE STORIES", "6 STORIES + 4 FEEDS", "60h de live". O número vem
# antes; o "h" de hora é absorvido para "60h de live" não virar quantidade 60 de
# um tipo desconhecido.
REGEX_QUANTIDADE = re.compile(r"(\d{1,3})\s*h?\s*(?:x\s*)?([^\d+,;\n]{2,40})",
                              re.IGNORECASE)

SEM_ESCOPO = ("não informado", "nao informado", "indefinido", "a definir",
              "-", "—", "")


def _tipo_do_termo(texto):
    """Qual tipo aquele trecho de escopo descreve, ou None."""
    alvo = " " + texto.strip().lower() + " "
    for tipo, termos in TERMOS_POR_TIPO:
        for termo in termos:
            if termo in alvo:
                return tipo
    return None


def _e_nao_mensuravel(texto):
    alvo = texto.strip().lower()
    return any(t in alvo for t in TERMOS_NAO_MENSURAVEIS)


def _e_organico(texto):
    alvo = texto.strip().lower()
    return any(t in alvo for t in TERMOS_ORGANICOS)


def _e_ambiguo(texto):
    """Trecho que fala de quantidade sem dizer o formato da peça.

    Só vale quando NENHUM tipo conhecido aparece no trecho: "20 vídeos" é
    ambíguo, "20 vídeos no feed" não é."""
    alvo = " " + texto.strip().lower() + " "
    return any(t in alvo for t in TERMOS_AMBIGUOS)


def _achar_alternativas_em_lista(bruto):
    """Acha "40 - Stories, reels ou feed" ANTES de o texto ser partido.

    Devolve (alternativas, texto_sem_elas). Só considera alternativa quando a
    lista tem a palavra "ou" E resolve para dois tipos conhecidos ou mais: sem
    isso, "6 stories, 4 reels" viraria alternativa quando é soma."""
    alternativas = []
    limpo = bruto
    for achado in REGEX_ALTERNATIVA_LISTA.finditer(bruto):
        lista = achado.group(2)
        if not re.search(r"\bou\b", lista, re.IGNORECASE):
            continue
        tipos = []
        for parte in re.split(r",|\bou\b", lista, flags=re.IGNORECASE):
            tipo = _tipo_do_termo(parte)
            if tipo and tipo not in tipos:
                tipos.append(tipo)
        if len(tipos) >= 2:
            alternativas.append((int(achado.group(1)), tipos))
            limpo = limpo.replace(achado.group(0), " ")
    return alternativas, limpo


def ler_escopo(texto):
    """Lê o texto livre do ESCOPO e devolve o que dá para contar.

    Devolve um dicionário:

        contratado          {TIPO: quantidade}  o que entra na cota do ciclo
        contratado_nao_validavel {TIPO: qtd}  X, YouTube, TikTok, Facebook
        contratado_organico {TIPO: qtd}  escopo que pede peça orgânica
        alternativas        [(quantidade, [TIPO, TIPO])]  "5 FEED (OU REELS)"
        anuais              [texto]  itens marcados ANUAL, fora do ciclo
        nao_mensuraveis     [(qtd ou None, texto)]  diárias, eventos, viagens,
                            tráfego, live. qtd só existe quando o item tem
                            quantidade de verdade EM POSTS (ex: "2 diárias");
                            live em horas e detalhe entre parênteses ficam
                            sempre com qtd=None
        ambiguos            [(qtd, texto)]  "20 vídeos", sem dizer o formato
        condicionais        [texto]  "a partir do 2º mês 12 combos"
        nao_reconhecido     [texto]  trechos com número que não casaram com tipo
        sem_escopo          True quando ninguém preencheu

    NÃO CHUTA TIPO. Trecho com número que não casa com nenhum termo conhecido vai
    para `nao_reconhecido` e aparece na tela, em vez de ser distribuído no tipo
    mais parecido: escopo é base de pagamento, e errar o tipo aqui viraria cota
    errada sem ninguém perceber.

    E NÃO CHUTA REGRA DE CONTRATO. As listas `contratado_nao_validavel`,
    `contratado_organico`, `ambiguos` e `condicionais` existem porque o dado real
    tem esses casos e nenhum deles se resolve sem alguém que leia o contrato. O
    programa separa e mostra; a decisão é escolhida na tela e fica registrada."""
    bruto = str(texto or "").strip()
    resultado = {"contratado": {}, "contratado_nao_validavel": {},
                 "contratado_organico": {}, "alternativas": [], "anuais": [],
                 "nao_mensuraveis": [], "ambiguos": [], "condicionais": [],
                 "nao_reconhecido": [], "telas_por_combo": None,
                 "sem_escopo": False, "texto": bruto}
    if bruto.lower() in SEM_ESCOPO:
        resultado["sem_escopo"] = True
        return resultado

    # A ALTERNATIVA EM LISTA SAI PRIMEIRO, antes de a vírgula partir o texto.
    # Ver o comentário de REGEX_ALTERNATIVA_LISTA: fazer isso depois perdia o
    # "ou feed" de "40 - Stories, reels ou feed" e fechava ciclo como NÃO
    # CONFORME sem motivo.
    em_lista, bruto_sem_lista = _achar_alternativas_em_lista(bruto)
    resultado["alternativas"].extend(em_lista)

    # Parte o texto em pedaços por separador, para cada item ser lido sozinho.
    # A quebra de linha entra porque "MENSAL: ... \n ANUAL: ..." usa linha.
    pedacos = [p.strip() for p in
               re.split(r"[+,;\n]|\be\b(?=\s+\d)", bruto_sem_lista)
               if p and p.strip()]

    # A periodicidade vale do rótulo em diante, e não só no pedaço onde aparece:
    # "ANUAL: 6 POSTS NO FEED" pode vir seguido de mais itens anuais.
    telas = REGEX_TELAS_POR_COMBO.search(bruto)
    if telas:
        resultado["telas_por_combo"] = int(telas.group(1))

    periodo_corrente = None
    for pedaco in pedacos:
        if REGEX_ANUAL.search(pedaco):
            periodo_corrente = "ANUAL"
        elif REGEX_MENSAL.search(pedaco):
            periodo_corrente = "MENSAL"

        achado = REGEX_QUANTIDADE.search(pedaco)
        if not achado:
            if _e_nao_mensuravel(pedaco):
                # SEM NÚMERO NENHUM (17/09/2026): nada pra declarar/contar,
                # fica só documentado. Ver o comentário completo do formato
                # da tupla mais abaixo, na primeira vez que um item REALMENTE
                # tem quantidade.
                resultado["nao_mensuraveis"].append((None, pedaco))
            elif _tipo_do_termo(pedaco):
                # ITEM DO CONTRATO SEM QUANTIDADE LEGÍVEL, e antes ele
                # DESAPARECIA. Achado no dado real em 03/09/2026: "X - Facebook"
                # aparece 3 vezes na planilha de validação, com a quantidade
                # escrita como a letra X. Sem número, o trecho não casava com
                # nada e era descartado em silêncio, então um item do contrato
                # simplesmente sumia do fechamento.
                resultado["nao_reconhecido"].append(
                    f"{pedaco} (item do contrato sem quantidade legível)")
            continue

        quantidade = int(achado.group(1))
        descricao = achado.group(2)

        if periodo_corrente == "ANUAL":
            resultado["anuais"].append(pedaco)
            continue

        # CONDIÇÃO NO ESCOPO fica visível, e não vira cota desde o primeiro
        # ciclo. O programa não sabe qual mês do contrato é este ciclo.
        if REGEX_CONDICAO.search(pedaco):
            resultado["condicionais"].append(pedaco)
            continue

        alternativa = REGEX_ALTERNATIVA.search(pedaco)
        # O TIPO PRINCIPAL SAI DA DESCRIÇÃO SEM O PARÊNTESES, e isso é correção
        # de um defeito que o teste pegou: em "5 FEED (OU REELS)" a descrição
        # inteira contém as duas palavras, e a busca por pedaço achava "reels"
        # primeiro. O resultado era a alternativa "REELS ou REELS", que faria a
        # cota de feed ser cumprida por reels sem ninguém ver.
        tipo = _tipo_do_termo(REGEX_ALTERNATIVA.sub(" ", descricao))
        if alternativa:
            outro = _tipo_do_termo(alternativa.group(1))
            tipos = [t for t in (tipo, outro) if t]
            if len(tipos) >= 2:
                resultado["alternativas"].append((quantidade, tipos))
                continue

        # O QUE ESTÁ ENTRE PARÊNTESES NÃO DECIDE O ITEM PRINCIPAL, e isto é
        # correção de uma regressão que eu mesmo criei em 03/09/2026 ao incluir
        # "collab" entre os termos não mensuráveis: "8 REELS (4 COLLABS)" virava
        # item de conferência inteiro, e os 8 reels do contrato desapareciam da
        # cota. O parêntese é detalhe do item, não o item.
        sem_parenteses = re.sub(r"\([^)]*\)", " ", pedaco)
        if _e_nao_mensuravel(sem_parenteses):
            # A TUPLA (quantidade, texto), E NÃO SÓ TEXTO (17/09/2026): pedido
            # do auditor, "diária de gravação" (e parecidos, com número de
            # verdade em POSTS) passa a poder ser confirmada com um check na
            # tela e contar no total do ciclo, igual já acontece com YouTube e
            # Twitter não validados. A quantidade guardada aqui é o teto: quem
            # confere não pode declarar mais do que o contrato pede. Ver
            # fechar_ciclo, `_nao_mensuravel_contavel`.
            resultado["nao_mensuraveis"].append((quantidade, pedaco))
            continue
        dentro_do_parentese = re.findall(r"\(([^)]*)\)", pedaco)
        for detalhe in dentro_do_parentese:
            if _e_nao_mensuravel(detalhe):
                # O item principal continua contando; o detalhe vira
                # conferência, SEM quantidade própria: o número do detalhe
                # (ex: "4" de "4 COLLABS") já é subconjunto do item principal,
                # contar separado dobraria a entrega.
                resultado["nao_mensuraveis"].append(
                    (None, f"{detalhe.strip()} (detalhe de \"{pedaco.strip()}\")"))

        # LIVE É HORA, NÃO POST. Ver TIPOS_EM_HORAS: contar 40 como quantidade
        # de posts faria a cota pedir 40 entregas que nunca chegam, porque live
        # não aparece na coluna TIPO da Monitoramento. SEM QUANTIDADE própria
        # aqui de propósito: a unidade é hora, não posts, então não dá pra
        # somar junto do resto sem inventar equivalência que ninguém mediu.
        if tipo in TIPOS_EM_HORAS:
            resultado["nao_mensuraveis"].append(
                (None, f"{pedaco} (medido em horas, e não em posts)"))
            continue

        # ESCOPO QUE PEDE ORGÂNICO vai para a conta do orgânico, que é contada à
        # parte porque peça orgânica não passa pela régua da portaria.
        if _e_organico(pedaco):
            destino = "contratado_organico"
            chave = tipo or "ORGÂNICO"
        elif tipo in TIPOS_NAO_VALIDAVEIS:
            # A ENTREGA EXISTE, A VALIDAÇÃO NÃO ALCANÇA. Ver
            # TIPOS_NAO_VALIDAVEIS: junto com "só CONFORME conta", isto faria a
            # cota nunca fechar. Fica separado, e quem fecha decide na tela.
            destino = "contratado_nao_validavel"
            chave = tipo
        elif not tipo:
            if _e_ambiguo(pedaco):
                # QUANTIDADE SEM FORMATO: "20 vídeos", "2 collabs". Chutar o
                # formato seria decidir a cota no lugar de quem tem o contrato.
                resultado["ambiguos"].append((quantidade, pedaco))
            else:
                resultado["nao_reconhecido"].append(pedaco)
            continue
        else:
            destino = "contratado"
            chave = tipo

        # Soma, e não sobrescreve: "6 STORIES + 4 COMBOS DE STORIES" é 10.
        resultado[destino][chave] = resultado[destino].get(chave, 0) + quantidade

    return resultado


# ---------------------------------------------------------------------------
# O que foi entregue, lido da Monitoramento
# ---------------------------------------------------------------------------
# POR QUE UM VEREDITO QUE NÃO É "CONFORME" NÃO É, POR SI, REPROVAÇÃO.
#
# Achado no papel de trabalho em 03/09/2026, e é um defeito de leitura que eu
# tinha: a minha primeira versão classificava como "peça reprovada" tudo o que
# não começasse com CONFORME. Só que a própria auditoria já separava isso em
# duas abas diferentes, com significados diferentes:
#
#     Achado04_ViolacaoRegulatoria    53 linhas, todas "NÃO CONFORME (Falta ...)"
#     Achado03_NaoValidada           341 linhas, que NÃO são violação
#
# E a aba Achado03 tem uma coluna própria, "Categoria do Gap", com exatamente
# duas categorias. A contagem fecha, e é o que prova que o mapeamento abaixo não
# é interpretação minha:
#
#     Evidência Inacessível                  223 = 140 link de rede social
#                                                 + 77 sem acesso à pasta
#                                                 +  6 pasta vazia
#     Limitação de Validação Automatizada    118 = 107 aviso pequeno/contraste
#                                                 + 11 requer análise humana
#
# A DIFERENÇA IMPORTA PORQUE A AÇÃO É OUTRA. Evidência inacessível se resolve
# conseguindo o arquivo, que é trabalho de quem organiza a pasta. Limitação da
# automação se resolve alguém OLHANDO a peça. E violação regulatória é achado,
# que vai para o relatório. Chamar os três de "reprovada" mandaria o auditor
# atrás de conformidade onde o problema é acesso a arquivo.
CATEGORIA_GAP_EVIDENCIA = "Evidência Inacessível"
CATEGORIA_GAP_LIMITACAO = "Limitação de Validação Automatizada"

# Os rótulos que a automação escreve, conforme o Manual de Parâmetros da
# auditoria, aba "Classificação Final (col. G)".
ROTULOS_SEM_EVIDENCIA = ("PASTA VAZIA", "SEM ACESSO", "NÃO FOI POSSÍVEL ANALISAR",
                         "NAO FOI POSSIVEL ANALISAR")
ROTULOS_LIMITE_DA_AUTOMACAO = (
    "REQUER ANÁLISE HUMANA", "REQUER ANALISE HUMANA",
    # ESTE NÃO EXISTE NO PAPEL DE TRABALHO, e por um motivo: lá o alerta de
    # áudio era uma COLUNA separada da planilha de validação ("Alerta de Áudio
    # (Fala Suspeita)"). No programa ele virou rótulo de veredito. Sem esta
    # linha ele cairia em "peça reprovada", ou seja, o programa acusaria
    # violação regulatória onde o que existe é uma fala que alguém precisa ouvir.
    "REQUER ANÁLISE DE ÁUDIO", "REQUER ANALISE DE AUDIO")
# O rótulo do orgânico, que não passa pela régua e por isso não tem veredito de
# conformidade para exibir. Não é gap nenhum.
ROTULOS_FORA_DA_REGUA = ("POST ORGÂNICO", "POST ORGANICO", "FORA DA VALIDAÇÃO",
                         "FORA DA VALIDACAO")


def categoria_do_gap(veredito):
    """A categoria da aba Achado03, ou vazio quando não é gap.

    Vazio quer dizer uma de três coisas: a peça é CONFORME, é NÃO CONFORME de
    verdade, ou a análise ainda não rodou. Nenhuma delas é gap de validação."""
    alvo = str(veredito or "").strip().upper()
    if not alvo:
        return ""
    if any(alvo.startswith(r) for r in ROTULOS_SEM_EVIDENCIA):
        return CATEGORIA_GAP_EVIDENCIA
    if any(alvo.startswith(r) for r in ROTULOS_LIMITE_DA_AUTOMACAO):
        return CATEGORIA_GAP_LIMITACAO
    return ""


def contar_entregas(linhas, handle, ciclo):
    """Conta os POSTS distintos por tipo, para um influenciador e um ciclo.

    CONTA POST, E NÃO LINHA, e é aqui que a mudança de 03/09/2026 vira base de
    pagamento: entrega do mesmo dia é um post só, e o auditor definiu que 1 post
    do dia é 1 combo. Contar linha inflaria a cota, porque uma sequência de
    cinco telas apareceria como cinco entregas.

    A marcação separa: peça orgânica e peça com link são entregas DIFERENTES,
    porque o auditor decidiu que "são tipos de entrega diferentes mesmo". Então
    o retorno traz os dois grupos, e quem cruza com o escopo escolhe.

    `linhas` são dicionários com as chaves handle, ciclo, tipo, post, marcacao,
    data_post e validacao. Quem lê a planilha monta isso; aqui não se lê nada."""
    alvo = str(handle or "").strip().lstrip("@").lower()
    ciclo_alvo = re.sub(r"(?i)^ciclo\s*", "", str(ciclo or "")).strip()

    por_tipo = {}
    por_tipo_conforme = {}
    por_tipo_organico = {}
    vistos = set()
    vistos_conforme = set()
    vistos_organico = set()
    linhas_do_ciclo = []
    sem_veredito = []
    reprovadas = []
    sem_evidencia = []
    limite_da_automacao = []
    # UM REGISTRO POR POST, PARA O CHECKLIST DO FINANCEIRO (09/09/2026). O
    # auditor pediu um aviso no formato que o próprio Marketing já manda no
    # grupo (uma lista numerada por data, com o item marcado quando cumprido),
    # em vez do texto corrido que havia antes. Aqui só se GUARDA a data e o
    # veredito de cada post já deduplicado; quem decide o ícone e a ordem é
    # quem monta o texto, porque isso é apresentação, não regra de contagem.
    posts = []
    for linha in linhas:
        if str(linha.get("handle") or "").strip().lstrip("@").lower() != alvo:
            continue
        se_ciclo = re.sub(r"(?i)^ciclo\s*", "",
                          str(linha.get("ciclo") or "")).strip().replace(".0", "")
        if se_ciclo != ciclo_alvo:
            continue
        tipo = str(linha.get("tipo") or "").strip().upper()
        if not tipo:
            continue
        linhas_do_ciclo.append(linha)
        # A CHAVE DO POST é (tipo, dia, número do post). Sem o dia, dois posts
        # de números iguais em ciclos remontados contariam como um.
        #
        # O DIA ENTRA COMO DATA, E NÃO COMO TEXTO (07/09/2026). A revisão do dia
        # pegou este lugar: a chave usava o texto cru da célula, então duas
        # telas do mesmo dia com o mesmo número de POST, uma com a data
        # reconhecida pelo Sheets ("05/09/26") e outra digitada como texto
        # ("05/09/2026"), geravam duas chaves distintas. As duas passavam por
        # `vistos`, `por_tipo` contava 2 entregas onde houve 1, e o Financeiro
        # podia fechar o ciclo com a cota cumprida sem estar. É a contagem que
        # alimenta a cota, então o efeito é direto no fechamento.
        chave = (tipo, data_de_planilha.chave_de_dia(linha.get("data_post")),
                 str(linha.get("post") or ""))
        organico = str(linha.get("marcacao") or "").strip().upper().startswith(
            ("ORGANICO", "ORGÂNICO", "SIM"))
        # `entregue_conforme` CONTINUA SEPARADO DE `entregue` (a lista com
        # tudo), mesmo depois de 16/09/2026 a cota ter deixado de exigir só
        # peça conforme (ver o comentário em fechar_ciclo). Serve pra dizer
        # QUANTO do total já passou na régua da portaria, sem gate: reprovada
        # e sem veredito continuam identificáveis por fora.
        #
        # A peça orgânica é o caso especial dessa regra, e não uma exceção a
        # ela: desde 03/09/2026 ela não passa pela régua regulatória, então ela
        # não tem veredito de conformidade para exibir. Por isso ela é contada no
        # grupo próprio, e é lá que quem fecha decide se conta no contrato.
        veredito = str(linha.get("validacao") or "").strip().upper()
        e_conforme = veredito.startswith("CONFORME")
        if organico:
            if chave not in vistos_organico:
                vistos_organico.add(chave)
                por_tipo_organico[tipo] = por_tipo_organico.get(tipo, 0) + 1
            continue
        if chave not in vistos:
            vistos.add(chave)
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
            posts.append({
                "data_post": linha.get("data_post"),
                # DATA JÁ CONVERTIDA, e não só o texto cru da célula: quem
                # monta o checklist do Financeiro precisa exibir DD/MM sem
                # reabrir a discussão de formato por linha, e sem repetir a
                # regra "nunca comparar/formatar data como texto".
                "data": data_de_planilha.data_de_celula(linha.get("data_post")),
                "tipo": tipo, "validacao": veredito})
            gap = categoria_do_gap(veredito)
            fora_da_regua = any(veredito.startswith(r)
                                for r in ROTULOS_FORA_DA_REGUA)
            if not veredito:
                sem_veredito.append(linha)
            elif e_conforme or fora_da_regua:
                pass
            elif gap == CATEGORIA_GAP_EVIDENCIA:
                sem_evidencia.append(linha)
            elif gap == CATEGORIA_GAP_LIMITACAO:
                limite_da_automacao.append(linha)
            else:
                # SOBRA A REPROVAÇÃO DE VERDADE: "NÃO CONFORME (Falta ...)", que
                # é o vocabulário da aba Achado04 do papel de trabalho.
                reprovadas.append(linha)
        if e_conforme and chave not in vistos_conforme:
            vistos_conforme.add(chave)
            por_tipo_conforme[tipo] = por_tipo_conforme.get(tipo, 0) + 1

    # ORDENADO POR DATA DE VERDADE, NÃO COMO TEXTO (09/09/2026), mesma regra do
    # resto deste arquivo: comparar "05/09/26" com "05/09/2026" como texto erra.
    # Data ilegível vai para o fim, sem travar a ordem das demais nem sumir da
    # lista.
    _legiveis = [p for p in posts if p["data"]]
    _ilegiveis = [p for p in posts if not p["data"]]
    _legiveis.sort(key=lambda p: p["data"])
    posts = _legiveis + _ilegiveis

    return {"entregue": por_tipo,
            # É ESTE que a cota usa. `entregue` fica para a tela mostrar o
            # total, porque a diferença entre os dois é informação de auditoria:
            # ela é o tamanho da situação do meio.
            "entregue_conforme": por_tipo_conforme,
            "entregue_organico": por_tipo_organico,
            "sem_veredito": sem_veredito,
            "reprovadas": reprovadas,
            # AS DUAS CATEGORIAS DA ABA Achado03, separadas porque a ação é
            # outra: uma se resolve conseguindo o arquivo, a outra olhando a
            # peça. Ver categoria_do_gap.
            "sem_evidencia": sem_evidencia,
            "limite_da_automacao": limite_da_automacao,
            "posts": posts,
            "linhas": linhas_do_ciclo}


# ---------------------------------------------------------------------------
# O fechamento do ciclo
# ---------------------------------------------------------------------------
CONFORME = "CONFORME"
INCOMPLETO = "INCOMPLETO"
SEM_BASE = "SEM BASE PARA COMPARAR"
# COTA_COM_PECA_REPROVADA SAIU DAQUI EM 16/09/2026. Existia uma situação
# própria pra "a quantidade fecha, mas tem peça reprovada na régua da
# portaria" (decisão do auditor em 31/08/2026), tratada como achado, não
# cumprimento. Revisto a pedido dele mesmo: "sempre haverá algum não
# conforme que pode passar, ele só vai ser avisado para as próximas não
# repetir". A peça reprovada continua identificada e vira aviso nos motivos
# do fechamento (ver fechar_ciclo), só deixou de ser uma situação à parte
# que travava o ciclo em CONFORME. Se o vocabulário antigo aparecer num
# registro já gravado (Historico_Entregas), é histórico, não bug.
COTA_ESPERANDO_ANALISE = "COTA FECHA, MAS FALTA ANÁLISE DE PEÇA"

# ESCOPO PREENCHIDO, MAS SEM NADA QUE DOWNLOAD MEÇA. Achado no dado real em
# 03/09/2026: existe contrato cujo escopo é só "40 HORAS LIVE". Isso NÃO é a
# mesma coisa que escopo em branco, e tratar como "sem base para comparar"
# culparia o cadastro por um cadastro que está certo. O que falta é a medição, e
# ela é humana: quem fecha confere as horas de live e registra.
SEM_COTA_MENSURAVEL = "ESCOPO SEM ENTREGA MEDIDA POR DOWNLOAD"

# AS DUAS SITUAÇÕES QUE SAÍRAM DE DENTRO DE "PEÇA REPROVADA" (03/09/2026), pelo
# cruzamento com a aba Achado03 do papel de trabalho. Elas não são conformidade:
# são a análise que não chegou ao fim, por dois motivos diferentes, e cada um
# pede uma ação diferente de uma pessoa diferente. Ver categoria_do_gap.
COTA_SEM_EVIDENCIA = "COTA FECHA, MAS FALTA EVIDÊNCIA DA PEÇA"
COTA_NO_LIMITE_DA_AUTOMACAO = "COTA FECHA, MAS A ANÁLISE NÃO CONCLUIU"

# NAO_CONFORME SAIU DAQUI EM 09/09/2026. Existia uma situação própria para
# "composição mudou" (tipo sem nenhuma entrega, ou tipo entregue fora do
# escopo), com o mesmo peso de INCOMPLETO. Comparado com o RA Nº 16/2026
# (Achado 1) e o dashboard oficial da auditoria (`Dashboard Influenciadores
# v4 - SEM SENHA.html`, campo Status Escopo só com ✅/🚫/⏳), o critério real é
# BINÁRIO: cota do ciclo cumprida ou não. "Tipo sem nenhuma entrega" já cai em
# INCOMPLETO (é falta de quantidade, só que total). "Tipo fora do escopo"
# passou a não decidir mais a situação sozinho: o RA16 trata substituição de
# composição como flexibilização a documentar (Ação 04, ex. Streamer que troca
# entrega por horas de live), não como o mesmo achado de deixar de entregar.
# Ver fechar_ciclo() e o comentário de exige_justificativa.
#
# O NOME TAMBÉM COLIDIA (apontado pelo auditor): "NÃO CONFORME" é o mesmo
# vocabulário do veredito regulatório por peça (CONFORME/NÃO CONFORME em
# validar_avisos_portaria136.py e na coluna VALIDACAO), e as duas coisas
# são perguntas diferentes: uma é se a peça tem os avisos da portaria, a
# outra é se o ciclo entregou a cota. Tirando o estado, tira a colisão.
# CONFORME COM OBSERVAÇÃO (16/09/2026), proposta do próprio auditor quando
# perguntei se a declaração humana devia mudar a conta: "pode ser um conforme
# com observação, o que acha?". Acho, e é melhor que as duas alternativas que
# eu tinha posto: "CONFORME" puro esconderia que parte do número veio de
# alguém afirmando, não de medição, e "só registra" obrigaria a conviver com
# um INCOMPLETO que quem conferiu sabe que não é verdade.
#
# QUANDO ELA APARECE: o ciclo só fecha porque alguém declarou, na própria
# tela, que uma entrega que o programa não mede existe (o rádio "Conferi à
# mão e as entregas existem", para tweet, YouTube, TikTok e Facebook). Sem a
# declaração, aquele ciclo seria INCOMPLETO.
#
# POR QUE ELA É SEPARADA DE CONFORME, e não um CONFORME com uma nota ao lado:
# porque é assim que dá para contar depois quantos ciclos fecharam por
# medição e quantos fecharam por palavra de alguém. Num CONFORME só, essa
# diferença some no primeiro filtro.
CONFORME_COM_OBSERVACAO = "CONFORME, COM CONFERÊNCIA HUMANA"

SITUACOES_DE_CICLO = (CONFORME, CONFORME_COM_OBSERVACAO, INCOMPLETO, SEM_BASE,
                      COTA_ESPERANDO_ANALISE,
                      SEM_COTA_MENSURAVEL, COTA_SEM_EVIDENCIA,
                      COTA_NO_LIMITE_DA_AUTOMACAO)

# COMO CADA SITUAÇÃO APARECE NA TELA. Isto mora aqui, e não na página, por dois
# motivos. O primeiro é que o teste pode exigir que TODA situação tenha rótulo,
# então quem criar a sétima situação amanhã não vai conseguir deixá-la sem nome
# na tela. O segundo é que a página não é o único lugar que precisa nomear a
# situação: o aviso automático, quando existir, tem que dizer a mesma coisa.
#
# ACRESCENTADO EM 03/09/2026 porque o nome comprido não cabia no indicador da
# tela e saía cortado ("SEM BA...", "NÃO C..."), ou seja, o auditor lia o
# fechamento sem saber do que se tratava. O nome longo continua sendo o valor
# guardado no registro; o curto é só para caber.
#
# gravidade: "ok" segue para o financeiro, "achado" é problema que vai para o
# auditor, "espera" é ciclo que ainda não terminou de ser medido.
APRESENTACAO = {
    # OS RÓTULOS MUDARAM EM 09/09/2026 pra "apto/não apto a pagamento", a
    # frase que o próprio RA Nº 16/2026 usa para descrever o que este
    # programa deveria mostrar (Ação 01, Achado 1: "indicando de forma
    # objetiva quais ciclos estão aptos a pagamento"). Continua sendo
    # sinalização, não autorização: quem libera o pagamento é o Financeiro.
    CONFORME: {
        "curto": "Ciclo apto a pagamento",
        "icone": "✅",
        "gravidade": "ok",
        "explicacao": "Tudo o que o escopo pede foi entregue e validado neste "
                      "ciclo."},
    CONFORME_COM_OBSERVACAO: {
        "curto": "Apto a pagamento, com conferência humana",
        "icone": "✅",
        "gravidade": "ok",
        "explicacao": "O ciclo fecha, mas parte dele foi confirmada por uma "
                      "pessoa em vez de medida pelo programa: alguém declarou "
                      "na tela que uma entrega que o download não enxerga "
                      "existe. Quem declarou e quando ficam no registro."},
    INCOMPLETO: {
        # ROTULO SUAVIZADO EM 10/09/2026. "Ciclo não apto a pagamento" (rótulo
        # de 09/09) veio direto da frase do RA Nº 16/2026, mas na mensagem
        # real pro Financeiro o auditor achou incisivo demais ("achei muito
        # incisiva"), sobretudo pra quem só está vendo o resultado de um
        # ciclo comum, não um problema grave. "Incompleto ou alterado" descreve
        # o mesmo estado (falta quantidade do escopo) sem soar como acusação.
        "curto": "Ciclo incompleto ou alterado",
        "icone": "⏳",
        "gravidade": "espera",
        # ESTE ESTADO PASSOU A COBRIR TAMBÉM "tipo sem nenhuma entrega"
        # (09/09/2026), que antes fechava à parte como NÃO CONFORME. É a
        # mesma coisa medida no RA16: falta de quantidade, total ou parcial,
        # é "escopo não cumprido". O ciclo ainda pode ser cumprido antes de
        # fechar; SOLICITAR PAGAMENTO agora, mesmo assim, exige justificativa
        # (é o que ENTREGA_NAO_FECHOU cobre em exige_justificativa).
        "explicacao": "Falta quantidade de algum tipo do escopo neste ciclo, "
                      "inclusive quando nenhuma peça daquele tipo foi "
                      "entregue. O ciclo ainda pode ser cumprido antes de "
                      "fechar; solicitar pagamento agora, mesmo assim, "
                      "exige justificativa escrita."},
    SEM_BASE: {
        "curto": "Sem base para comparar",
        "icone": "❔",
        "gravidade": "espera",
        "explicacao": "O escopo não está preenchido no cadastro, então não há "
                      "contra o que comparar a entrega. O que falta é cadastro, "
                      "não entrega."},
    SEM_COTA_MENSURAVEL: {
        "curto": "Escopo sem entrega medida por download",
        "icone": "🔍",
        "gravidade": "espera",
        "explicacao": "O escopo está preenchido, mas nada nele é medido por "
                      "download: são horas de live, diárias, eventos ou "
                      "plataforma que o programa não baixa. A conferência é "
                      "humana, e a lista está abaixo."},
    COTA_ESPERANDO_ANALISE: {
        "curto": "Cota fecha, mas falta análise",
        "icone": "⏳",
        "gravidade": "espera",
        "explicacao": "A quantidade do escopo fecha, mas há peça sem veredito "
                      "da análise. Rode a análise antes de fechar o ciclo."},
    COTA_SEM_EVIDENCIA: {
        "curto": "Cota fecha, mas falta evidência",
        "icone": "📂",
        "gravidade": "espera",
        "explicacao": "A quantidade fecha, mas há peça que a análise não "
                      "conseguiu abrir: pasta vazia, sem acesso, ou link que "
                      "aponta para a rede social em vez do arquivo. Resolve-se "
                      "conseguindo o arquivo, e não olhando a peça."},
    COTA_NO_LIMITE_DA_AUTOMACAO: {
        "curto": "Cota fecha, mas a análise não concluiu",
        "icone": "👁️",
        "gravidade": "espera",
        "explicacao": "A quantidade fecha, mas há peça em que a automação não "
                      "conseguiu decidir, normalmente aviso pequeno ou de baixo "
                      "contraste. Precisa de alguém olhando a peça na tela."},
}


def apresentacao(situacao):
    """Rótulo curto, ícone, gravidade e explicação de uma situação de ciclo.

    Nunca devolve vazio: situação desconhecida vira o próprio texto dela, para
    a tela não ficar em branco justamente quando algo saiu do previsto."""
    padrao = {"curto": str(situacao), "icone": "❔", "gravidade": "espera",
              "explicacao": ""}
    return dict(padrao, **APRESENTACAO.get(situacao, {}))


# QUEM COBRIU QUEM (23/09/2026, pedido do auditor)
#
# Até aqui o programa dizia "entregas parecem compensadas", olhando dois
# totais. Quem lia a tela tinha que descobrir sozinho, na tabela, o que tinha
# coberto o quê. O pedido foi direto: "que o programa identifique o que foi
# compensado em relação ao escopo, e não apenas confiar nos números de que
# parece que algo foi compensado".
#
# O QUE É FATO E O QUE É ATRIBUIÇÃO, e a diferença tem que ficar visível:
#
#   FATO         faltaram 2 STORIES, e sobraram 2 REELS
#   ATRIBUIÇÃO   "os 2 REELS cobriram os 2 STORIES"
#
# A atribuição só é única quando existe UMA sobra e UMA falta, que é o caso
# comum. Com mais de uma origem de sobra, qual cobriu qual não é uma verdade
# que o dado contenha: é uma divisão. Esta aqui é sempre a mesma (sobra maior
# primeiro, empate pelo nome), escolhida para dois fechamentos iguais nunca
# saírem escritos diferente, e não porque exista uma resposta certa.
#
# A DECLARAÇÃO DE FORA DA PLATAFORMA ENTRA DOS DOIS LADOS, e é por isso que
# ela é assunto aqui: item de fora da plataforma que a pessoa NÃO confirmou
# (a caixa de marcar da diária, por exemplo) é uma falta como outra qualquer,
# e pode ser coberto por sobra medida. Confirmado, ele some da conta: o teto
# em fechar_ciclo garante que uma declaração nunca vale mais que o
# contratado daquele item, então ela cobre a própria linha e nunca sobra
# para cobrir outra.
def explicar_compensacao(faltas, sobras):
    """Divide as sobras entre as faltas, e devolve quem cobriu quem.

    `faltas` e `sobras`: listas de {"o_que": texto, "quanto": inteiro}. A
    sobra pode trazer também "origem", um texto curto que a tela usa para
    dizer de onde ela veio (medida na plataforma, peça orgânica, tipo que
    não estava no escopo).

    Devolve uma lista, uma entrada por falta que foi coberta ao menos em
    parte:

        [{"o_que": "STORIES", "quanto": 2, "coberto": 2,
          "por": [{"o_que": "REELS", "quanto": 2, "origem": "medido"}]}]

    Falta que ficou sem cobertura sai com `coberto` menor que `quanto`, e é
    isso que separa "compensado" de "ficou faltando de verdade". Quem chama
    decide o que fazer com cada caso."""
    restantes = [dict(s, quanto=int(s.get("quanto") or 0)) for s in (sobras or [])
                 if int(s.get("quanto") or 0) > 0]
    # A ORDEM É FIXA, e o porquê está no comentário grande acima: sobra maior
    # primeiro, empate resolvido pelo nome. Sem isso, o mesmo fechamento
    # poderia sair escrito de um jeito hoje e de outro amanhã, e um texto que
    # muda sozinho é ruim num registro de auditoria.
    restantes.sort(key=lambda s: (-s["quanto"], str(s.get("o_que") or "")))

    resultado = []
    for falta in sorted((f for f in (faltas or []) if int(f.get("quanto") or 0) > 0),
                        key=lambda f: str(f.get("o_que") or "")):
        precisa = int(falta["quanto"])
        cobriram = []
        for sobra in restantes:
            if precisa <= 0:
                break
            if sobra["quanto"] <= 0:
                continue
            usado = min(sobra["quanto"], precisa)
            sobra["quanto"] -= usado
            precisa -= usado
            cobriram.append({"o_que": sobra.get("o_que"), "quanto": usado,
                             "origem": sobra.get("origem", ""),
                             "rotulo": sobra.get("rotulo", "")})
        resultado.append({
            "o_que": falta.get("o_que"),
            "quanto": int(falta["quanto"]),
            "coberto": int(falta["quanto"]) - precisa,
            "rotulo": falta.get("rotulo", ""),
            "por": cobriram,
        })
    return resultado


def _rotulo_do_item(item, quantos):
    """Como aquele item aparece na frase.

    `rotulo` MANDA QUANDO EXISTE, e existe por um motivo achado testando em
    23/09/2026: item de fora da plataforma já traz o número dentro do próprio
    texto do contrato ("1 DIARIA DE GRAVACAO"), então prefixar a quantidade
    produzia "1 1 DIARIA DE GRAVACAO". Tipo mensurável não tem esse problema,
    e continua saindo como "2 STORIES"."""
    if item.get("rotulo"):
        return str(item["rotulo"])
    return f"{quantos} {item.get('o_que')}"


def texto_da_compensacao(compensacao):
    """A frase que vai para a tela e para o registro, ou vazio.

    Só fala das faltas que foram COBERTAS: falta descoberta não é
    compensação, e tem mensagem própria em fechar_ciclo."""
    partes = []
    for item in compensacao or []:
        if not item.get("coberto"):
            continue
        origem = ", ".join(_rotulo_do_item(p, p["quanto"])
                           for p in item.get("por") or [])
        if not origem:
            continue
        partes.append(
            f"{_rotulo_do_item(item, item['coberto'])} coberto(s) por "
            f"{origem} a mais")
    return "; ".join(partes)


def fechar_ciclo(escopo_lido, contagem, declaracoes=None,
                 declaracoes_nao_mensuravel=None):
    """Compara o contratado com o entregue e devolve o fechamento.

    A REGRA MUDOU EM 09/09/2026, alinhada ao RA Nº 16/2026 (Achado 1) e ao
    dashboard oficial da auditoria: o critério de fechamento é BINÁRIO, cota
    do ciclo cumprida ou não. É também como a pessoa do Marketing descreveu o
    processo em áudio no mesmo dia: "cada mês é ciclo, a gente contabiliza a
    entrega mensal de cada influenciador". Antes, "tipo sem nenhuma entrega" e
    "tipo fora do escopo" fechavam à parte como NÃO CONFORME, palavra que o
    auditor apontou como confusa: colide com o veredito regulatório por peça
    (CONFORME/NÃO CONFORME em validar_avisos_portaria136.py), que é outra
    pergunta (a peça tem os avisos da portaria?) e não esta (o ciclo entregou
    a cota?).

      falta quantidade no TOTAL do ciclo, somando todos os tipos  INCOMPLETO
      tudo do escopo cumprido no total, nada faltando             CONFORME
      escopo não preenchido ou não legível             SEM BASE PARA COMPARAR

    `declaracoes_nao_mensuravel` COBRE ENTREGA FORA DA PLATAFORMA (17/09/2026):
    {texto_do_item: quantidade_confirmada}, para os itens de
    `nao_mensuraveis` que TÊM quantidade em posts (diária de gravação, por
    exemplo; live em horas nunca entra aqui, ver ler_escopo).

    A JUSTIFICATIVA DEIXOU DE SER SEMPRE OBRIGATÓRIA (17/09/2026, mesmo dia,
    revisado depois de o auditor testar ao vivo). A primeira versão exigia
    sempre que o campo era usado, e isso confundia quem via a tabela toda
    verde (STORIES e REELS batendo exato) e mesmo assim era barrado por uma
    justificativa, sem entender o porquê até achar a diária lá embaixo. A
    regra final: quando confirmar a entrega fora da plataforma é só o que
    faltava para o ciclo fechar por inteiro, sem nenhum tipo mensurável
    abaixo do contratado nem composição fora do escopo, não há nada de
    anômalo a explicar, e a justificativa some, trocada pelo motivo
    automático "Entrega fora da plataforma confirmada..." Se, mesmo com a
    declaração, o ciclo continuar INCOMPLETO, ou se algum tipo mensurável
    ficou abaixo do combinado (situação de substituição real, que pede
    explicação por si só), a justificativa volta a ser obrigatória. Ver o
    comentário de `exige_justificativa` mais abaixo.

    ENTREGAR MAIS DO MESMO TIPO NÃO É DESVIO. Na planilha de achados, 13 combos
    contra 12 contratados fechou ✅, e essa leitura continua: o que o auditor
    quer pegar é MUDANÇA DE COMPOSIÇÃO, não excesso.

    TIPO ENTREGUE FORA DO ESCOPO CONTINUA REGISTRADO (fora_do_escopo) e
    CONTINUA EXIGINDO JUSTIFICATIVA (exige_justificativa), mas deixou de
    decidir a situação do ciclo sozinho: o RA16 trata substituição de
    composição como flexibilização a documentar (Ação 04, ex. Streamer que
    troca entrega por horas de live), não como o mesmo achado de deixar de
    entregar. Um ciclo pode fechar CONFORME (cota cumprida) e ainda assim
    pedir essa justificativa, porque são perguntas diferentes: a cota fechou?
    e a composição bateu com o contrato? O motivo é o mesmo de sempre: o
    Marketing pode ter pedido a mudança porque o retorno foi bom, isso não é
    proibido, e também não pode passar como contrato cumprido como escrito.
    Quem fecha escreve o porquê, e o porquê fica registrado.

    "exige_justificativa" TAMBÉM COBRE NÃO TER FECHADO (09/09/2026), e não só
    a composição: virou o gate único de "posso solicitar pagamento deste
    ciclo sem escrever nada?". Ciclo INCOMPLETO, ou numa situação do meio
    (peça reprovada, sem evidência, sem veredito), também pede essa
    justificativa antes de solicitar. Ver ENTREGA_NAO_FECHOU."""
    contratado = dict(escopo_lido.get("contratado") or {})
    # QUALQUER VEREDITO CONTA PARA A COTA (16/09/2026, revisão da decisão de
    # 31/08/2026, a pedido do auditor: "sempre haverá algum não conforme que
    # pode passar, ele só vai ser avisado para as próximas não repetir").
    # ANTES, só peça CONFORME contava, e uma peça reprovada sozinha impedia o
    # ciclo de fechar mesmo com a quantidade toda entregue: o achado
    # regulatório (a peça não tem o aviso da portaria) virava também um
    # bloqueio de pagamento, que são perguntas diferentes ("a peça está
    # conforme?" e "o ciclo entregou a cota?"). A peça reprovada continua
    # identificada e avisada (ver mais abaixo), só deixou de travar o
    # fechamento.
    entregue = dict(contagem.get("entregue") or {})
    entregue_total = entregue
    organico = dict(contagem.get("entregue_organico") or {})
    reprovadas = list(contagem.get("reprovadas") or [])
    sem_veredito = list(contagem.get("sem_veredito") or [])
    sem_evidencia = list(contagem.get("sem_evidencia") or [])
    limite_da_automacao = list(contagem.get("limite_da_automacao") or [])

    sem_cota = not contratado and not escopo_lido.get("alternativas")
    if escopo_lido.get("sem_escopo") or sem_cota:
        # SEPARA DUAS COISAS QUE PARECIAM UMA (03/09/2026). Escopo em branco é
        # falta de cadastro. Escopo preenchido só com o que download não mede,
        # como o contrato de "40 HORAS LIVE" que existe no dado real, é outra
        # coisa: o cadastro está certo e a medição é humana. Chamar os dois de
        # "sem base para comparar" mandaria alguém cobrar o Marketing por um
        # cadastro que está completo.
        tem_algo_no_escopo = bool(
            escopo_lido.get("nao_mensuraveis")
            or escopo_lido.get("contratado_nao_validavel")
            or escopo_lido.get("contratado_organico")
            or escopo_lido.get("ambiguos")
            or escopo_lido.get("condicionais")
            or escopo_lido.get("anuais"))
        if not escopo_lido.get("sem_escopo") and tem_algo_no_escopo:
            situacao_vazia = SEM_COTA_MENSURAVEL
            motivo = ("O escopo está preenchido, mas nada nele é contado por "
                      "download. A conferência deste ciclo é humana, e a lista "
                      "do que precisa ser conferido está abaixo.")
        else:
            situacao_vazia = SEM_BASE
            motivo = ("O escopo deste influenciador não está preenchido no "
                      "cadastro, ou está escrito de um jeito que o programa não "
                      "consegue contar. Sem ele não há com o que comparar.")
        return {
            "situacao": situacao_vazia,
            "exige_justificativa": False,
            "por_tipo": [],
            "faltando": {},
            "fora_do_escopo": {},
            "motivos": [motivo],
            "total_contratado": 0,
            "total_entregue": 0,
            "conferir_a_mao": _conferir_a_mao(escopo_lido, organico),
            # AS DUAS CHAVES NOVAS DE 23/09/2026 TAMBÉM SAEM DAQUI, vazias:
            # sem escopo para comparar não há compensação a explicar nem nota
            # automática a escrever. Faltando elas, quem lê o fechamento
            # quebraria justamente no caminho em que o cadastro está incompleto.
            "compensacao": [],
            "nota_automatica": "",
        }

    # As alternativas ("5 FEED OU REELS") são cumpridas pela SOMA dos tipos que
    # aceitam. Tratadas antes dos tipos simples, porque consomem entrega.
    entregue_restante = dict(entregue)
    linhas_alternativa = []
    for quantidade, tipos in escopo_lido.get("alternativas") or []:
        soma = sum(entregue_restante.get(t, 0) for t in tipos)
        usados = 0
        for t in tipos:
            gasto = min(entregue_restante.get(t, 0), quantidade - usados)
            entregue_restante[t] = entregue_restante.get(t, 0) - gasto
            usados += gasto
        linhas_alternativa.append({
            "tipo": " ou ".join(tipos), "contratado": quantidade,
            "entregue": soma, "falta": max(0, quantidade - soma),
            "alternativa": True,
        })

    por_tipo = []
    faltando = {}
    for tipo, quantidade in sorted(contratado.items()):
        feito = entregue_restante.get(tipo, 0)
        falta = max(0, quantidade - feito)
        if falta:
            faltando[tipo] = falta
        por_tipo.append({"tipo": tipo, "contratado": quantidade,
                         "entregue": feito, "falta": falta,
                         "alternativa": False})
    por_tipo.extend(linhas_alternativa)

    # QUALQUER TIPO COMPENSA QUALQUER TIPO (16/09/2026), decisão final do
    # auditor depois de dois exemplos puxarem em direções diferentes: o
    # primeiro (falta stories, sobra feed/reels) sugeria só um grupo
    # Feed/Reels, mas o segundo (10 reels + 10 stories contratados, entregou
    # 9 reels e 11 stories, "isso está ok") tinha stories cobrindo reels. A
    # palavra final foi literal: "qualquer coisa pode compensar qualquer
    # coisa". A conta de QUANTIDADE passou a olhar o TOTAL contratado contra
    # o TOTAL entregue, não mais tipo por tipo; `faltando`, `por_tipo` e
    # `linhas_alternativa` acima continuam com o número CRU de cada tipo, sem
    # nenhum abatimento, porque a tela ainda precisa mostrar a composição
    # real de quem olhar a tabela.
    # O ORGÂNICO ENTRA NA SOMA, DOS DOIS LADOS (16/09/2026). Ele corria num
    # trilho paralelo desde 03/09/2026 ("peça orgânica e peça com link são
    # entregas DIFERENTES"), e isso foi ficando errado quando a régua virou
    # "qualquer coisa compensa qualquer coisa": medido neste dia, 16 stories
    # contratados com 10 stories + 6 lives entregues fechava CONFORME, e os
    # mesmos 10 stories + 6 ORGÂNICOS fechavam INCOMPLETO. O auditor foi
    # direto ao ponto: "eles fazem substituições de acordo com a repercussão
    # da entrega", e peça orgânica é uma dessas substituições.
    #
    # OS DOIS LADOS, e não só o entregue: contar orgânico entregue sem contar
    # orgânico contratado daria cota de graça a quem tem "12 POSTAGENS
    # ORGÂNICAS" escrito no contrato.
    #
    # ELA NÃO TEM VEREDITO, E ISSO ESTÁ CERTO: peça orgânica não passa pela
    # régua da portaria (decisão de 03/09/2026), então não há conformidade a
    # esperar antes de contá-la. A separação continua existindo em
    # `entregue_organico` e no indicador próprio da tela, que é onde ela serve.
    # O TIPO NÃO VALIDÁVEL PASSOU A COBRAR (16/09/2026). Medido no mesmo dia:
    # escopo "12 COMBOS DE STORIES + 8 TWEETS", com só os 12 stories
    # entregues, fechava CONFORME. Os 8 tweets eram invisíveis para a conta,
    # ou seja, "8 TWEETS" no contrato era letra morta.
    #
    # ELES FICARAM DE FORA POR UM MOTIVO REAL, em 03/09/2026: a régua da
    # portaria não roda em tweet, YouTube, TikTok nem Facebook, então nenhuma
    # peça desses tipos recebe veredito CONFORME, e "só peça CONFORME conta"
    # os deixaria faltando para sempre. A saída daquele dia foi tirá-los da
    # conta e criar o rádio de conferência humana na tela. Só que a resposta
    # do rádio nunca chegava ao motor: era montada e descartada.
    #
    # AGORA ELA CHEGA (`declaracoes`), então dá para fazer o certo dos dois
    # lados: o tipo cobra, e a declaração de quem conferiu cobre.
    _contratado_nao_validavel = dict(escopo_lido.get("contratado_nao_validavel") or {})
    # ITENS FORA DA PLATAFORMA, COM QUANTIDADE DE VERDADE (17/09/2026): diária
    # de gravação e parecidos, o subconjunto de `nao_mensuraveis` que tem um
    # número em POSTS (ver ler_escopo). Chave é o próprio texto do item,
    # porque, ao contrário de YouTube/Twitter, não existe um vocabulário fixo
    # de tipos aqui.
    _nao_mensuravel_contavel = {texto: int(qtd)
                                for qtd, texto in (escopo_lido.get("nao_mensuraveis") or [])
                                if qtd}
    _total_contratado = (sum(contratado.values())
                         + sum(q for q, _tipos in escopo_lido.get("alternativas") or [])
                         + sum((escopo_lido.get("contratado_organico") or {}).values())
                         + sum(_contratado_nao_validavel.values())
                         + sum(_nao_mensuravel_contavel.values()))
    _total_entregue = sum(entregue_total.values()) + sum(organico.values())

    # A DECLARAÇÃO NUNCA VALE MAIS QUE O CONTRATADO DAQUELE TIPO: dizer "os
    # tweets existem" cobre os 8 tweets do contrato, não 80. Sem esse teto, um
    # engano de digitação viraria cota.
    _declarado = {}
    for _tipo_dec, _quanto in (declaracoes or {}).items():
        _teto = _contratado_nao_validavel.get(_tipo_dec, 0)
        _ja_medido = entregue_total.get(_tipo_dec, 0)
        _cabe = max(0, min(int(_quanto or 0), _teto - _ja_medido))
        if _cabe:
            _declarado[_tipo_dec] = _cabe
    # O TETO CAIU PRO LADO DE FORA DA PLATAFORMA, EM 23/09/2026, e só ali:
    # o auditor perguntou se uma entrega externa (a diária de gravação, por
    # exemplo) podia cobrir a falta de OUTRO tipo, tipo story faltando, e a
    # resposta até então era não, porque o teto travava a declaração na
    # própria linha do contrato. Agora ela pode exceder o contratado, e o
    # excedente entra como SOBRA, disputável por qualquer falta, igual a
    # sobra medida (ver a montagem de _sobras mais abaixo).
    #
    # O QUE NÃO CAIU: exceder aqui exige justificativa (ver
    # `_veio_de_declaracao_externa`, mais abaixo). A diferença do teto que
    # continua em `_declarado` (tipo não validável, algumas linhas acima) é
    # exatamente essa: aquele é tipo que O DOWNLOAD MEDE e a régua não
    # valida, então o arquivo existe e pode ser conferido depois. Este aqui
    # o programa nunca vai enxergar, então a palavra de quem declarou é a
    # única evidência que existe, e por isso o excesso pede explicação por
    # escrito em vez de ficar tão barato quanto um clique.
    _declarado_nm = {}
    _excedente_nm = {}
    for _texto_dec, _quanto in (declaracoes_nao_mensuravel or {}).items():
        _teto = _nao_mensuravel_contavel.get(_texto_dec, 0)
        _quanto = max(0, int(_quanto or 0))
        _dentro = min(_quanto, _teto)
        if _dentro:
            _declarado_nm[_texto_dec] = _dentro
        _sobrou = _quanto - _dentro
        if _sobrou > 0:
            _excedente_nm[_texto_dec] = _sobrou
    _total_declarado = (sum(_declarado.values()) + sum(_declarado_nm.values())
                        + sum(_excedente_nm.values()))

    _falta_sem_declaracao = max(0, _total_contratado - _total_entregue)
    _falta_total = max(0, _total_contratado - _total_entregue - _total_declarado)
    # Fechou SÓ por causa da declaração: é o que separa CONFORME de
    # CONFORME_COM_OBSERVACAO lá embaixo.
    _fechou_por_declaracao = bool(_total_declarado) and not _falta_total and _falta_sem_declaracao

    # STORIES PEDE ATENÇÃO À PARTE, no mesmo fôlego da decisão acima: "mas as
    # entregas principais são stories, por isso temos que ter atenção a
    # isso". Mesmo com o total do ciclo fechando por outro tipo, uma queda em
    # stories entra como achado próprio e passa a exigir justificativa,
    # porque é a entrega que mais pesa na maioria dos contratos.
    _stories_contratado = contratado.get("STORIES", 0)
    _stories_entregue = entregue_total.get("STORIES", 0)
    _stories_faltando = max(0, _stories_contratado - _stories_entregue)

    tipos_do_escopo = set(contratado)
    for _q, tipos in escopo_lido.get("alternativas") or []:
        tipos_do_escopo.update(tipos)
    # OS TIPOS QUE O ESCOPO PEDE E O PROGRAMA NÃO VALIDA TAMBÉM SÃO DO ESCOPO.
    # Sem esta linha, um contrato de "12 stories + 8 tweets" fecharia NÃO
    # CONFORME por "X/TWITTER fora do escopo" quando os tweets são exatamente o
    # que foi contratado. Seria acusar mudança de composição onde não houve.
    tipos_do_escopo.update(escopo_lido.get("contratado_nao_validavel") or {})
    tipos_do_escopo.update(escopo_lido.get("contratado_organico") or {})
    # O TIPO FORA DO ESCOPO É OLHADO NO TOTAL, e não só nas peças conformes: o
    # influenciador entregou aquele formato, e isso é mudança de composição
    # independentemente de a peça ter passado na régua da portaria. CONTINUA
    # REGISTRADO com "qualquer coisa compensa qualquer coisa": a conta de
    # QUANTIDADE ficou mais solta, mas entregar algo nunca combinado é outra
    # pergunta, sobre COMPOSIÇÃO, não sobre volume.
    fora_do_escopo = {t: n for t, n in entregue_total.items()
                      if t not in tipos_do_escopo and n}

    # O QUE FALTOU E O QUE SOBROU, PARA SABER QUEM COBRIU QUEM (23/09/2026).
    # Ver o comentário grande de explicar_compensacao para a diferença entre
    # o fato (faltou isto, sobrou aquilo) e a atribuição (isto cobriu aquilo).
    #
    # AS FALTAS SÃO AS TRÊS QUE EXISTEM, e não só a mensurável:
    #   1. tipo medido abaixo do contratado (`faltando`)
    #   2. tipo que o programa não valida e ninguém declarou (tweet, YouTube)
    #   3. item de fora da plataforma que ninguém confirmou (a diária)
    # Sem as duas últimas, um ciclo em que a diária não aconteceu e sobraram
    # dois stories diria "está tudo certo", que é o contrário do que houve.
    _faltas = [{"o_que": t, "quanto": n} for t, n in faltando.items()]
    for _tipo_nv, _qtd_nv in _contratado_nao_validavel.items():
        _falta_nv = max(0, _qtd_nv - entregue_total.get(_tipo_nv, 0)
                        - _declarado.get(_tipo_nv, 0))
        if _falta_nv:
            _faltas.append({"o_que": _tipo_nv, "quanto": _falta_nv})
    for _texto_nm, _qtd_nm in _nao_mensuravel_contavel.items():
        _falta_nm = max(0, _qtd_nm - _declarado_nm.get(_texto_nm, 0))
        if _falta_nm:
            # ROTULO PRÓPRIO: o texto do contrato já começa com o número ("1
            # DIARIA DE GRAVACAO"), então a frase usa ele inteiro, entre
            # aspas, do mesmo jeito que o motivo da declaração já fazia.
            _faltas.append({"o_que": _texto_nm, "quanto": _falta_nm,
                            "rotulo": f'"{_texto_nm}"'})

    # AS SOBRAS SAEM DO QUE FOI MEDIDO, e só. Declaração nunca sobra: o teto
    # aplicado acima faz ela cobrir a própria linha do contrato e nada além,
    # então ela não tem como cobrir outro tipo.
    _sobras = []
    for _tipo_s, _feito_s in entregue_restante.items():
        _sobra_s = _feito_s - contratado.get(_tipo_s, 0)
        if _sobra_s > 0:
            _sobras.append({
                "o_que": _tipo_s, "quanto": _sobra_s,
                # Tipo que nem estava no escopo é sobra de outra natureza, e a
                # tela diz isso: cobriu a falta, mas mudou a composição.
                "origem": "fora do escopo" if _tipo_s in fora_do_escopo else "medido"})
    _organico_contratado = dict(escopo_lido.get("contratado_organico") or {})
    for _tipo_o, _feito_o in organico.items():
        _sobra_o = _feito_o - _organico_contratado.get(_tipo_o, 0)
        if _sobra_o > 0:
            _sobras.append({"o_que": f"{_tipo_o} orgânico(s)",
                            "quanto": _sobra_o, "origem": "orgânico"})
    # O EXCEDENTE DE FORA DA PLATAFORMA TAMBÉM É SOBRA (23/09/2026, ver o
    # comentário grande onde ele é calculado). Rótulo próprio, porque o texto
    # do item já traz um número dentro ("1 DIARIA DE GRAVACAO"), e sem isso a
    # frase saía "2 1 DIARIA DE GRAVACAO", repetindo o número.
    for _texto_ex, _qtd_ex in _excedente_nm.items():
        _sobras.append({
            "o_que": _texto_ex, "quanto": _qtd_ex, "origem": "fora da plataforma",
            "rotulo": f'{_qtd_ex} além do contratado em "{_texto_ex}"'})

    compensacao = explicar_compensacao(_faltas, _sobras)
    _texto_compensacao = texto_da_compensacao(compensacao)

    # SÓ EXCEDER NÃO BASTA: A COBERTURA PRECISA TER SIDO USADA DE VERDADE
    # (23/09/2026). Declarar 5 diárias quando só 1 era pedida não pede
    # explicação nenhuma se o ciclo já fechava sem elas; o que pede
    # explicação é o excedente TER SIDO NECESSÁRIO para cobrir outra falta,
    # porque aí a palavra de quem declarou passou a decidir o fechamento, e o
    # programa não tem como conferir aquele número sozinho.
    _veio_de_declaracao_externa = any(
        p.get("origem") == "fora da plataforma"
        for item in compensacao for p in (item.get("por") or []))

    motivos = []
    # "SEM NENHUMA ENTREGA" SÓ CONTA QUANDO AINDA FALTA DE VERDADE (16/09/2026):
    # com o total podendo compensar, um tipo zerado sozinho não quer dizer
    # mais nada sobre o ciclo como um todo.
    nada_entregue = {t: n for t, n in contratado.items()
                     if not entregue_restante.get(t, 0) and n and _falta_total}
    if nada_entregue:
        motivos.append(
            "Tipo do escopo sem nenhuma entrega neste ciclo: "
            + ", ".join(f"{t} (contratado {n})" for t, n in sorted(nada_entregue.items())))
    if fora_do_escopo:
        motivos.append(
            "Tipo entregue que não está no escopo: "
            + ", ".join(f"{t} ({n} post(s))" for t, n in sorted(fora_do_escopo.items())))
    # O QUE COBRIU O QUÊ, POR EXTENSO (23/09/2026, substitui "parecem
    # compensadas"). A frase antiga dizia que algo tinha sido compensado sem
    # dizer o quê, porque a conta que existia era só de dois totais. Agora a
    # conta é por item (ver explicar_compensacao), então o texto diz.
    #
    # "PARECEM" SAIU DE PROPÓSITO: ela era honesta com a conta antiga e passou
    # a ser falsa modéstia com a nova. O que continua não sendo afirmação de
    # verdade é a ATRIBUIÇÃO quando há mais de uma sobra, e isso está tratado
    # no comentário de explicar_compensacao, não no texto da tela.
    #
    # QUANDO O CICLO É INCOMPLETO DE VERDADE (total não fecha) E NINGUÉM
    # DECLAROU nada de fora da plataforma, o motivo detalha o número de cada
    # tipo: é a única pista de qual tipo precisa de atenção, porque a mensagem
    # de "falta no total" (mais abaixo) não diz qual. Com declaração
    # envolvida, a mensagem própria dela já explica, e duplicar confundiria.
    _tem_declaracao_externa = bool(_declarado) or bool(_declarado_nm)
    if not _falta_total and _texto_compensacao:
        motivos.append(f"Entregas compensadas: {_texto_compensacao}. "
                       f"O total do ciclo fechou.")
    elif _falta_total and not _tem_declaracao_externa:
        _com_falta = dict(faltando)
        if _stories_faltando:
            _com_falta.setdefault("STORIES", _stories_faltando)
        if _com_falta:
            motivos.append(
                "ATENÇÃO: "
                + ", ".join(f"{t} entregou {contratado.get(t, 0) - n} de "
                            f"{contratado.get(t, 0)}, {n} a menos"
                            for t, n in sorted(_com_falta.items()))
                + ".")
    # PEÇA REPROVADA VIRA AVISO, NÃO TRAVA (16/09/2026, revisão de
    # 31/08/2026): aparece sempre que existir, independente da situação final,
    # porque "sempre haverá algum não conforme que pode passar", e o ponto
    # agora é avisar pra não repetir, não impedir o ciclo de fechar.
    if reprovadas:
        motivos.append(
            f"ATENÇÃO: {len(reprovadas)} peça(s) deste ciclo não passaram na "
            f"régua da portaria. Contam como entrega mesmo assim; revise o "
            f"que faltou nelas para não se repetir.")

    # A FALTA DE QUANTIDADE É DITA SEMPRE, e não só quando ela é o único
    # problema (corrigido em 03/09/2026, ao rodar no dado real). Desde
    # 16/09/2026 ela é do TOTAL, não mais por tipo: ver o comentário acima de
    # "QUALQUER TIPO COMPENSA QUALQUER TIPO".
    if _falta_total:
        motivos.append(
            f"Falta quantidade no total do ciclo: entregue {_total_entregue} de "
            f"{_total_contratado} contratados, somando todos os tipos juntos.")
    # A DECLARAÇÃO APARECE SEMPRE QUE FOI USADA, inclusive quando o ciclo
    # fecha: é ela que explica por que o total bate sem o programa ter medido
    # tudo. Sem esta linha, "apto a pagamento" apareceria sem dizer que parte
    # veio de conferência humana.
    if _declarado:
        motivos.append(
            "Conferido à mão por quem fechou, e contado no total: "
            + ", ".join(f"{t} ({n})" for t, n in sorted(_declarado.items())))
    # ENTREGA FORA DA PLATAFORMA CONFIRMADA (17/09/2026): vira motivo próprio,
    # e não some junto com `_declarado`, porque o texto do item já é longo
    # (ex: "2 diárias de gravação para a marca") e merecia linha própria.
    if _declarado_nm:
        motivos.append(
            "Entrega fora da plataforma confirmada por quem fechou, e "
            "contada no total: "
            + "; ".join(f"\"{t}\" ({n})" for t, n in sorted(_declarado_nm.items())))

    if _falta_total:
        situacao = INCOMPLETO
    elif sem_veredito:
        situacao = COTA_ESPERANDO_ANALISE
        motivos.append(
            f"A quantidade do escopo fecha, mas {len(sem_veredito)} peça(s) "
            f"ainda não têm veredito da análise. A cota não pode ser declarada "
            f"cumprida antes de saber se elas passam.")
    elif sem_evidencia:
        # A ORDEM É PROPOSITAL: evidência inacessível vem antes do limite da
        # automação porque é o problema mais barato de resolver e o que trava
        # mais linhas no dado real (223 contra 118 no papel de trabalho).
        situacao = COTA_SEM_EVIDENCIA
        motivos.append(
            f"A quantidade do escopo fecha, mas em {len(sem_evidencia)} peça(s) "
            f"a análise não conseguiu abrir o material: pasta vazia, sem acesso "
            f"à pasta, ou link apontando para a rede social em vez do arquivo. "
            f"Na aba Achado03 do papel de trabalho isso é "
            f"\"{CATEGORIA_GAP_EVIDENCIA}\", e se resolve conseguindo o arquivo.")
    elif limite_da_automacao:
        situacao = COTA_NO_LIMITE_DA_AUTOMACAO
        motivos.append(
            f"A quantidade do escopo fecha, mas em {len(limite_da_automacao)} "
            f"peça(s) a automação não conseguiu decidir, normalmente aviso "
            f"pequeno ou de baixo contraste. Na aba Achado03 isso é "
            f"\"{CATEGORIA_GAP_LIMITACAO}\", e precisa de alguém olhando a peça.")
    elif _fechou_por_declaracao:
        # SÓ FECHOU PORQUE ALGUÉM DECLAROU. Ver o comentário de
        # CONFORME_COM_OBSERVACAO: o ciclo segue apto a pagamento, e a
        # situação guarda que parte do número não foi medida.
        situacao = CONFORME_COM_OBSERVACAO
    else:
        situacao = CONFORME

    return {
        "situacao": situacao,
        # A JUSTIFICATIVA PASSOU A GATE DE "SOLICITAR PAGAMENTO" (09/09/2026),
        # e por isso cobre as DUAS razões pelas quais o ciclo está diferente do
        # escopo: não fechou em quantidade/situação (ENTREGA_NAO_FECHOU,
        # inclui INCOMPLETO e as situações do meio), OU veio composição fora
        # do contrato (fora_do_escopo), mesmo com a cota fechando. As duas são
        # a mesma pergunta no fundo, "isto está de acordo com o escopo?", e por
        # isso viraram um campo só, não duas justificativas separadas.
        #
        # QUALQUER TIPO QUE FICOU ABAIXO DO CONTRATADO ENTRA AQUI (17/09/2026,
        # generalizado a partir da régua que nasceu só para Stories em
        # 16/09/2026): mesmo com o TOTAL do ciclo fechando, se um tipo
        # específico ficou abaixo do que foi combinado, isso é composição
        # diferente do contrato, e pede explicação. `faltando` já traz essa
        # conta pronta, tipo por tipo, sem contar alternativa consumida (ver
        # "STORIES PEDE ATENÇÃO À PARTE" e "QUALQUER TIPO QUE FICOU PRA TRÁS"
        # um pouco acima, onde os motivos ficam em texto).
        # ENTREGA FORA DA PLATAFORMA SÓ PEDE JUSTIFICATIVA QUANDO SOBRA
        # ALGUMA COISA A EXPLICAR (REVISTO 17/09/2026, mesmo dia da versão
        # anterior, depois de testar ao vivo com o caso @saporitorenata: 12
        # stories + 5 reels batendo exato, e a diária confirmada fechando o
        # total certinho, sem substituição nenhuma). Marcar o CHECK sozinho
        # não entra mais na conta: se o ciclo fecha por inteiro (nenhum tipo
        # mensurável faltando, nada fora do escopo, situação não é
        # INCOMPLETO nem as do meio), a confirmação é só isso, uma
        # confirmação, e o motivo automático "Entrega fora da plataforma
        # confirmada..." já registra o que aconteceu, sem precisar de texto
        # escrito. Continua exigindo quando: o ciclo permanece INCOMPLETO
        # mesmo com a declaração (faltou entrega de verdade, não só faltou
        # medir), ou algum tipo mensurável ficou abaixo do combinado
        # (`faltando`, substituição real de composição), ou veio tipo fora
        # do escopo. As três condições abaixo já cobriam isso sozinhas.
        #
        # `faltando` SOZINHO DEIXOU DE PEDIR JUSTIFICATIVA (23/09/2026, pedido
        # do auditor, revendo a régua que nasceu em 16-17/09). O motivo dele é
        # direto: "caso tenha sido compensada ou a entrega bateu exatamente
        # com o que está no escopo, essa parte da Observação não precisa
        # aparecer, quero que ela apareça apenas se a entrega for divergente e
        # MENOR". Quando o total não fecha, a situação já é INCOMPLETO e cai
        # em ENTREGA_NAO_FECHOU, que continua pedindo. Ou seja: o que saiu foi
        # exatamente o caso "faltou um tipo, mas outro cobriu e o total
        # fechou".
        #
        # O REGISTRO NÃO SE PERDE COM ISSO, e essa é a condição que tornou a
        # mudança aceitável do lado da auditoria: no mesmo pedido, o ciclo
        # compensado passou a gravar `nota_automatica` no histórico, escrita
        # pelo programa, dizendo o que cobriu o quê. Antes o registro dependia
        # de alguém digitar; agora ele existe sempre, e a pessoa só escreve
        # quando há algo que o programa não tem como saber.
        #
        # TIPO FORA DO ESCOPO TAMBÉM PAROU DE PEDIR, no mesmo dia (23/09/2026).
        # Eu tinha mantido esta exceção e levantado ela: entregar um formato
        # que nunca foi contratado é pergunta sobre COMPOSIÇÃO, não sobre
        # volume, e o pedido falava de entrega "menor". O auditor foi
        # consultado com essa ressalva na mão e respondeu para tirar também.
        #
        # ENTÃO SOBROU UMA CONDIÇÃO, e ela é exatamente a frase dele: a
        # Observação escrita à mão aparece quando o ciclo NÃO FECHOU, que é o
        # "divergente e menor". Todo o resto (compensado, batendo exato,
        # composição trocada) é registrado pelo programa em `nota_automatica`,
        # que diz o que cobriu o quê e cita o tipo fora do escopo pelo nome.
        # Ou seja: o rastro da flexibilização continua, só deixou de depender
        # de alguém digitar para o ciclo poder ser registrado.
        #
        # UMA SEGUNDA CONDIÇÃO ENTROU DEPOIS, NO MESMO DIA: excedente de
        # entrega fora da plataforma cobrindo falta de outro tipo. A diferença
        # para o resto desta lista é a origem da evidência: compensação por
        # tipo medido ou por composição trocada tem arquivo no Drive, que dá
        # para conferir depois. Excedente de fora da plataforma é só a
        # palavra de quem declarou, então quando ele decide o fechamento
        # (não quando é só folga, sem ser usado), a Observação volta a ser
        # obrigatória. Ver `_veio_de_declaracao_externa`, calculado acima.
        "exige_justificativa": (situacao in ENTREGA_NAO_FECHOU
                                or _veio_de_declaracao_externa),
        "por_tipo": por_tipo,
        "faltando": faltando,
        "fora_do_escopo": fora_do_escopo,
        "motivos": motivos,
        # QUEM COBRIU QUEM, estruturado, para a tela poder mostrar item a item
        # em vez de repetir a frase pronta (23/09/2026).
        "compensacao": compensacao,
        # O TEXTO QUE VAI PARA A COLUNA NOTA DO HISTÓRICO quando ninguém
        # escreve nada (23/09/2026, pedido do auditor: "para entregas que
        # foram compensadas ou que estão ok, a coluna NOTA pode ficar com
        # avisos como Ciclo completo ou Ciclo completo/Compensado, mas já
        # automático, para existir o registro").
        #
        # SÓ PARA CICLO QUE FECHOU: num ciclo que não fechou a justificativa
        # continua obrigatória, e uma nota automática ali roubaria o lugar do
        # que a pessoa tem que explicar.
        "nota_automatica": _nota_automatica(situacao, _texto_compensacao,
                                            fora_do_escopo),
        # OS TRÊS TOTAIS QUE DECIDIRAM A SITUAÇÃO ACIMA, EXPOSTOS AQUI
        # (16/09/2026): quem grava um histórico de entregas (ver
        # pages/3_Financeiro.py) precisa do mesmo número que decidiu
        # CONFORME/INCOMPLETO, não de uma soma recalculada por fora que pode
        # divergir num caso de borda (por exemplo, tipo que aparece contratado
        # sozinho E dentro de uma alternativa ao mesmo tempo).
        "total_contratado": _total_contratado,
        "total_entregue": _total_entregue,
        "conferir_a_mao": _conferir_a_mao(escopo_lido, organico),
    }


def _nota_automatica(situacao, texto_compensacao, fora_do_escopo):
    """O que o programa escreve na coluna NOTA quando ninguém escreve nada.

    NASCEU EM 23/09/2026, junto com a queda da justificativa obrigatória para
    ciclo compensado. As duas coisas andam juntas de propósito: a Observação
    escrita à mão deixou de ser exigida ali, e o registro que ela garantia
    passa a ser escrito pelo programa, com o que ele sabe.

    NUNCA SUBSTITUI O QUE A PESSOA ESCREVEU: quem chama usa isto só quando o
    campo veio vazio (ver pages/3_Financeiro.py). O texto de gente diz por que
    aconteceu; este aqui só diz o que aconteceu.

    Vazio quando o ciclo não fechou: ali a justificativa continua obrigatória,
    e uma nota automática tomaria o lugar da explicação que falta."""
    if situacao not in (CONFORME, CONFORME_COM_OBSERVACAO):
        return ""
    # A REDAÇÃO É A DO AUDITOR (23/09/2026): "Ciclo completo", ou "Ciclo
    # completo (entrega compensada)". O detalhe do que cobriu o quê vai
    # DENTRO do parêntese, e não no lugar dele, porque foi ele mesmo quem
    # pediu, algumas horas antes no mesmo dia, que o programa parasse de
    # dizer só que algo "parece compensado" sem dizer o quê.
    dentro = []
    if texto_compensacao:
        dentro.append(f"entrega compensada: {texto_compensacao}")
    if fora_do_escopo:
        dentro.append("tipo entregue fora do escopo: "
                      + ", ".join(sorted(fora_do_escopo)))
    if not dentro:
        return "Ciclo completo."
    return "Ciclo completo (" + "; ".join(dentro) + ")."


def _conferir_a_mao(escopo_lido, organico):
    """O que o fechamento NÃO mediu, e por isso não pode afirmar conformidade.

    Existe para o fechamento não ficar mais confiante do que ele tem direito de
    ser. Sem esta lista, um ciclo com "presença em 4 eventos" no escopo fecharia
    CONFORME olhando só os posts."""
    saida = []
    # AS CATEGORIAS QUE O PROGRAMA NÃO RESOLVE SOZINHO (03/09/2026, eram
    # quatro; a de orgânico contratado saiu em 17/09/2026, ver o comentário
    # mais abaixo), achadas no dado real. Elas aparecem aqui porque um
    # fechamento que não as mostra afirma conformidade sobre o que não olhou.
    for tipo, quantidade in sorted(
            (escopo_lido.get("contratado_nao_validavel") or {}).items()):
        saida.append(
            f"{quantidade} de {tipo}: a análise regulatória não alcança esse "
            f"tipo, então nenhuma peça dele fica CONFORME. Decidir se conta é "
            f"de quem fecha")
    # A NOTA SOBRE ORGÂNICO CONTRATADO SAIU DAQUI (17/09/2026, mesmo dia da
    # correção do texto acima). Pedido do auditor: diferente do que a análise
    # regulatória não alcança (o loop acima, que ainda pede uma decisão real
    # na tela, o rádio "Conferi à mão"), orgânico já é conferido pelo
    # analista na rotina normal, e não precisa de veredito nenhum, só de
    # sinalizar que foi postado, o que a contagem automática já faz. Uma
    # observação cujo único efeito era mandar "conferir a peça" sem nenhuma
    # ação correspondente na tela era só poluição visual, sem função.
    for quantidade, trecho in escopo_lido.get("ambiguos") or []:
        saida.append(
            f"\"{trecho}\": o escopo pede {quantidade}, sem dizer o formato. "
            f"Qual tipo conta é leitura de contrato")
    for trecho in escopo_lido.get("condicionais") or []:
        saida.append(
            f"\"{trecho}\": a quantidade depende de condição escrita no "
            f"contrato, e o programa não sabe qual mês do contrato é este ciclo")

    telas = escopo_lido.get("telas_por_combo")
    if telas:
        saida.append(
            f"Este contrato declara combo de {telas} telas. A contagem é por "
            f"POST do dia, então um combo publicado em dois dias aparece como "
            f"dois. Conferir se as telas por dia fecham o combo")
    for quantidade, item in escopo_lido.get("nao_mensuraveis") or []:
        if quantidade:
            saida.append(f"{item} (download não mede isso; pode ser "
                         f"confirmado e contado no total, com justificativa)")
        else:
            saida.append(f"{item} (download não mede isso)")
    for item in escopo_lido.get("anuais") or []:
        saida.append(f"{item} (marcado ANUAL no escopo, fora do ciclo)")
    for item in escopo_lido.get("nao_reconhecido") or []:
        saida.append(f"{item} (o programa não reconheceu o tipo)")
    for tipo, n in sorted(organico.items()):
        saida.append(f"{n} post(s) {tipo} marcados como ORGÂNICO "
                     f"(conferir se contam no escopo deste contrato)")
    return saida


# ---------------------------------------------------------------------------
# Quando o fechamento exige justificativa para SOLICITAR PAGAMENTO
# ---------------------------------------------------------------------------
# ESTA SEÇÃO MUDOU DE FORMA EM 09/09/2026. Existia um rádio "Este ciclo já foi
# pago?" (NÃO PAGO/PARCIALMENTE PAGO/PAGO) que registrava o que já tinha
# ACONTECIDO, e um achado próprio ("PAGAMENTO SEM A ENTREGA FECHADA") quando
# alguém reportava pagamento num ciclo que não tinha fechado. O auditor
# apontou o problema de fundo: "o pagamento vem depois do ciclo fechado...
# então essa mensagem é para pagamento do ciclo e não do escopo". Ou seja, o
# fluxo real é ESCOPO → ciclo entregue → SOLICITA o pagamento → ciclo
# seguinte. Perguntar "já foi pago?" no meio desse fluxo pressupõe que o
# pagamento pode acontecer ANTES da solicitação, que é exatamente o que o
# programa deveria evitar, não registrar depois.
#
# A régua ficou mais simples, e ainda a mesma pergunta de sempre: o ciclo
# está de acordo com o escopo, ou está diferente (faltou quantidade, ou veio
# composição fora do contrato)? No primeiro caso, solicita direto. No
# segundo, só solicita depois de alguém escrever por que autoriza mesmo
# assim, e isso fica gravado (quem e o porquê) no registro do fechamento.
#
# As situações de entrega em que a cota NÃO fechou. Junto com qualquer
# composição fora do escopo, são o que agora exige a justificativa (ver
# "exige_justificativa" em fechar_ciclo).
#
# COTA_SEM_EVIDENCIA E COTA_NO_LIMITE_DA_AUTOMACAO ENTRARAM AQUI EM 04/09/2026,
# e a falta delas era um buraco real, não teórico. Cruzando este achado com o
# dado real da aba Achado01_EntregaEComprovacao (260 linhas), 74 delas (28,5%)
# têm pagamento registrado (PAGO ou PARCIALMENTE PAGO) numa linha em que a
# quantidade do escopo fecha mas falta o link de comprovação da entrega, que é
# exatamente a situação COTA_SEM_EVIDENCIA. Sem esta linha na tupla, era
# precisamente esse padrão, o mais comum entre os casos de pagamento com
# problema no dado real, que passava sem exigir justificativa. Exemplos reais:
# @adrianamunizofc ciclo 7, @alvinegrosou ciclo 6, @babamarcoss ciclo 4, todos
# PAGO ou PARCIALMENTE PAGO com "sem link válido" na observação.
# COTA_COM_PECA_REPROVADA SAIU DAQUI EM 16/09/2026, junto com a situação:
# peça reprovada não trava mais o fechamento, então também deixou de exigir
# justificativa pra solicitar pagamento (vira só aviso, ver fechar_ciclo).
ENTREGA_NAO_FECHOU = (INCOMPLETO, SEM_BASE,
                      COTA_ESPERANDO_ANALISE,
                      SEM_COTA_MENSURAVEL, COTA_SEM_EVIDENCIA,
                      COTA_NO_LIMITE_DA_AUTOMACAO)


# ---------------------------------------------------------------------------
# O cronograma do ciclo, para o texto do Financeiro
# ---------------------------------------------------------------------------
# POR QUE ISTO EXISTE (11/09/2026)
#
# O texto do Financeiro listava só o que foi baixado, tudo com ✅, e nunca uma
# data com ❌. O auditor corrigiu a premissa: "essa mensagem é de acordo com
# essa planilha do calendário que automatizamos agora. a cada rodada de post
# eles marcam o check na data que consta na planilha do calendário que é
# anteriormente preenchida por eles".
#
# Conferido contra o Calendário real em 11/09/2026 (aba AGO.26, 25 linhas de
# @lucasguimaraes) contra o print de um cronograma real: 11 das 15 datas batem
# exatamente, inclusive a ausência de 19/08 nos dois lados.
#
# E AS OUTRAS 4 SÃO A RAZÃO DESTA FUNÇÃO NÃO TER COPIADO O STATUS DELES, ATÉ
# 16/09/2026. Divergiram assim: 16/08 estava ✅ no cronograma e "Não Postada"
# no Calendário; 27/08 estava ✅ no cronograma e com Status vazio; 17/08 saiu
# como LOTTU no cronograma e EDS no Calendário; 14/08 estava "Não Postada" no
# Calendário e nem aparecia no cronograma.
#
# REVERTIDO EM 16/09/2026: o caso "Calendário marcou Publicada, sem vídeo
# captado aqui" (o antigo DIVERGENCIA) passou a contar como ENTREGUE também,
# com número na sequência, igual a um post de verdade. Decisão do auditor,
# depois de eu explicar o ⚠️: "não precisa colocar isso, é um processo
# interno deles, se eles marcaram, pode colocar verde como entregue mesmo".
# A ferramenta é deles, e confiar no processo interno deles é escolha válida
# quando quem decide é quem responde por aquele processo.
#
# O QUE NÃO MUDA: esta função é só o CHECKLIST descritivo do WhatsApp. A
# conta de escopo x entrega que decide se o ciclo fechou (fechar_ciclo,
# contar_entregas) continua exigindo vídeo real, baixado e com veredito
# CONFORME da régua da portaria. Confiar na marcação deles aqui não dá cota
# de ciclo a ninguém.
#
# DIVERGENCIA FICA DEFINIDA, MAS NUNCA MAIS PRODUZIDA POR ESTA FUNÇÃO
# (compatibilidade com quem ainda lê a constante, ex. o ícone e o nome em
# pages/3_Financeiro.py).
ENTREGUE = "ENTREGUE"
NAO_POSTADA = "NAO_POSTADA"
DIVERGENCIA = "DIVERGENCIA"
PENDENTE = "PENDENTE"

# A ÚNICA NOTA QUE VAI PARA A MENSAGEM DO WHATSAPP (16/09/2026, ver
# pages/3_Financeiro.py:linha_de_cronograma). As outras três notas abaixo são
# leitura NOSSA sobre uma diferença entre o Calendário e o que foi baixado, e
# o pedido do auditor foi tirar essa camada de comparação do texto que vai
# para o Marketing: "deixar apenas como está na planilha deles". Esta é
# diferente porque não é comparação nenhuma, é avisar que não existe linha
# com que comparar, e isso o Marketing não tem como saber sozinho.
NOTA_SEM_LINHA = "sem linha no Calendário"


def montar_cronograma(posts, linhas_calendario):
    """Uma linha por data do ciclo, juntando o Calendário e o que foi baixado.

    `posts` é contagem["posts"] (o que a auditoria tem, com data já convertida).
    `linhas_calendario` vem de calendario_divulgacoes.linhas_do_influenciador.

    Devolve uma lista ordenada por data, com um dicionário por data:
      data      a data, como data
      marca     a marca daquela linha do Calendário, ou vazio
      estado    ENTREGUE, NAO_POSTADA ou PENDENTE (DIVERGENCIA não é mais
                produzido desde 16/09/2026: Calendário marcado como
                Publicada já conta como ENTREGUE, com ou sem vídeo captado)
      numero    a posição na contagem de entregas, só para ENTREGUE
      nota      o que precisa ser dito naquela linha, ou vazio

    A NUMERAÇÃO CONTA SÓ ENTREGA, como no cronograma real: data sem post não
    recebe número. E ela segue a ordem das datas, não a ordem de download."""
    import calendario_divulgacoes as cal

    por_data = {}
    for linha in linhas_calendario or []:
        por_data.setdefault(linha["data"], []).append(linha)
    entregues = {p["data"] for p in (posts or []) if p.get("data")}

    itens, numero = [], 0
    for data in sorted(set(por_data) | entregues):
        do_calendario = por_data.get(data, [])
        status = [l.get("status", "") for l in do_calendario]
        publicada = any(cal.e_publicada(s) for s in status)
        nao_postada = any(cal.e_nao_postada(s) for s in status)
        marca = ", ".join(sorted({l.get("marca", "").strip()
                                  for l in do_calendario if l.get("marca")}))
        nota = ""
        if data in entregues or publicada:
            # AS DUAS RAZÕES DE CONTAR COMO ENTREGUE (16/09/2026): tem vídeo
            # captado aqui, OU o Calendário deles marcou Publicada. Ver o
            # comentário grande acima de ENTREGUE/DIVERGENCIA para o porquê.
            numero += 1
            estado = ENTREGUE
            if data in entregues:
                if nao_postada and not publicada:
                    nota = "o Calendário marcou Não Postada"
                elif not do_calendario:
                    nota = NOTA_SEM_LINHA
                elif not publicada:
                    nota = "o Calendário ainda não foi marcado"
        elif nao_postada:
            estado = NAO_POSTADA
        else:
            # Data planejada que ainda não foi marcada por ninguém. É a linha
            # sem marca no fim do cronograma real.
            estado = PENDENTE
        itens.append({"data": data, "marca": marca, "estado": estado,
                      "numero": numero if estado == ENTREGUE else None,
                      "nota": nota})
    return itens
