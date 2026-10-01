"""
Gera um Excel com todos os casos classificados como "REQUER ANÁLISE HUMANA"
(a IA não conseguiu confirmar nem descartar algum elemento obrigatório com
segurança) — lista de trabalho pra revisão manual, com link direto pro vídeo
específico apontado como problema em cada linha. Não escreve na planilha
original, só lê o cache já processado.

Rodar: py gerar_relatorio_requer_analise.py
"""

import os

import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.hyperlink import Hyperlink

import pipeline_influenciadores as pipeline

DESTINO = os.path.join(pipeline.BASE_DIR, "Casos_Requer_Analise_Humana.xlsx")


def main():
    linhas = pipeline.carregar_planilha()
    cache = pipeline.carregar_cache()

    casos = []
    for l in linhas:
        r = cache.get(l["link"])
        if not r:
            continue
        veredito = pipeline.formatar_para_planilha(r)
        if veredito and veredito.upper().startswith("REQUER"):
            casos.append((l, r, veredito))

    casos.sort(key=lambda c: c[0]["excel_row"])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Requer Análise Humana"

    cabecalho = ["Linha", "Influenciador", "Data", "Tipo", "Veredito", "Motivo (o que a IA não confirmou)", "Vídeo/arquivo apontado"]
    ws.append(cabecalho)
    for cel in ws[1]:
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill(start_color="0D2137", end_color="0D2137", fill_type="solid")

    for l, r, veredito in casos:
        arquivo = r.get("arquivo", "")
        link_video = r.get("link_video_problema")
        row = [l["excel_row"], l["influenciador"], l["data"], l["tipo_post"], veredito, r.get("motivo", ""), arquivo]
        ws.append(row)
        if link_video:
            cel = ws.cell(row=ws.max_row, column=7)
            cel.hyperlink = Hyperlink(ref=cel.coordinate, target=link_video)
            cel.font = Font(color="0563C1", underline="single")

    larguras = {"A": 8, "B": 22, "C": 12, "D": 10, "E": 20, "F": 90, "G": 45}
    for col, largura in larguras.items():
        ws.column_dimensions[col].width = largura
    ws.freeze_panes = "A2"
    for row in ws.iter_rows(min_row=2):
        row[5].alignment = openpyxl.styles.Alignment(wrap_text=True, vertical="top")

    wb.save(DESTINO)
    print(f"{len(casos)} caso(s) de Requer Análise Humana.")
    print(f"Relatório salvo em: {DESTINO}")


if __name__ == "__main__":
    main()
