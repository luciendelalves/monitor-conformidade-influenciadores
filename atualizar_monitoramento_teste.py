# -*- coding: utf-8 -*-
"""
Substitui o conteúdo da Monitoramento de TESTE no Drive pelo modelo vazio
local, mantendo o MESMO endereço da planilha (quem já tem o link continua
valendo).

Uso: py atualizar_monitoramento_teste.py
"""
import io
import os
import sys

from googleapiclient.http import MediaFileUpload

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE, "_drive_credenciais"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import drive_client_upload
import sheets_client

MODELO = os.path.join(BASE, "TESTE - Marketing de Influência (modelo vazio).xlsx")
ARQUIVO_ID = os.path.join(BASE, "teste_watch_folder", "monitoramento_teste_id.txt")


def main():
    with open(ARQUIVO_ID, encoding="utf-8") as f:
        planilha = f.read().strip()

    antes = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().get(
        spreadsheetId=planilha, range="'Monitoramento'!A2:V2000").execute()).get("values", [])
    if antes:
        print(f"ATENÇÃO: a planilha tem {len(antes)} linha(s) de dado, que serão perdidas.")
        if "forcar" not in sys.argv:
            print("Rode de novo com 'forcar' se quiser substituir mesmo assim.")
            return

    svc = drive_client_upload.get_service()
    media = MediaFileUpload(
        MODELO,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=False,
    )
    arquivo = svc.files().update(fileId=planilha, media_body=media,
                                 fields="id, name, webViewLink").execute()
    print(f"Atualizada: {arquivo['name']}")
    print(f"  {arquivo.get('webViewLink')}")

    resp = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().get(
        spreadsheetId=planilha, includeGridData=False).execute())
    print(f"\n  abas: {[s['properties']['title'] for s in resp['sheets']]}")

    vals = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().get(
        spreadsheetId=planilha, range="'Monitoramento'!A1:V3").execute()).get("values", [])
    print(f"  cabeçalho com {len(vals[0]) if vals else 0} colunas")
    print(f"  linhas de dado: {max(0, len(vals) - 1)}")


if __name__ == "__main__":
    main()
