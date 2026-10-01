# -*- coding: utf-8 -*-
"""
O Calendário Geral de Divulgações do Marketing.

É uma planilha SEPARADA da Monitoramento, com uma linha por post planejado. O
Marketing preenche à mão influenciador, marca, responsável e data; o programa
preenche o que só existe depois do vídeo: Jogo, Status, Horário e Monitorado
por. Ver DESENHO_CALENDARIO.md para tudo o que foi medido antes de desenhar.

A ESTRUTURA, medida em 11/09/2026 nas abas AGO.26 e SET.26, 1.984 linhas:

  - uma aba por mês, nomeada MMM.AA (de DEZ.25 a DEZ.26)
  - cabeçalho na linha 2, dados a partir da linha 3, linha 1 vazia
  - colunas A a I: Influenciador, Marca, Responsável, Jogo, Status,
    Data da postagem, Horário, "Monitorado por:", "Coluna 1"

POR QUE ESTE MÓDULO NÃO IMPORTA `fluxo_downloads` NO TOPO (11/09/2026): o
`fluxo_downloads` importa este módulo de volta, dentro das funções que
escrevem no Calendário. Importação nos dois sentidos, com uma delas no topo,
é ciclo esperando para acontecer no dia em que a ordem de importação mudar.
Os caminhos aqui saem do próprio arquivo, e o que precisa do `fluxo_downloads`
o importa dentro da função.
"""
import os

import data_de_planilha

BASE = os.path.dirname(os.path.abspath(__file__))

# A linha 1 é vazia e a 2 é o cabeçalho. Dado começa na 3.
PRIMEIRA_LINHA = 3

COL = {"influenciador": 0, "marca": 1, "responsavel": 2, "jogo": 3,
       "status": 4, "data": 5, "horario": 6, "monitorado": 7}

# Até a coluna I, que é a última com dono na planilha deles.
ULTIMA_COLUNA = "I"

# OS DOIS ÚNICOS VALORES QUE EXISTEM na coluna Status da planilha deles,
# medido em 1.984 linhas: Publicada (946), Não Postada (415) e vazio (623).
# "Apagada" NÃO existe lá, e criar vocabulário novo na planilha de outra área
# é decisão deles, não nossa. Decidido com o auditor em 11/09/2026.
STATUS_PUBLICADA = "Publicada"
STATUS_NAO_POSTADA = "Não Postada"

# Como o Marketing escreve os meses no nome das abas.
MESES_DA_ABA = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
                "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

# O identificador da planilha REAL mora junto dos outros três de produção, e
# NÃO em teste_watch_folder. É o mesmo mecanismo do modo real: faltando
# qualquer peça, o programa escreve na cópia de teste, que é o seguro.
ARQUIVO_ID_REAL = os.path.join(BASE, "marketing_producao", "calendario_id.txt")
ARQUIVO_ID_TESTE = os.path.join(BASE, "teste_watch_folder",
                                "calendario_teste_id.txt")


def normalizar_handle(bruto):
    """O @ como chave de comparação.

    Na planilha deles o mesmo influenciador aparece como "@Giroquue",
    "giroquue" e "nathanqueiroz  ". Sem isto o casamento falharia em silêncio,
    que é o pior resultado possível aqui: a linha fica vazia e ninguém sabe
    por quê."""
    return str(bruto or "").strip().lstrip("@").strip().lower()


def normalizar_marca(bruto):
    """A marca como chave de comparação.

    Agosto escreve EDSCAP e setembro escreve EDS CAP, na MESMA planilha. Tirar
    todo espaço resolve as duas grafias, e a caixa alta deixa a comparação
    estável."""
    return "".join(str(bruto or "").split()).upper()


def aba_do_mes(data):
    """O nome da aba a partir da data do post: 11/09/2026 -> 'SET.26'."""
    if data is None:
        return None
    return f"{MESES_DA_ABA[data.month - 1]}.{data.year % 100:02d}"


