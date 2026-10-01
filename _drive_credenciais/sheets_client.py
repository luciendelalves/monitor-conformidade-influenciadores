"""
Cliente Google Sheets (leitura E escrita) — usado só pra devolver a sugestão de
classificação na planilha "AUDITORIA - VALIDAÇÃO MKT INFLU", que é cópia de
trabalho da própria Auditoria. Token separado do drive_token.json (que só lê
vídeos) por menor privilégio: cada credencial tem só o escopo que precisa.
"""

import os
import ssl
import threading
import time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

_TOKEN_PATH = os.path.join(os.path.dirname(__file__), "sheets_write_token.json")

_service = None

# UMA CHAMADA POR VEZ, E ISSO NÃO É ZELO EXCESSIVO: SEM ISTO O PROCESSO MORRE
# (08/09/2026).
#
# O QUE ACONTECEU. O trabalhador morreu com "Segmentation fault", exit 139, sem
# traceback nenhum, no meio de um download. Erro de Python teria traceback e a
# tarefa marcada como falha; ali não houve nem um nem outro, e é assim que
# defeito em biblioteca nativa aparece.
#
# A CAUSA. Este módulo guarda UM service em `_service` e entrega o mesmo objeto
# a qualquer thread que peça. O cliente do Google carrega um http por dentro que
# NÃO é seguro para uso simultâneo. Pior: `executar()` ZERA esse global quando
# há erro de rede, o que uma thread pode fazer no exato momento em que a outra
# está usando o objeto.
#
# QUEM USA ISTO DE DUAS THREADS, no processo do trabalhador:
#
#   thread principal    escreve o veredito quando uma análise termina
#                       (concluir_analise, em trabalhador.py)
#   linha de download   escreve a linha da Monitoramento e o status da fila
#                       (processar_fila, em fluxo_downloads.py)
#
# Essa dupla existe desde que o trabalhador passou a ter linha de download
# própria, e é anterior a qualquer mudança recente. A varredura de fila só
# tornou o encontro mais frequente, e foi assim que apareceu.
#
# As análises NÃO entram na conta: rodam em ProcessPoolExecutor, e cada processo
# tem o service próprio.
#
# POR QUE AQUI, E NÃO NO TRABALHADOR. Dá para pedir a cada quem chama que não
# fale com a planilha na hora errada, e foi a primeira tentativa. Mas isso é
# combinado que se perde: o próximo ponto de chamada não vai saber. A trava fica
# na camada mais baixa, pelo mesmo raciocínio que pôs aqui a trava contra
# injeção de fórmula.
#
# REENTRANTE de propósito: há chamada de dentro de chamada na mesma thread
# (`escrever_lote` chama `executar` mais de uma vez, e há `executar` dentro de
# função passada para `executar`). Com trava simples, a thread esperaria por si
# mesma e o programa congelaria para sempre, sem aparecer em log nenhum.
#
# O CUSTO ACEITO: as chamadas à planilha deixam de acontecer em paralelo. Não
# pesa neste programa, que já espera de 30 a 180 segundos entre links do
# Instagram de propósito. Congelar seria pior, e cair é o que já aconteceu.
_TRAVA_DA_API = threading.RLock()

# TRAVA CONTRA INJEÇÃO DE FÓRMULA (04/09/2026, achado do parecer de
# cibersegurança que revisou o projeto seis dias depois do parecer sobre o
# SAST). Toda escrita deste arquivo usa valueInputOption="USER_ENTERED", que é
# o modo do Sheets que INTERPRETA texto começando com "=", "+", "-" ou "@" como
# fórmula. Hoje nenhuma tela do projeto oferece campo de texto livre nesse
# caminho de escrita (a única edição em lote existente usa um dropdown de
# opções fixas), então não há exploração possível agora. Mas a trava fica na
# camada mais baixa e compartilhada, para proteger de saída qualquer tela
# futura que reuse escrever_lote ou adicionar_linhas com texto livre.
#
# A PRÓPRIA CONVENÇÃO DO PROJETO GRAVA @HANDLE COM O @ NA FRENTE, então a
# neutralização não pode ser "não gravar valor que comece com @": teria que
# corromper toda linha de influenciador. A saída padrão para isso (a mesma que
# o Excel e o Sheets usam quando alguém digita manualmente) é um apóstrofo na
# frente: ele força o Sheets a tratar como texto, e o apóstrofo em si NÃO
# aparece na célula, então "@fulano" continua aparecendo como "@fulano".
_CARACTERES_DE_FORMULA = ("=", "+", "-", "@")


def _neutralizar_formula(valor):
    """Prefixa com apóstrofo se o texto começaria uma fórmula no Sheets.

    Só mexe em string cujo primeiro caractere é um dos quatro perigosos.
    Número, data e qualquer outro tipo passam direto, sem conversão: essa
    função não serve para formatar, só para não deixar o Sheets interpretar
    texto como fórmula."""
    if isinstance(valor, str) and valor.startswith(_CARACTERES_DE_FORMULA):
        return "'" + valor
    return valor


