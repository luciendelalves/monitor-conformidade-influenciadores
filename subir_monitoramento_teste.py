# -*- coding: utf-8 -*-
"""
Sobe o modelo vazio da Monitoramento pro Drive como planilha do Google, pra
servir de alvo de teste da automação. O ID fica salvo em
teste_watch_folder/monitoramento_teste_id.txt, do mesmo jeito que o ID da fila.

É criada pelo token de escopo drive.file, então o programa só enxerga o que
ele mesmo criou: não tem como escrever por engano na planilha real do
Marketing.

Uso:
    py subir_monitoramento_teste.py
"""
import io
import os
import sys

from googleapiclient.http import MediaFileUpload

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE, "_drive_credenciais"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import drive_client_upload

MODELO = os.path.join(BASE, "TESTE - Marketing de Influência (modelo vazio).xlsx")
ARQUIVO_ID = os.path.join(BASE, "teste_watch_folder", "monitoramento_teste_id.txt")
NOME_NO_DRIVE = "TESTE - Marketing de Influência - Não Usar"


def main():
    if not os.path.exists(MODELO):
        raise SystemExit(f"Não achei o modelo: {MODELO}\nRode antes o criar_modelo_vazio_marketing.py")

    if os.path.exists(ARQUIVO_ID):
        with open(ARQUIVO_ID, encoding="utf-8") as f:
            ja = f.read().strip()
        if ja:
            print(f"Já existe uma planilha de teste criada: {ja}")
            print(f"https://docs.google.com/spreadsheets/d/{ja}")
            print("\nApague o arquivo de ID se quiser criar outra do zero:")
            print(f"  {ARQUIVO_ID}")
            return

    svc = drive_client_upload.get_service()
    metadata = {"name": NOME_NO_DRIVE, "mimeType": "application/vnd.google-apps.spreadsheet"}
    media = MediaFileUpload(
        MODELO,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=False,
    )
    arquivo = svc.files().create(body=metadata, media_body=media,
                                 fields="id, name, webViewLink").execute()

    os.makedirs(os.path.dirname(ARQUIVO_ID), exist_ok=True)
    with open(ARQUIVO_ID, "w", encoding="utf-8") as f:
        f.write(arquivo["id"])

    print(f"Criada: {arquivo['name']}")
    print(f"  ID  : {arquivo['id']}")
    print(f"  Link: {arquivo.get('webViewLink')}")
    print(f"  ID salvo em: {ARQUIVO_ID}")

    # confere que as abas e cabecalhos sobreviveram a conversao
    import sheets_client
    resp = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().get(
        spreadsheetId=arquivo["id"]).execute())
    abas = [s["properties"]["title"] for s in resp["sheets"]]
    print(f"\n  abas na planilha criada: {abas}")

    for aba, esperado in (("Monitoramento", "@doinflu"), ("Dados_influ", "INFLU")):
        vals = sheets_client.executar(
            lambda a=aba: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=arquivo["id"], range=f"'{a}'!A1:V1").execute())
        cab = vals.get("values", [[]])[0]
        ok = esperado in cab
        print(f"  {aba:16} cabeçalho com {len(cab)} colunas | contém {esperado!r}: {ok}")


if __name__ == "__main__":
    main()
