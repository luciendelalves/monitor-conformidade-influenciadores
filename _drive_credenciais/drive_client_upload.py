"""
Cliente Google Drive SÓ PRA ESCRITA (upload/criação de pasta), separado do
drive_client.py (que é somente leitura de propósito, usado pelos scripts de
validação). Usa o token com escopo drive.file (drive_file_token.json) — esse
escopo só enxerga arquivos/pastas criados por este próprio app, nunca a
árvore de pastas real do Marketing, o que é uma proteção a mais: não tem
como esse código escrever em cima de nada que já existia antes dele.
"""
import json
import os
import ssl
import sys

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import trava

_TOKEN_PATH = os.path.join(os.path.dirname(__file__), "drive_file_token.json")
_service = None

_PASTA_TESTE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "teste_watch_folder")

# TRAVA CONTRA CORRIDA NA CRIAÇÃO DE PASTA (25/09/2026, achado ao vivo: duas
# pastas "03. LOTTU" na raiz de teste, criadas em dias DIFERENTES, 22 e
# 23/09, cada uma com a árvore inteira embaixo). `obter_ou_criar_pasta`
# procura e só cria se não achar, em dois passos sem proteção nenhuma entre
# eles; duas chamadas quase juntas (duas pessoas, ou duas máquinas, criando
# a mesma pasta pela primeira vez) podem as duas "não achar" e as duas
# criarem. Mesma técnica já usada em fluxo_downloads.py para a Monitoramento
# (trava.travar, arquivo de trava do sistema, funciona entre processos e
# entre máquinas, não só entre threads).
#
# UMA TRAVA SÓ PARA TODAS AS PASTAS, de propósito: criar pasta é raro e
# rápido comparado a subir vídeo, então serializar isso não pesa no tempo
# total, e uma trava por (nome, pasta-mãe) exigiria sanitizar nome de pasta
# para virar nome de arquivo, complexidade que não paga o ganho aqui.
_ARQUIVO_TRAVA_PASTA = os.path.join(_PASTA_TESTE, "obter_ou_criar_pasta")

# CACHE PERSISTENTE, ACRESCENTADO NO MESMO DIA (25/09/2026): a trava sozinha
# não bastou. Achado ao vivo de novo, poucos minutos depois de travar: duas
# pastas "story" criadas com 751 MILISSEGUNDOS de diferença, já dentro da
# trava (uma esperou a outra terminar, de verdade), e mesmo assim a segunda
# não achou a pasta que a primeira tinha acabado de criar. O índice de busca
# do Drive (`files().list`) não é imediatamente consistente com uma criação
# (`files().create`) recém-feita, e isso não é coisa de trava resolver: a
# trava ordena as chamadas, não obriga o Google a já saber da anterior.
#
# A SAÍDA É PARAR DE PERGUNTAR AO DRIVE "ISSO JÁ EXISTE?" SEMPRE. Guarda a
# resposta a primeira vez, num arquivo local, do mesmo jeito que o programa
# já faz para o número de perfil do Instagram (`instagram_userids.json`) e
# para o mapa de pastas do futebol (`pasta_por_handle_futebol.json`): grava
# uma vez, reusa pra sempre, sem precisar da busca de novo. Só cai na busca
# de verdade na PRIMEIRA vez que aquele (nome, pasta-mãe) aparece.
_ARQUIVO_CACHE_PASTAS = os.path.join(_PASTA_TESTE, "pastas_conhecidas.json")