def get_service():
    global _service
    # Sob a trava também: sem ela, duas threads veem `_service` vazio ao mesmo
    # tempo, as duas constroem o cliente, e uma pode estar reescrevendo o
    # arquivo do token enquanto a outra o lê.
    with _TRAVA_DA_API:
        if _service is not None:
            return _service

        creds = Credentials.from_authorized_user_file(_TOKEN_PATH)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(_TOKEN_PATH, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

        _service = build("sheets", "v4", credentials=creds)
        return _service


# Códigos em que vale tentar de novo: o Google pede para repetir depois de um
# intervalo. Erros 4xx (a não ser o 429) são problema do pedido em si, repetir
# só produz o mesmo erro.
_STATUS_QUE_VALE_REPETIR = (429, 500, 502, 503, 504)


def executar(construir_e_chamar, tentativas=3, espera_s=3, repetivel=True):
    """Roda uma chamada à API (recebe uma função sem argumento que chama
    get_service() e executa a requisição), repetindo quando a falha é de rede
    ou temporária do lado do Google.

    Antes repetia UMA vez e na hora, sem esperar. Em 28/08/2026 uma oscilação
    de rede derrubou o carregamento da planilha com "The read operation timed
    out": a segunda tentativa saiu imediatamente e caiu junto com a primeira.
    Agora espera entre as tentativas, igual ao cliente do Drive, que já era
    assim e não apresentava esse problema.

    `repetivel=False` para chamadas que NÃO podem ser repetidas com segurança.
    O caso é o append de linhas novas: se o pedido chegou ao Google e só a
    resposta se perdeu, repetir insere as mesmas linhas duas vezes. Numa
    planilha de auditoria, linha duplicada é pior que erro na tela, então
    nesse caso a falha aparece e a pessoa refaz sabendo o que aconteceu."""
    global _service
    ultimo_erro = None
    # A TRAVA PEGA O CICLO INTEIRO, inclusive a espera entre tentativas. Soltar
    # no meio deixaria a outra thread entrar justamente quando `_service` acabou
    # de ser zerado, que é o pior momento possível. Segurar por alguns segundos
    # não pesa aqui, e o motivo completo está no comentário de _TRAVA_DA_API.
    with _TRAVA_DA_API:
        for tentativa in range(1, tentativas + 1):
            try:
                return construir_e_chamar()
            except (ssl.SSLError, ConnectionError, TimeoutError, OSError) as e:
                ultimo_erro = e
                _service = None  # força reconectar do zero na tentativa seguinte
            except HttpError as e:
                status = getattr(getattr(e, "resp", None), "status", None)
                if status not in _STATUS_QUE_VALE_REPETIR:
                    raise
                ultimo_erro = e
            if not repetivel or tentativa == tentativas:
                break
            time.sleep(espera_s)
        raise ultimo_erro


def ler_coluna(spreadsheet_id, aba, coluna, linhas):
    """Lê o valor atual de uma coluna pra uma lista de números de linha.
    Devolve dict {linha: valor_ou_None}. Uma chamada só, mesmo pra muitas linhas."""
    if not linhas:
        return {}
    minimo, maximo = min(linhas), max(linhas)
    resp = executar(lambda: get_service().spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{aba}'!{coluna}{minimo}:{coluna}{maximo}",
    ).execute())
    valores = resp.get("values", [])
    resultado = {}
    for linha in linhas:
        idx = linha - minimo
        v = valores[idx][0] if idx < len(valores) and valores[idx] else None
        resultado[linha] = v
    return resultado


def escrever_lote(spreadsheet_id, aba, coluna, atualizacoes):
    """atualizacoes: lista de (linha, valor). Escreve tudo numa chamada batch."""
    if not atualizacoes:
        return
    data = [
        {"range": f"'{aba}'!{coluna}{linha}",
         "values": [[_neutralizar_formula(valor)]]}
        for linha, valor in atualizacoes
    ]
    executar(lambda: get_service().spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": data},
    ).execute())


def id_da_aba(spreadsheet_id, aba):
    """Número interno da aba, que algumas operações exigem em vez do nome."""
    meta = executar(lambda: get_service().spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets(properties(sheetId,title))").execute())
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == aba:
            return s["properties"]["sheetId"]
    return None


def apagar_linhas(spreadsheet_id, aba, linhas):
    """Apaga linhas inteiras, de verdade, puxando as de baixo para cima.

    Apaga de baixo para cima de propósito: apagar a linha 10 muda o número de
    todas as linhas abaixo dela, então fazer na ordem crescente erraria o alvo
    a partir da segunda. Devolve quantas foram apagadas.

    repetivel=False nas chamadas: apagar linha não é idempotente. Se o pedido
    chegou ao Google e só a resposta se perdeu, repetir apagaria OUTRAS linhas,
    as que subiram de posição."""
    if not linhas:
        return 0
    numero_aba = id_da_aba(spreadsheet_id, aba)
    if numero_aba is None:
        return 0
    pedidos = [
        {"deleteDimension": {"range": {
            "sheetId": numero_aba, "dimension": "ROWS",
            "startIndex": n - 1, "endIndex": n,
        }}}
        for n in sorted(set(linhas), reverse=True)
    ]
    executar(lambda: get_service().spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": pedidos}).execute(),
        repetivel=False)
    return len(pedidos)


def adicionar_linhas(spreadsheet_id, aba, colunas, linhas):
    """Acrescenta linhas novas logo após a última linha com dado no intervalo de
    colunas indicado (ex: "A:E"). Usa values().append() em vez de calcular o
    número da próxima linha na mão — a API descobre sozinha onde termina o
    dado existente, evitando gravar por cima de algo se uma linha for
    adicionada por outra pessoa entre a leitura e a escrita."""
    if not linhas:
        return
    linhas_seguras = [[_neutralizar_formula(v) for v in linha] for linha in linhas]
    # repetivel=False de propósito: append insere linha nova, e repetir uma
    # chamada que talvez tenha dado certo duplicaria os dados (ver executar).
    executar(lambda: get_service().spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{aba}'!{colunas}",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": linhas_seguras},
    ).execute(), repetivel=False)