def letra(nome):
    return chr(ord("A") + COL[nome])


def _campo(linha, nome):
    indice = COL[nome]
    return str(linha[indice]).strip() if len(linha) > indice else ""


def achar_linha(linhas, handle, marca, data):
    """Em qual linha da planilha escrever, ou por que não dá.

    `linhas` são os valores devolvidos pelo Sheets a partir da PRIMEIRA_LINHA.
    Devolve (numero_da_linha_na_planilha, motivo). Com linha achada, o motivo
    é vazio.

    A REGRA DA PRIMEIRA VAZIA (11/09/2026): a chave influenciador + marca +
    data repete em cerca de 3% das linhas, sempre duas vezes, e é quem posta
    dois stories no mesmo dia (andersonneiff, eduardagutierrez, weslleyof_).
    Escrever sempre na primeira que ainda está com Status vazio faz a primeira
    entrega cair na primeira linha e a segunda na segunda, sem o programa
    precisar saber qual story é qual."""
    procurado = (normalizar_handle(handle), normalizar_marca(marca))
    casaram = []
    for posicao, linha in enumerate(linhas):
        chave = (normalizar_handle(_campo(linha, "influenciador")),
                 normalizar_marca(_campo(linha, "marca")))
        if chave != procurado:
            continue
        # DATA COMPARADA COMO DATA, NUNCA COMO TEXTO. "06/09/2026" gravado no
        # Sheets volta "06/09/26", e comparar texto falharia sem dar erro.
        if not data_de_planilha.mesmo_dia(_campo(linha, "data"), data):
            continue
        casaram.append((PRIMEIRA_LINHA + posicao, linha))

    # O @ SAI NORMALIZADO NA MENSAGEM (11/09/2026). Com o handle vindo com @
    # do endereço, a mensagem saía "@@leticiadisher_", que lê como defeito de
    # programa e desvia a atenção de quem está procurando a causa real.
    visivel = normalizar_handle(handle)
    if not casaram:
        return None, (f"Não achei linha no Calendário para @{visivel}, "
                      f"{marca}, {data:%d/%m/%Y}.")
    for numero, linha in casaram:
        if not _campo(linha, "status"):
            return numero, ""
    return None, (f"As {len(casaram)} linha(s) de @{visivel}, {marca}, "
                  f"{data:%d/%m/%Y} já estão preenchidas. Não sobrescrevi.")


def abas_entre(primeira, ultima):
    """Os nomes de aba, em ordem, que cobrem o intervalo de datas.

    Um ciclo atravessa o mês com frequência (13/08 a 02/09, por exemplo), e no
    Calendário cada mês é uma aba separada. Ler só a aba da primeira data
    perderia metade do ciclo em silêncio."""
    if primeira is None or ultima is None or ultima < primeira:
        return []
    nomes, ano, mes = [], primeira.year, primeira.month
    while (ano, mes) <= (ultima.year, ultima.month):
        nomes.append(f"{MESES_DA_ABA[mes - 1]}.{ano % 100:02d}")
        mes += 1
        if mes > 12:
            mes, ano = 1, ano + 1
    return nomes


