# -*- coding: utf-8 -*-
"""
Aplica na Monitoramento de TESTE o mesmo cabeçalho da planilha oficial do
Marketing: cores, fonte, tamanho e negrito, coluna por coluna.

Os valores abaixo foram lidos da planilha oficial em 27/08/2026, em uma
leitura que não escreveu nada lá. São duas famílias de cor: verde-escuro
#356854 nas colunas do dia a dia, e vermelho-escuro #980000 no bloco de
cadastro do influenciador (ID DA CONTA até ESCOPO), que usa outra fonte.

O que este script NÃO consegue reproduzir: as pílulas coloridas dos menus
suspensos (SIM verde, LOTTU laranja, EDS azul, Pendente vermelho). Elas são
um recurso próprio do Google Sheets cuja configuração de cor não é exposta
pela API, então nem a leitura da oficial traz esses tons.

Uso: py aplicar_cores_monitoramento_teste.py
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import fluxo_downloads as fluxo
import sheets_client

VERDE, VERMELHO, BRANCO = "#356854", "#980000", "#FFFFFF"

# (primeira coluna, última coluna, fundo, fonte, tamanho, negrito)
FAIXAS = [
    (2, 2, VERDE, "Roboto", 10, False),
    (3, 5, VERMELHO, "Fjalla One", 11, True),
    (6, 10, VERMELHO, "Fjalla One", 11, False),
    (11, 21, VERDE, "Roboto", 10, False),
    (22, 22, VERDE, "Roboto", 10, True),
]


def cor(hexa):
    hexa = hexa.lstrip("#")
    return {"red": int(hexa[0:2], 16) / 255,
            "green": int(hexa[2:4], 16) / 255,
            "blue": int(hexa[4:6], 16) / 255}


def main():
    sid = fluxo._planilha_monitoramento_id()
    if not sid:
        raise SystemExit("A Monitoramento de teste não está configurada.")
    svc = sheets_client.get_service()

    meta = svc.spreadsheets().get(spreadsheetId=sid, includeGridData=False).execute()
    aba = next(s["properties"] for s in meta["sheets"]
               if s["properties"]["title"] == "Monitoramento")
    sheet_id = aba["sheetId"]

    pedidos = []
    for primeira, ultima, fundo, familia, tamanho, negrito in FAIXAS:
        pedidos.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": primeira - 1, "endColumnIndex": ultima},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": cor(fundo),
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                    "textFormat": {"foregroundColor": cor(BRANCO), "fontFamily": familia,
                                   "fontSize": tamanho, "bold": negrito},
                }},
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,"
                          "verticalAlignment,textFormat)",
            }
        })

    svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": pedidos}).execute()
    print(f"cabeçalho formatado em {len(FAIXAS)} faixas de coluna")

    # confere relendo
    d = svc.spreadsheets().get(spreadsheetId=sid, ranges=["Monitoramento!A1:V1"],
                               includeGridData=True).execute()
    linha = d["sheets"][0]["data"][0]["rowData"][0].get("values", [])
    print("\nconferência (lido de volta da planilha de teste):")
    for i, cel in enumerate(linha, start=1):
        fmt = cel.get("effectiveFormat", {})
        b = fmt.get("backgroundColor", {})
        rgb = "#%02X%02X%02X" % (round(b.get("red", 0) * 255), round(b.get("green", 0) * 255),
                                 round(b.get("blue", 0) * 255))
        tf = fmt.get("textFormat", {})
        if cel.get("formattedValue"):
            print(f"   col {i:>2} {cel['formattedValue'][:20]:22} fundo={rgb} "
                  f"fonte={tf.get('fontFamily')} tam={tf.get('fontSize')}")


if __name__ == "__main__":
    main()
