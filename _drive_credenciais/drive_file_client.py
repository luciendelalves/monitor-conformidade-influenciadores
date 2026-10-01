"""
Cliente Google Drive com escopo drive.file — só cria/gerencia arquivos que a
própria automação criou, não tem acesso ao resto do Drive do usuário. Usado
pra subir/atualizar arquivos (ex: o manual de parâmetros) direto na pasta de
trabalho da auditoria no Drive, sem precisar de um passo manual de arrastar.
"""

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

_TOKEN_PATH = os.path.join(os.path.dirname(__file__), "drive_file_token.json")

_service = None

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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


def upload_arquivo(caminho_local, nome_no_drive, pasta_id, mime_type=MIME_XLSX):
    """Sobe um arquivo local pra dentro de uma pasta do Drive. Se mime_type for
    um tipo nativo do Google (ex: application/vnd.google-apps.spreadsheet),
    o Drive converte o .xlsx pro formato nativo (Google Sheets) automaticamente.
    Devolve (id, link_web) do arquivo criado."""
    metadata = {"name": nome_no_drive, "parents": [pasta_id]}
    media = MediaFileUpload(
        caminho_local,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=True,
    )
    arquivo = get_service().files().create(
        body={**metadata, "mimeType": mime_type} if mime_type != MIME_XLSX else metadata,
        media_body=media,
        fields="id,webViewLink",
        supportsAllDrives=True,
    ).execute()
    return arquivo["id"], arquivo.get("webViewLink")


def atualizar_arquivo(file_id, caminho_local):
    """Substitui o CONTEÚDO de um arquivo já existente no Drive (mesmo id,
    mesmo link) por uma versão local nova — usado pra manter a cópia do
    manual no Drive sincronizada sem criar um arquivo duplicado a cada
    atualização. Exige que esse arquivo tenha sido criado por essa mesma
    credencial (escopo drive.file só alcança arquivos que ela mesma criou)."""
    media = MediaFileUpload(
        caminho_local,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=True,
    )
    arquivo = get_service().files().update(
        fileId=file_id,
        media_body=media,
        fields="id,webViewLink,modifiedTime",
        supportsAllDrives=True,
    ).execute()
    return arquivo["id"], arquivo.get("webViewLink"), arquivo.get("modifiedTime")