def linhas_do_influenciador(handle, primeira, ultima):
    """As linhas do Calendário daquele @ entre duas datas, em ordem de data.

    POR QUE ISTO EXISTE (11/09/2026): o cronograma que o Marketing manda no
    grupo lista TAMBÉM as datas em que o influenciador não postou, e essas
    datas não existem na Monitoramento, só aqui. Sem esta leitura, o texto do
    Financeiro só sabe listar o que foi entregue.

    NÃO FILTRA POR MARCA, de propósito. No cronograma real que o auditor
    mostrou, o cabeçalho traz uma marca e as linhas trazem outra: o mesmo ciclo
    de um influenciador mistura marcas (medido em 11/09/2026 nas linhas de
    `@lucasguimaraes` em AGO.26, com linhas LOTTU e EDS no mesmo intervalo).
    Filtrar por marca faria sumir entrega que aconteceu. A marca de cada linha
    vai junto, para quem lê ver de qual foi cada post.

    Devolve (linhas, problemas). `problemas` traz o que não deu para ler, e
    existe para a tela poder dizer que a lista está incompleta em vez de
    mostrar um cronograma curto como se fosse o cronograma inteiro."""
    procurado = normalizar_handle(handle)
    achadas, problemas = [], []
    for aba in abas_entre(primeira, ultima):
        try:
            linhas = ler_aba(aba)
        except Exception as e:
            if _aba_nao_existe(e):
                # ABA QUE NÃO EXISTE NÃO É PROBLEMA DE LEITURA, É LIMITE DO
                # CALENDÁRIO (11/09/2026). Ele começa em DEZ.25 (ver o
                # cabeçalho deste arquivo); mês antes disso, ou mês futuro
                # ainda não criado, nunca vai ter aba. Um aviso técnico repetido
                # por mês faltante ("<HttpError 400... Unable to parse
                # range...>") assustava mais do que informava, e a mesma frase
                # aparecia uma vez por mês faltante. Só falta de verdade (rede,
                # permissão) continua caindo em `problemas`.
                continue
            problemas.append(f"aba {aba}: {str(e)[:120]}")
            continue
        for posicao, linha in enumerate(linhas):
            if normalizar_handle(_campo(linha, "influenciador")) != procurado:
                continue
            # DATA COMO DATA, NUNCA COMO TEXTO: a mesma regra do resto do
            # arquivo. Aqui ela decide se a linha é ou não deste ciclo.
            data = data_de_planilha.data_de_celula(_campo(linha, "data"))
            if data is None or not (primeira <= data <= ultima):
                continue
            achadas.append({"aba": aba, "linha": PRIMEIRA_LINHA + posicao,
                            "data": data, "marca": _campo(linha, "marca"),
                            "status": _campo(linha, "status"),
                            "jogo": _campo(linha, "jogo")})
    achadas.sort(key=lambda l: (l["data"], l["linha"]))
    return achadas, problemas


def _aba_nao_existe(erro):
    """Se o erro é 'esta aba não existe na planilha', e não outra falha.

    A API do Sheets devolve HttpError 400 com "Unable to parse range" quando o
    NOME da aba não existe (medido em 11/09/2026, pedindo 'ABR.26' na cópia de
    teste). É o único caso em que a mensagem de erro é o esperado, não uma
    falha: mês sem aba é normal fora da faixa que o Calendário cobre."""
    return "Unable to parse range" in str(erro)


def e_publicada(status):
    """Se o Status daquela linha diz que o post saiu."""
    return str(status or "").strip().lower() == STATUS_PUBLICADA.lower()


def e_nao_postada(status):
    """Se o Status daquela linha diz que o post não saiu.

    Compara sem acento e sem caixa porque na planilha real a mesma marcação
    aparece como "Não Postada" e "NÃO POSTADA"."""
    limpo = str(status or "").strip().lower().replace("ã", "a")
    return limpo == STATUS_NAO_POSTADA.lower().replace("ã", "a")


def apelidos_conhecidos(linhas):
    """Os nomes já usados na coluna 'Monitorado por', em minúsculo.

    A planilha deles é a fonte do vocabulário, como já é feito com as listas
    de seleção da Monitoramento. Serve para o programa não escrever ali um
    e-mail de login nem um nome que ninguém usa."""
    return {_campo(l, "monitorado").lower()
            for l in linhas if _campo(l, "monitorado")}


def ler_id_real():
    from fluxo_downloads import ler_identificador
    return ler_identificador(ARQUIVO_ID_REAL)


