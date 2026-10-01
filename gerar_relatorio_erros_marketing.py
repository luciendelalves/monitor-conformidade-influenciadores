"""
Gera um Excel só com os casos de erro humano CONFIRMADOS no preenchimento das
pastas/links pelo Marketing: linhas onde o link do Drive aponta pra conteúdo
de um influenciador DIFERENTE do que está anotado na planilha, com prova
(nome dos arquivos reais dentro da pasta bate com o @ de outra pessoa).

Só entram aqui casos com link ainda acessível e conteúdo claramente
identificável — não entram os ambíguos, os de link quebrado (404) nem os
falso-positivo (placeholder "aguardado"/"AGUARDANDO VIDEO NO DRIVE").

Rodar: py gerar_relatorio_erros_marketing.py
"""

import os
import re

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.hyperlink import Hyperlink

import pipeline_influenciadores as pipeline

DESTINO = os.path.join(pipeline.BASE_DIR, "Erros_Preenchimento_Marketing.xlsx")

# (linha com o link errado, influenciador anotado errado, dono real do conteúdo, linha do dono real)
CASOS_CONFIRMADOS = [
    (127, "@joaovictorr10", "@feijhonys", 109),
    (804, "@lucasguimaraes", "@eudisbocuda", 758),
    (873, "@reservapretarara", "@noronhavivii", 941),
    (907, "@adrianamunizofc", "@cassinha.161", 897),
    (954, "@brunobubuof", "@apoline", 967),
    (1416, "@eudisbocuda", "@marcelinho_jhonson", 1413),
    (1455, "@eudisbocuda", "@marcelinho_jhonson", 1454),
    (2216, "@bahiadohype", "@apoline", 2226),
]


def main():
    linhas = pipeline.carregar_planilha()
    por_linha = {l["excel_row"]: l for l in linhas}

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Erros de Preenchimento"

    cabecalho = [
        "Linha com link errado", "Influenciador anotado (errado)", "Data anotada",
        "Dono real do conteúdo (evidência: nome dos arquivos)", "Linha correta desse dono",
        "Link do Drive (compartilhado por engano)",
    ]
    ws.append(cabecalho)
    for cel in ws[1]:
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill(start_color="0D2137", end_color="0D2137", fill_type="solid")

    for linha_errada, influ_errado, dono_real, linha_certa in CASOS_CONFIRMADOS:
        l = por_linha.get(linha_errada)
        link = l["link"] if l else ""
        row = [linha_errada, influ_errado, l["data"] if l else "", dono_real, linha_certa, link]
        ws.append(row)
        if link:
            cel = ws.cell(row=ws.max_row, column=6)
            cel.hyperlink = Hyperlink(ref=cel.coordinate, target=link)
            cel.font = Font(color="0563C1", underline="single")

    larguras = {"A": 18, "B": 26, "C": 14, "D": 42, "E": 18, "F": 60}
    for col, largura in larguras.items():
        ws.column_dimensions[col].width = largura
    ws.freeze_panes = "A2"
    for row in ws.iter_rows(min_row=2):
        row[3].alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(DESTINO)
    print(f"{len(CASOS_CONFIRMADOS)} caso(s) confirmado(s) de erro de preenchimento.")
    print(f"Relatório salvo em: {DESTINO}")
    return DESTINO


if __name__ == "__main__":
    main()
