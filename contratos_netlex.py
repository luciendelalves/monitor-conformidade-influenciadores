# -*- coding: utf-8 -*-
"""
O número do contrato no Netlex, por influenciador e por janela de contrato.

POR QUE ESTE ARQUIVO EXISTE (03/09/2026)

Pedido do auditor: "na parte de Cadastro também deve conter o numero do contrato
NETLEX (Caso ele tenha, se não tiver, fica em branco mesmo)".

MEDIDO ANTES DE ESCREVER: a Dados_influ do Marketing tem 20 colunas, e nenhuma
delas é o número do Netlex. As que mais se aproximam são ID_CONTA, que guarda o
identificador da conta na bet ("ID LOTTU: ...", "ID EDS: ..."), e Documentos, que
é link de pasta no Drive.

DE ONDE O NÚMERO VEM, ENTÃO (medido em 03/09/2026, depois de o auditor apontar a
pasta certa no Drive): da própria auditoria. Está na planilha final do papel de
trabalho, aba Achado02_InconformidadeDatas, cabeçalho na linha 4, coluna "Nº
Contrato Netlex". Ali são 996 linhas de pagamento, e nelas:

    147 linhas com número de verdade, de 53 influenciadores, 54 números
    238 linhas com o texto "Não vinculado no Sankhya", que NÃO é número
    611 linhas vazias

O importador (importar_netlex_do_papel.py) traz esses números para cá. O que a
planilha do papel de trabalho NÃO tem é a janela do contrato: as datas dela são
de pagamento, não de vigência. Por isso o número importado entra com janela
VAZIA, e a origem fica registrada. Ele vale para o influenciador, não para uma
janela específica, e a tela diz isso.

Como a regra do projeto é que a Monitoramento real nunca recebe escrita, ele
mora aqui, num registro NOSSO. É o que a tela de Cadastro já anunciava desde
31/08/2026: "quando existir, vai ficar numa planilha da Auditoria, como campo
opcional, sem alterar a planilha deles".

A CHAVE INCLUI A JANELA DO CONTRATO, E ISSO É O PONTO PRINCIPAL DESTE ARQUIVO.

O auditor registrou duas coisas sobre contrato de influenciador, e as duas
quebram a chave óbvia (só o @):

    nem todo influenciador tem contrato, então o campo é opcional de verdade
    RENOVAÇÃO NÃO ENCERRA O ANTERIOR: o mesmo @ pode ter mais de um contrato

Se a chave fosse só o @, a renovação sobrescreveria o número do contrato antigo,
e o papel de trabalho perderia qual contrato valia quando a peça foi publicada.
Com a janela na chave, cada contrato guarda o seu número, e a renovação é um
registro NOVO em vez de uma sobrescrita.

E TEM UM EFEITO QUE VALE DIZER: o Marketing sobrescreve INÍCIO_CONTRATO e
FIM_CONTRATO na linha do influenciador quando renova, então a janela antiga
desaparece da planilha deles. Aqui ela não desaparece. O número antigo continua
guardado contra a janela em que foi assinado, mesmo depois de a planilha do
Marketing só mostrar a janela nova.

O QUE ESTE ARQUIVO NÃO FAZ: ele não confere se o número existe no Netlex, não
diz se o contrato está válido e não afirma que quem está sem número está
irregular. Em branco quer dizer "não informado aqui", e nada além disso. A
auditoria já mediu que o vínculo do contrato é pouco preenchido nos sistemas, e
essa é justamente a razão de o campo ser opcional.

PENDÊNCIA ESCRITA AQUI PARA NÃO PASSAR POR DECISÃO TOMADA: o registro é um
arquivo local, do mesmo jeito que o fechamento de ciclo. O certo é virar uma aba
numa planilha da Auditoria, para não depender desta máquina. Enquanto não virar,
o arquivo é o registro.
"""
import csv
import os
from datetime import date, datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(BASE, "teste_watch_folder", "netlex_contratos.csv")

CAMPOS = ("handle", "inicio", "fim", "numero_netlex", "origem", "observacao",
          "quem", "quando")

# De onde o registro veio. Importa para a tela poder dizer que um número não é
# de uma janela específica, e para ninguém confundir o que foi digitado por
# alguém com o que foi trazido de outra planilha.
ORIGEM_TELA = "informado na tela"
ORIGEM_PAPEL_DE_TRABALHO = "papel de trabalho, Achado02"


def normalizar_handle(valor):
    """O @ sem arroba, sem espaço e em minúscula, para a chave não depender de
    como a pessoa digitou."""
    texto = str(valor or "").strip().lstrip("@").strip()
    return texto.lower()


def normalizar_data(texto):
    """Data em AAAA-MM-DD, ou vazio quando não dá para ler.

    As formas vêm de planilha de Marketing, e o serial do Sheets aparece de
    verdade nos dados. Normalizar aqui é o que evita a mesma janela virar duas
    chaves diferentes só porque numa linha veio 03/10/2025 e noutra veio 45933."""
    t = str(texto or "").strip()
    if not t:
        return ""
    t = t.split()[0]
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(t, formato).date().isoformat()
        except ValueError:
            continue
    if t.isdigit() and len(t) == 5:
        try:
            return (date(1899, 12, 30) + timedelta(days=int(t))).isoformat()
        except (ValueError, OverflowError):
            return ""
    # NÃO CHUTA. Data ilegível vira janela vazia, e o registro fica no @ sem
    # janela, que é honesto. Inventar uma data aqui criaria chave que não
    # corresponde a contrato nenhum.
    return ""