def planilha_id():
    """Qual Calendário vale agora: o real ou a cópia de teste.

    Só devolve o real com o modo real autorizado (os três arquivos de sempre)
    E o identificador do Calendário presente. Faltando qualquer um, cai na
    cópia de teste, sem avisar, que é o comportamento seguro e é o mesmo do
    resto do programa."""
    from fluxo_downloads import ler_identificador, modo_real_autorizado
    if modo_real_autorizado():
        real = ler_identificador(ARQUIVO_ID_REAL)
        if real:
            return real
    return ler_identificador(ARQUIVO_ID_TESTE)


def link(data=None):
    """Endereço do Calendário que está valendo, na aba do mês.

    APONTA PARA O QUE ESTÁ VALENDO, e não para a planilha real sempre
    (11/09/2026). Fora do modo autorizado o programa escreve na cópia de
    teste, e um atalho que abrisse a real faria a pessoa conferir a planilha
    errada e concluir que o programa não escreveu nada.

    Sem data, usa o mês de hoje, que é o caso comum: quem clica quer ver o que
    acabou de ser preenchido. None quando não há identificador configurado."""
    from datetime import date as _date
    pid = planilha_id()
    if not pid:
        return None
    endereco = f"https://docs.google.com/spreadsheets/d/{pid}/edit"
    aba = aba_do_mes(data or _date.today())
    try:
        import sheets_client
        gid = sheets_client.id_da_aba(pid, aba)
    except Exception:
        # Aba inexistente ou planilha fora do ar: o endereço sem a aba ainda
        # abre a planilha, que é melhor que não oferecer atalho nenhum.
        gid = None
    return f"{endereco}#gid={gid}" if gid is not None else endereco


def e_a_real():
    """Se o Calendário que está valendo é o REAL do Marketing.

    A tela usa isto para avisar, porque abrir a planilha viva de outra área
    achando que é a cópia de teste é o tipo de engano que custa caro."""
    real = ler_id_real()
    return bool(real) and planilha_id() == real


def ler_aba(aba):
    """As linhas de dados da aba, a partir da PRIMEIRA_LINHA."""
    import sheets_client
    faixa = f"'{aba}'!A{PRIMEIRA_LINHA}:{ULTIMA_COLUNA}3000"
    resposta = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha_id(), range=faixa).execute())
    return resposta.get("values", [])


def _escrever_celulas(planilha, aba, coluna, atualizacoes):
    import sheets_client
    sheets_client.escrever_lote(planilha, aba, coluna, atualizacoes)


def escrever(aba, numero_linha, valores):
    """Preenche as colunas do programa numa linha do Calendário.

    `valores` é um dict com chaves de COL, por exemplo
    {"jogo": "Mines", "status": STATUS_PUBLICADA}.

    NUNCA ESCREVE POR CIMA DE CÉLULA COM CONTEÚDO. A planilha é preenchida à
    mão por outra área, e na coluna Horário existe coisa que o programa não
    entende e não precisa entender ("POSTADO NA LIVE", "-", "16:012", "18:40.",
    todas medidas na planilha real). Destruir isso seria apagar trabalho de
    gente sem ninguém ter pedido.

    Devolve (gravou, motivo). Falha de rede vira (False, motivo), nunca erro
    subindo: escrever no Calendário não pode derrubar o download."""
    try:
        linhas = ler_aba(aba)
    except Exception as e:
        return False, f"Não consegui ler o Calendário: {e}"
    posicao = numero_linha - PRIMEIRA_LINHA
    atual = linhas[posicao] if 0 <= posicao < len(linhas) else []
    gravou = []
    try:
        for nome, valor in valores.items():
            if not str(valor or "").strip():
                continue
            if _campo(atual, nome):
                continue  # já tem gente escrevendo ali
            _escrever_celulas(planilha_id(), aba, letra(nome),
                              [(numero_linha, valor)])
            gravou.append(nome)
    except Exception as e:
        return False, f"Não consegui escrever no Calendário: {e}"
    if not gravou:
        return False, "Nada a escrever: as células já estavam preenchidas."
    return True, ", ".join(gravou)