def _ler_cache_pastas():
    if not os.path.exists(_ARQUIVO_CACHE_PASTAS):
        return {}
    try:
        with open(_ARQUIVO_CACHE_PASTAS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def get_service():
    global _service
    if _service is not None:
        return _service
    creds = Credentials.from_authorized_user_file(_TOKEN_PATH)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(_TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    _service = build("drive", "v3", credentials=creds)
    return _service


def _executar(construir_e_chamar):
    """Roda uma chamada à API (recebe uma função sem argumento que chama
    get_service() e executa a requisição) tentando de novo uma vez se a
    conexão cair no meio — acontece quando o app fica um tempo parado e o
    Windows/antivírus/VPN derruba a conexão ociosa antes da chamada seguinte."""
    global _service
    try:
        return construir_e_chamar()
    except (ConnectionError, TimeoutError, ssl.SSLError):
        _service = None  # força reconectar do zero na tentativa seguinte
        return construir_e_chamar()


def _chave_cache(nome_pasta, id_pasta_pai):
    return f"{id_pasta_pai or 'raiz'}::{nome_pasta}"


def pasta_conhecida(nome_pasta, id_pasta_pai=None):
    """Devolve o id já guardado para (pasta-mãe, nome), ou None se este par
    nunca foi resolvido antes. Não fala com o Drive.

    EXPOSTA À PARTE (25/09/2026), para quem já sabe que a pasta existe
    (achou por listagem, em `descer_pelo_caminho`) também poder consultar o
    cache antes de perguntar ao Drive de novo. Antes, só `obter_ou_criar_
    pasta` lia o cache, e só no caminho de CRIAR; o caminho de ACHAR por
    listagem nunca consultava nada, e ficava exposto à mesma inconsistência
    de busca em toda chamada, mesmo depois da pasta já ser conhecida."""
    with trava.travar(_ARQUIVO_TRAVA_PASTA):
        return _ler_cache_pastas().get(_chave_cache(nome_pasta, id_pasta_pai))


def lembrar_pasta(nome_pasta, id_pasta_pai, id_pasta):
    """Grava (pasta-mãe, nome) -> id, para nunca mais precisar perguntar ao
    Drive por esse par. Mesmo arquivo e mesma trava de `obter_ou_criar_
    pasta`, para as duas nunca discordarem sobre o que já é conhecido."""
    with trava.travar(_ARQUIVO_TRAVA_PASTA):
        cache = _ler_cache_pastas()
        cache[_chave_cache(nome_pasta, id_pasta_pai)] = id_pasta
        os.makedirs(_PASTA_TESTE, exist_ok=True)
        with open(_ARQUIVO_CACHE_PASTAS, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def obter_ou_criar_pasta(nome_pasta, id_pasta_pai=None):
    """Procura uma pasta com esse nome (dentre as que este app já criou); se
    não achar, cria. Retorna o ID da pasta.

    SOB TRAVA (25/09/2026): procurar e criar precisam ficar dentro do mesmo
    bloco travado, senão a proteção não vale nada. Travar só a criação
    deixaria as duas chamadas passarem pela busca (sem achar nada, porque
    nenhuma das duas criou ainda) e disputarem a trava só depois, quando o
    estrago de calcular errado já estava feito.

    O CACHE PERSISTENTE VEM ANTES DA BUSCA, e não só antes da criação (achado
    no mesmo dia): a busca ao vivo no Drive é o próprio problema, não só a
    criação. Uma vez conhecida, a pasta nunca mais passa pela busca.

    ISTO SÓ COBRE O CAMINHO DE CRIAR. Quem entra achando a pasta por
    listagem (`descer_pelo_caminho`, quando a pasta já existe) precisa
    gravar sozinho com `lembrar_pasta`, e conferir com `pasta_conhecida`
    antes de listar de novo: achado ao vivo no mesmo dia, com "03. LOTTU"
    JÁ EXISTINDO em duplicidade (duas pastas desse nome, criadas em dias
    diferentes), a busca por listagem podia devolver uma ou outra em ordem
    diferente a cada chamada, mesmo sem nada mudar, e nunca passava por
    aqui para ganhar a proteção do cache."""
    with trava.travar(_ARQUIVO_TRAVA_PASTA):
        cache = _ler_cache_pastas()
        chave = _chave_cache(nome_pasta, id_pasta_pai)
        if chave in cache:
            return cache[chave]

        query = f"name = '{nome_pasta}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if id_pasta_pai:
            query += f" and '{id_pasta_pai}' in parents"
        resp = _executar(lambda: get_service().files().list(q=query, fields="files(id, name)").execute())
        achadas = resp.get("files", [])
        if achadas:
            id_pasta = achadas[0]["id"]
        else:
            metadata = {"name": nome_pasta, "mimeType": "application/vnd.google-apps.folder"}
            if id_pasta_pai:
                metadata["parents"] = [id_pasta_pai]
            pasta = _executar(lambda: get_service().files().create(body=metadata, fields="id").execute())
            id_pasta = pasta["id"]

        cache[chave] = id_pasta
        os.makedirs(_PASTA_TESTE, exist_ok=True)
        with open(_ARQUIVO_CACHE_PASTAS, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
        return id_pasta


def procurar_pasta(nome_pasta, id_pasta_pai=None):
    """Igual a obter_ou_criar_pasta, mas NÃO cria: devolve o ID ou None.
    Serve pra conferir o que já existe sem deixar pasta vazia para trás."""
    query = f"name = '{nome_pasta}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if id_pasta_pai:
        query += f" and '{id_pasta_pai}' in parents"
    resp = _executar(lambda: get_service().files().list(q=query, fields="files(id, name)").execute())
    achadas = resp.get("files", [])
    return achadas[0]["id"] if achadas else None


def listar_arquivos(id_pasta, so_pastas=False):
    """Lista o conteúdo de uma pasta criada por este app.

    Traz também o md5Checksum, que é a impressão digital do conteúdo que o
    próprio Drive calcula ao receber o arquivo. É o que permite reconhecer o
    mesmo vídeo enviado com outro nome."""
    tipo_pasta = "application/vnd.google-apps.folder"
    query = f"'{id_pasta}' in parents and trashed = false"
    query += f" and mimeType {'=' if so_pastas else '!='} '{tipo_pasta}'"
    arquivos, pagina = [], None
    while True:
        resp = _executar(lambda: get_service().files().list(
            q=query, pageSize=1000, pageToken=pagina,
            fields="nextPageToken, files(id, name, md5Checksum, webViewLink)").execute())
        arquivos.extend(resp.get("files", []))
        pagina = resp.get("nextPageToken")
        if not pagina:
            return arquivos


def mandar_para_lixeira(id_item):
    """Manda um arquivo ou pasta para a LIXEIRA do Drive, onde fica 30 dias e
    pode ser restaurado.

    Nunca use files().delete() no lugar disto: ele apaga de forma permanente e
    sem volta. Aconteceu de verdade neste projeto, em 26/08/2026, e dois
    arquivos foram perdidos sem possibilidade de recuperação."""
    return _executar(lambda: get_service().files().update(
        fileId=id_item, body={"trashed": True}, fields="id, name").execute())


def enviar_arquivo(caminho_local, nome_no_drive, id_pasta_destino):
    """Sobe um arquivo local pra uma pasta do Drive (criada por este app) e
    devolve (id_do_arquivo, link_de_visualizacao)."""
    metadata = {"name": nome_no_drive, "parents": [id_pasta_destino]}

    def _chamar():
        media = MediaFileUpload(caminho_local, resumable=False)  # recriado a cada tentativa
        return get_service().files().create(body=metadata, media_body=media, fields="id, webViewLink").execute()

    arquivo = _executar(_chamar)
    return arquivo["id"], arquivo.get("webViewLink")
