"""
Gera um relatório em Excel dos links do Drive reaproveitados em mais de uma
linha da planilha "AUDITORIA - VALIDAÇÃO MKT INFLU" — pra levar ao Marketing
ou documentar o achado de auditoria. Não altera nada na planilha original.

Rodar: py gerar_relatorio_links_duplicados.py
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "_drive_credenciais"))
import openpyxl
from openpyxl.styles import Font, PatternFill
import drive_client
import pipeline_influenciadores as pipeline

DESTINO = os.path.join(pipeline.BASE_DIR, "Relatorio_Links_Duplicados.xlsx")


def listar_conteudo(link, tipo_link, drive_id):
    """Lista os nomes dos arquivos reais dentro do link (pasta ou arquivo
    único), sem baixar nada — só pra dar pista de qual influenciador é dono
    de verdade do conteúdo (o nome do arquivo geralmente vem com o @)."""
    try:
        if tipo_link == "DRIVE_FOLDER":
            itens = drive_client.list_folder(drive_id)
            nomes = [it.get("name", "") for it in itens]
            return "; ".join(nomes) if nomes else "(pasta vazia)"
        elif tipo_link == "DRIVE_FILE":
            meta = drive_client.get_metadata(drive_id)
            return meta.get("name", "")
    except Exception as e:
        return f"ERRO ao acessar: {e}"
    return ""


def main():
    linhas = pipeline.carregar_planilha()
    link_para_linhas = {}
    for l in linhas:
        link_para_linhas.setdefault(l["link"], []).append(l)

    grupos = [(link, ls) for link, ls in link_para_linhas.items() if len(ls) > 1]
    grupos.sort(key=lambda g: min(l["excel_row"] for l in g[1]))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Links Duplicados"

    cabecalho = ["Grupo", "Linha", "Influenciador", "Data", "Tipo", "Qtd. linhas no grupo", "Influenciadores diferentes?", "Arquivos reais na pasta/link", "Link"]
    ws.append(cabecalho)
    for cel in ws[1]:
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill(start_color="0D2137", end_color="0D2137", fill_type="solid")

    fill_alerta = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")

    for i, (link, ls) in enumerate(grupos, start=1):
        influenciadores = {l["influenciador"] for l in ls}
        diferentes = len(influenciadores) > 1
        primeiro = ls[0]
        conteudo = listar_conteudo(link, primeiro["tipo_link"], primeiro["drive_id"])
        print(f"[{i}/{len(grupos)}] linhas {[l['excel_row'] for l in ls]}: {conteudo[:80]}")
        for l in sorted(ls, key=lambda x: x["excel_row"]):
            row = [i, l["excel_row"], l["influenciador"], l["data"], l["tipo_post"], len(ls), "SIM" if diferentes else "não", conteudo, link]
            ws.append(row)
            if diferentes:
                for cel in ws[ws.max_row]:
                    cel.fill = fill_alerta

    for col, largura in zip("ABCDEFGHI", [8, 8, 22, 12, 10, 10, 14, 60, 60]):
        ws.column_dimensions[col].width = largura
    ws.freeze_panes = "A2"

    wb.save(DESTINO)
    print(f"\n{len(grupos)} grupo(s) de link duplicado, {sum(len(ls) for _, ls in grupos)} linha(s) envolvidas.")
    print(f"Relatório salvo em: {DESTINO}")


if __name__ == "__main__":
    main()