def chave(handle, inicio, fim):
    """Identidade de um contrato: quem, e de quando até quando."""
    return (normalizar_handle(handle), normalizar_data(inicio),
            normalizar_data(fim))


def ler():
    """Todos os registros, na ordem em que foram gravados. Lista vazia se ainda
    não existe arquivo, que é o estado normal antes do primeiro uso."""
    if not os.path.exists(ARQUIVO):
        return []
    with open(ARQUIVO, encoding="utf-8", newline="") as f:
        return [dict(linha) for linha in csv.DictReader(f)]


def por_chave():
    """Mapa chave -> registro, com o ÚLTIMO gravado vencendo.

    O último vence de propósito: corrigir um número digitado errado é gravar de
    novo, e não editar o arquivo à mão. O histórico continua no arquivo, porque
    a gravação é sempre acréscimo."""
    saida = {}
    for registro in ler():
        saida[chave(registro.get("handle"), registro.get("inicio"),
                    registro.get("fim"))] = registro
    return saida


def numero_de(handle, inicio, fim, registros=None):
    """O número do contrato daquela janela, ou vazio.

    VAZIO NÃO É ERRO: quer dizer que ninguém informou o número para esta janela.
    Quem chama não deve transformar isso em alerta."""
    mapa = registros if registros is not None else por_chave()
    achado = mapa.get(chave(handle, inicio, fim))
    return str(achado.get("numero_netlex") or "").strip() if achado else ""


def gravar(handle, inicio, fim, numero_netlex, quem, observacao="",
           origem=ORIGEM_TELA):
    """Acrescenta um registro. Devolve o registro gravado.

    SEMPRE ACRESCENTA, nunca reescreve linha: assim fica a trilha de quem
    informou o quê e quando, que é o que um papel de trabalho precisa. Quem lê
    resolve pelo último, em por_chave."""
    handle_limpo = normalizar_handle(handle)
    if not handle_limpo:
        raise ValueError("sem @ do influenciador não há o que registrar")
    registro = {
        "handle": handle_limpo,
        "inicio": normalizar_data(inicio),
        "fim": normalizar_data(fim),
        "numero_netlex": str(numero_netlex or "").strip(),
        "origem": str(origem or "").strip(),
        "observacao": str(observacao or "").strip(),
        "quem": str(quem or "").strip(),
        "quando": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    novo = not os.path.exists(ARQUIVO)
    os.makedirs(os.path.dirname(ARQUIVO), exist_ok=True)
    if not novo:
        _alinhar_titulos()
    with open(ARQUIVO, "a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            escritor.writeheader()
        escritor.writerow(registro)
    return registro


def _alinhar_titulos():
    """Reescreve o arquivo se a lista de campos cresceu desde a última gravação.

    Sem isto, o acréscimo escreveria os valores novos sob os títulos antigos e o
    registro passaria a mentir em silêncio. Aconteceu de verdade no registro de
    fechamento de ciclo, e a coluna `origem` entrou aqui pelo mesmo caminho."""
    with open(ARQUIVO, encoding="utf-8", newline="") as f:
        antigos = list(csv.DictReader(f))
        titulos = tuple(antigos[0].keys()) if antigos else ()
    if not titulos or titulos == CAMPOS:
        return
    with open(ARQUIVO, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        for antigo in antigos:
            escritor.writerow({c: antigo.get(c, "") or "" for c in CAMPOS})


def numeros_do_influenciador(handle, registros=None):
    """Todos os números já registrados para um @, sem olhar a janela.

    POR QUE ISTO EXISTE: o número importado do papel de trabalho não tem janela,
    porque a planilha de lá guarda datas de PAGAMENTO e não de vigência. Então
    quando a janela da linha do Marketing não casa com registro nenhum, a tela
    cai aqui.

    DEVOLVE LISTA, e não um número, de propósito. Medido em 03/09/2026: três
    influenciadores têm DOIS contratos no papel de trabalho (@clararodriiguess
    1137 e 2163, @ruivinhademarte 1029 e 2074, @nathanqueiroz 1290 e 12902).
    Escolher um deles aqui seria o programa decidindo qual contrato vale, que é
    leitura de contrato e não de programa."""
    alvo = normalizar_handle(handle)
    fonte = registros if registros is not None else ler()
    numeros = []
    for registro in fonte:
        if normalizar_handle(registro.get("handle")) != alvo:
            continue
        numero = str(registro.get("numero_netlex") or "").strip()
        if numero and numero not in numeros:
            numeros.append(numero)
    return sorted(numeros)


def historico_de(handle):
    """Todos os contratos já registrados para um @, do mais recente para o mais
    antigo. É por aqui que a renovação aparece: dois contratos, duas janelas,
    dois números, sem um apagar o outro."""
    alvo = normalizar_handle(handle)
    do_influenciador = [r for r in ler()
                        if normalizar_handle(r.get("handle")) == alvo]
    return sorted(do_influenciador,
                  key=lambda r: (r.get("inicio") or "", r.get("quando") or ""),
                  reverse=True)
