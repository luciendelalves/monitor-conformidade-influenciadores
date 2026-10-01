# -*- coding: utf-8 -*-
"""
Protótipo (fase 2 do watch-folder): em vez de detectar arquivo já baixado,
lê uma planilha "Fila de Downloads" (Influenciador + Link) onde o analista
de Marketing cola o link do vídeo, baixa o vídeo (yt-dlp) e sobe pra uma
pasta organizada por influenciador no Drive (pasta de TESTE nesta fase,
igual ao protótipo anterior — nunca mexe em pasta real do Marketing nem na
planilha Monitoramento).

Uso:
    py prototipo_fila_downloads.py            (roda de verdade nesta planilha de TESTE)

A planilha de teste é criada por criar_planilha_fila_downloads.py; o ID fica
salvo em teste_watch_folder/fila_downloads_id.txt.
"""
import os
import sys
import tempfile

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_drive_credenciais"))
import sheets_client
import drive_client_upload

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_ID = os.path.join(PASTA_BASE, "teste_watch_folder", "fila_downloads_id.txt")
ABA = "Fila"
NOME_PASTA_TESTE_RAIZ = "TESTE - Watch Folder - Não Usar"


def carregar_planilha_id():
    with open(ARQUIVO_ID, "r", encoding="utf-8") as f:
        return f.read().strip()


def baixar_video(link, pasta_destino):
    """Baixa o vídeo do link com yt-dlp. Devolve o caminho do arquivo baixado
    ou levanta exceção com o motivo (ex: precisa de login)."""
    import yt_dlp

    opcoes = {
        "outtmpl": os.path.join(pasta_destino, "%(id)s.%(ext)s"),
        "format": "worst",  # teste: qualidade mais baixa, mais rápido
        "quiet": True,
        "no_warnings": True,
        # YouTube vem bloqueando (403) o client "web" padrão em vários formatos;
        # o client "android" contorna isso na maioria dos casos (achado de hoje).
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    }
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        info = ydl.extract_info(link, download=True)
        return ydl.prepare_filename(info)


def main():
    spreadsheet_id = carregar_planilha_id()
    svc = sheets_client.get_service()
    resp = svc.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"{ABA}!A2:D1000").execute()
    linhas = resp.get("values", [])

    if not linhas:
        print("Nenhuma linha na fila.")
        return

    id_pasta_raiz = drive_client_upload.obter_ou_criar_pasta(NOME_PASTA_TESTE_RAIZ)

    for i, linha in enumerate(linhas):
        numero_linha = i + 2  # A2 é a linha 2
        influenciador = linha[0] if len(linha) > 0 else ""
        link = linha[1] if len(linha) > 1 else ""
        status = linha[2] if len(linha) > 2 else ""

        if not link or status:
            continue  # já processado, ou sem link

        print(f"Linha {numero_linha}: {influenciador} | {link}")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                caminho_video = baixar_video(link, tmp)
                print(f"  Baixado: {os.path.basename(caminho_video)} ({os.path.getsize(caminho_video)} bytes)")

                id_pasta_influenciador = drive_client_upload.obter_ou_criar_pasta(influenciador or "SEM_INFLUENCIADOR", id_pasta_raiz)
                nome_no_drive = f"{influenciador}_{os.path.basename(caminho_video)}"
                _id_arquivo, link_drive = drive_client_upload.enviar_arquivo(caminho_video, nome_no_drive, id_pasta_influenciador)
                print(f"  Subiu pro Drive: {link_drive}")

            sheets_client.escrever_lote(spreadsheet_id, ABA, "C", [(numero_linha, "BAIXADO E ORGANIZADO")])
            sheets_client.escrever_lote(spreadsheet_id, ABA, "D", [(numero_linha, link_drive)])
        except Exception as e:
            msg = str(e)[:200]
            print(f"  FALHA: {msg}")
            sheets_client.escrever_lote(spreadsheet_id, ABA, "C", [(numero_linha, f"FALHA: {msg}")])


if __name__ == "__main__":
    main()
