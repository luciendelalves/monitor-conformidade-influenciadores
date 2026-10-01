"""
Cliente Google Drive (somente leitura) para os scripts de auditoria em producao/analises/.

Usa o token gerado por autorizar_drive.py (escopo drive.readonly, mesma conta
auditor@empresa.com). As pastas de vídeos de influenciadores vivem num
Drive Compartilhado da EGB — por isso toda chamada aqui usa supportsAllDrives /
includeItemsFromAllDrives; sem isso a API responde 404 mesmo com permissão real.
"""

import os
import ssl
import time

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

_TOKEN_PATH = os.path.join(os.path.dirname(__file__), "drive_token.json")

_service = None


def _com_retentativas(fn, tentativas=3, espera_s=3):
    """Repete uma chamada de rede até `tentativas` vezes antes de desistir.
    Achado real de auditoria: oscilações transitórias de rede (SSL: RECORD_
    LAYER_FAILURE) aconteciam ocasionalmente durante download/listagem no
    Drive — sem retentativa, isso derrubava a tela inteira do app (o
    carregamento da planilha roda toda vez que a tela recarrega, fora do
    try/except que já protegia o processamento de cada linha)."""
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            return fn()
        except (ssl.SSLError, ConnectionError, TimeoutError, OSError) as e:
            ultimo_erro = e
            if tentativa < tentativas:
                time.sleep(espera_s)
    raise ultimo_erro


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


def get_metadata(file_id):
    return _com_retentativas(lambda: get_service().files().get(
        fileId=file_id,
        fields="id,name,mimeType,size,driveId",
        supportsAllDrives=True,
    ).execute())


PASTA_MIME_TYPE = "application/vnd.google-apps.folder"

# Subpastas com esses termos no nome são material não editado/publicado (ex:
# "vídeo bruto") — não faz sentido checar aviso regulatório em algo que ainda
# nem foi ao ar, então ficam de fora da checagem normal.
#
# "bruta" ENTROU EM 01/09/2026, E ISSO CORRIGE UM DEFEITO. A comparação é por
# pedaço do nome, então "bruto" já pegava "brutos", "vídeo bruto" e "VÍDEO
# BRUTO". Só que a varredura do Drive dos influenciadores ATIVOS encontrou 25
# pastas chamadas "brutas", no feminino, e "brutas" não contém "bruto". Essas 25
# estavam entrando na análise como se fossem peça publicada.
NOMES_SUBPASTA_IGNORADA = ("bruto", "bruta", "raw")


def list_folder(folder_id, _profundidade=0):
    """Lista os arquivos dentro de uma pasta do Drive, descendo em subpastas
    (até 3 níveis). O Marketing às vezes organiza os clipes de um post dentro
    de uma subpasta (ex: pasta do post > "stories/" > vídeos) — listar só o
    primeiro nível fazia posts com conteúdo real parecerem vazios (achado real
    de auditoria: pasta com vídeo dentro classificada como PASTA VAZIA).
    Subpastas de material bruto/não editado (ver NOMES_SUBPASTA_IGNORADA) são
    puladas de propósito."""
    files = []
    page_token = None
    while True:
        resp = _com_retentativas(lambda: get_service().files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id,name,mimeType,size)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageToken=page_token,
        ).execute())
        for item in resp.get("files", []):
            if item.get("mimeType") == PASTA_MIME_TYPE:
                nome_pasta = (item.get("name") or "").lower()
                ignorar = any(termo in nome_pasta for termo in NOMES_SUBPASTA_IGNORADA)
                if _profundidade < 3 and not ignorar:
                    files.extend(list_folder(item["id"], _profundidade=_profundidade + 1))
            else:
                files.append(item)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def _baixar_com_downloader(request, dest_path):
    """Baixa reiniciando do zero em cada tentativa — uma falha de rede no meio
    de um chunk deixa o arquivo parcial, então cada retentativa reabre o
    arquivo (trunca) e reinicia o download completo, não tenta retomar."""
    def _tentativa():
        with open(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return dest_path

    return _com_retentativas(_tentativa)


def download_file(file_id, dest_path):
    """Baixa um arquivo do Drive para dest_path."""
    request = get_service().files().get_media(fileId=file_id, supportsAllDrives=True)
    return _baixar_com_downloader(request, dest_path)


def export_file(file_id, mime_type, dest_path):
    """Exporta um arquivo nativo do Google Workspace (Sheets/Docs/Slides) para um
    formato comum (ex: xlsx). Usa o endpoint files.export do Drive API — não
    precisa do escopo do Sheets, drive.readonly já é suficiente."""
    request = get_service().files().export_media(fileId=file_id, mimeType=mime_type)
    return _baixar_com_downloader(request, dest_path)
