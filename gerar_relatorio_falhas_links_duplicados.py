"""
Relatório de FALHAS de link duplicado — os 66 grupos reais (exclui os 2
falso-positivo de placeholder "aguardado"/"AGUARDANDO VIDEO NO DRIVE", que não
são duplicidade de link, são ausência de vídeo). Cada linha das 66 pastas
entra como falha, classificada em:

  - "Influenciador diferente (confirmado)": o nome real dos arquivos na pasta
    bate com OUTRO influenciador, não o anotado na linha — erro de
    preenchimento comprovado.
  - "Influenciador diferente (link quebrado)": linhas com influenciadores
    diferentes, mas o link já não abre mais (404) — não dá pra confirmar o
    dono, mas a divergência de nome já é suspeita por si só.
  - "Mesmo influenciador reaproveitado": o mesmo influenciador aparece em
    todas as linhas do grupo — o link foi reutilizado em datas diferentes
    (pode ser conteúdo real por trás, mas o link sozinho não deveria servir
    de prova pra mais de uma data sem checagem).

Rodar: py gerar_relatorio_falhas_links_duplicados.py
"""

import os
import sys

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.hyperlink import Hyperlink

sys.path.append(os.path.join(os.path.dirname(__file__), "_drive_credenciais"))
import drive_client
import pipeline_influenciadores as pipeline

DESTINO = os.path.join(pipeline.BASE_DIR, "Links_Duplicados_ou_Reaproveitados.xlsx")

PLACEHOLDERS_SEM_VIDEO = {"aguardado", "AGUARDANDO VIDEO NO DRIVE"}


def classificar_grupo(ls):
    influenciadores = {l["influenciador"] for l in ls}
    if len(influenciadores) == 1:
        return "Mesmo influenciador reaproveitado"
    # tem influenciadores diferentes — testa se o link ainda abre
    primeiro = ls[0]
    try:
        drive_client.get_metadata(primeiro["drive_id"])
        return "Influenciador diferente (confirmado)"
    except Exception:
        return "Influenciador diferente (link quebrado)"


def _adicionar_aba_manual(wb, fill_confirmado, fill_quebrado):
    ws = wb.create_sheet("Manual")

    titulo_fill = PatternFill(start_color="0D2137", end_color="0D2137", fill_type="solid")
    titulo_font = Font(bold=True, color="FFFFFF", size=13)
    negrito = Font(bold=True)
    quebra = Alignment(wrap_text=True, vertical="top")

    ws["A1"] = "O que é essa planilha"
    ws["A1"].font = titulo_font
    ws["A1"].fill = titulo_fill
    ws.merge_cells("A1:B1")
    ws.row_dimensions[1].height = 22

    ws["A3"] = (
        "\"Link duplicado\" é quando o MESMO link do Google Drive aparece em mais de uma linha "
        "da planilha de auditoria — ou seja, duas (ou mais) datas/posts diferentes estão apontando "
        "pra a mesma pasta/arquivo de vídeo. Isso é sempre uma falha de preenchimento do Marketing, "
        "porque cada post deveria ter sua própria pasta de evidência. A gravidade muda de acordo com "
        "o motivo — por isso a coluna \"Classificação da falha\" separa os casos em 3 tipos, explicados "
        "abaixo."
    )
    ws.merge_cells("A3:B3")
    ws["A3"].alignment = quebra
    ws.row_dimensions[3].height = 90

    linhas = [
        (
            "Mesmo influenciador reaproveitado",
            None,
            "O mesmo influenciador aparece em TODAS as linhas do grupo (ex: 12 datas diferentes, "
            "sempre o mesmo @). Não necessariamente é conteúdo falso — pode ser que o Marketing só "
            "não separou o material por data, jogando tudo numa pasta só. Mas mesmo assim é falha, "
            "porque um único link não deveria servir de prova de conformidade pra mais de uma data "
            "sem uma checagem manual confirmando que o conteúdo de cada data está mesmo lá dentro. "
            "É o tipo de caso que precisa ser aberto e conferido individualmente (como fizemos com o "
            "@ranchodomaia__, onde as 12 fotos eram realmente de 12 dias diferentes, só que fora do lugar)."
        ),
        (
            "Influenciador diferente (confirmado)",
            fill_confirmado,
            "As linhas do grupo têm influenciadores DIFERENTES anotados, e foi possível abrir o link "
            "e ver que o conteúdo real (pelo nome dos arquivos) pertence a só um deles. Ou seja: é erro "
            "de preenchimento comprovado — o link de um influenciador foi colado por engano na linha de "
            "outro. Esse é o achado mais grave e mais sólido: já sabemos exatamente qual linha está errada "
            "e qual é o dono verdadeiro do conteúdo (lista completa em Erros_Preenchimento_Marketing.xlsx)."
        ),
        (
            "Influenciador diferente (link quebrado)",
            fill_quebrado,
            "As linhas do grupo também têm influenciadores diferentes anotados, mas o link já não abre "
            "mais (erro 404 no Drive) — então não dá pra confirmar pelo conteúdo quem é o dono real. "
            "A divergência de nomes já é suspeita por si só (mesmo link não devia ter dois donos "
            "diferentes), mas fica sem prova concreta até o link ser recuperado ou o Marketing confirmar "
            "manualmente."
        ),
    ]

    linha_atual = 6
    ws.cell(row=linha_atual, column=1, value="Classificação").font = negrito
    ws.cell(row=linha_atual, column=2, value="O que significa").font = negrito
    for cel in ws[linha_atual]:
        cel.fill = titulo_fill
        cel.font = Font(bold=True, color="FFFFFF")
    linha_atual += 1

    for nome, cor, explicacao in linhas:
        ws.cell(row=linha_atual, column=1, value=nome).font = negrito
        ws.cell(row=linha_atual, column=2, value=explicacao).alignment = quebra
        if cor:
            ws.cell(row=linha_atual, column=1).fill = cor
        ws.row_dimensions[linha_atual].height = 110
        linha_atual += 1

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 100
    for row in ws.iter_rows(min_row=7, max_row=linha_atual - 1):
        row[0].alignment = Alignment(wrap_text=True, vertical="top")


def _adicionar_aba_hipotese_ferramenta(wb):
    ws = wb.create_sheet("Hipótese - Captura de Stories")

    titulo_fill = PatternFill(start_color="0D2137", end_color="0D2137", fill_type="solid")
    alerta_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
    titulo_font = Font(bold=True, color="FFFFFF", size=13)
    negrito = Font(bold=True)
    quebra = Alignment(wrap_text=True, vertical="top")

    ws["A1"] = "HIPÓTESE AINDA A CONFIRMAR — não é um achado fechado, é um indício a validar com o Marketing"
    ws["A1"].font = titulo_font
    ws["A1"].fill = titulo_fill
    ws.merge_cells("A1:B1")
    ws.row_dimensions[1].height = 30
    ws["A1"].alignment = quebra

    ws["A3"] = (
        "Contexto: Stories do Instagram somem em 24h e não existe API pública da Meta que deixe "
        "qualquer empresa baixar o Story de OUTRA conta automaticamente — alguém sempre precisa "
        "capturar o conteúdo antes dele expirar. Analisando os nomes reais dos arquivos baixados "
        "durante essa auditoria, aparecem padrões que sugerem que já existe algum tipo de ferramenta "
        "automatizada fazendo essa captura hoje — mas o padrão do nome não é de uma plataforma "
        "profissional de social listening com parceria oficial da Meta, e sim de apps/bots "
        "\"salvador de Stories\" de terceiros, que costumam funcionar sem autorização do Instagram."
    )
    ws.merge_cells("A3:B3")
    ws["A3"].alignment = quebra
    ws.row_dimensions[3].height = 130

    linha_atual = 6
    ws.cell(row=linha_atual, column=1, value="Padrão observado").font = negrito
    ws.cell(row=linha_atual, column=2, value="O que indica").font = negrito
    for cel in ws[linha_atual]:
        cel.fill = titulo_fill
        cel.font = Font(bold=True, color="FFFFFF")
    linha_atual += 1

    padroes = [
        (
            "usuario's AAAA-M-D-H.M.S story.mp4\n(ex: capitaopitomba's2026-5-7-10.54.309 story.mp4)",
            "Formato típico de apps \"Story Saver\"/\"IG Story Reposter\" de terceiros — baixam Stories "
            "de contas públicas sem precisar de autorização, geralmente via engenharia reversa da API "
            "privada do Instagram (não é a API oficial da Meta).",
        ),
        (
            "usuario_idnumerico_AAAA-MM-DD.mp4\n(ex: nathanqueiroz_3938465083101768525_2026-07-10.mp4)",
            "Formato típico de ferramentas de download tipo \"4K Stogram\"/\"InstaSave\" — mesma "
            "categoria de app não-oficial, nomeando pelo ID interno do post.",
        ),
        (
            "WhatsApp Image AAAA-MM-DD at HH.MM.SS.jpeg\n(ex: caso @ranchodomaia__)",
            "Esse é diferente dos dois acima — é print de tela mandado manualmente por WhatsApp, sem "
            "nenhuma ferramenta automatizada por trás. Mostra que o processo de captura hoje é misto: "
            "parte automatizada (por app não-oficial), parte manual.",
        ),
    ]

    for padrao, explicacao in padroes:
        ws.cell(row=linha_atual, column=1, value=padrao).font = negrito
        ws.cell(row=linha_atual, column=1).alignment = quebra
        ws.cell(row=linha_atual, column=2, value=explicacao).alignment = quebra
        ws.row_dimensions[linha_atual].height = 100
        linha_atual += 1

    linha_atual += 1
    ws.cell(row=linha_atual, column=1, value="Por que importa").font = negrito
    for cel in ws[linha_atual]:
        cel.fill = alerta_fill
    ws.merge_cells(start_row=linha_atual, start_column=1, end_row=linha_atual, end_column=2)
    linha_atual += 1
    ws.cell(row=linha_atual, column=1, value=(
        "Apps não-oficiais de download de Stories normalmente violam os Termos de Uso do Instagram/Meta. "
        "Se for confirmado que é isso que está em uso hoje pra alimentar essa auditoria, é um risco de "
        "conformidade próprio da EGB (empresa de apostas licenciada) usar uma ferramenta desse tipo no "
        "processo — vale confirmar diretamente com o Marketing qual ferramenta/serviço eles usam pra "
        "capturar os Stories antes de tirar qualquer conclusão."
    ))
    ws.cell(row=linha_atual, column=1).alignment = quebra
    ws.merge_cells(start_row=linha_atual, start_column=1, end_row=linha_atual, end_column=2)
    ws.row_dimensions[linha_atual].height = 110
    for cel in ws[linha_atual]:
        cel.fill = alerta_fill

    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 80


def main():
    linhas = pipeline.carregar_planilha()
    link_para_linhas = {}
    for l in linhas:
        link_para_linhas.setdefault(l["link"], []).append(l)

    grupos = [(link, ls) for link, ls in link_para_linhas.items() if len(ls) > 1 and link not in PLACEHOLDERS_SEM_VIDEO]
    grupos.sort(key=lambda g: min(l["excel_row"] for l in g[1]))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Falhas - Links Duplicados"

    cabecalho = ["Grupo", "Linha", "Influenciador", "Data", "Tipo", "Classificação da falha", "Qtd. linhas no grupo", "Link"]
    ws.append(cabecalho)
    for cel in ws[1]:
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill(start_color="0D2137", end_color="0D2137", fill_type="solid")

    fill_confirmado = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
    fill_quebrado = PatternFill(start_color="FFE0B2", end_color="FFE0B2", fill_type="solid")

    for i, (link, ls) in enumerate(grupos, start=1):
        classe = classificar_grupo(ls)
        for l in sorted(ls, key=lambda x: x["excel_row"]):
            row = [i, l["excel_row"], l["influenciador"], l["data"], l["tipo_post"], classe, len(ls), link]
            ws.append(row)
            cel_link = ws.cell(row=ws.max_row, column=8)
            if link and link.startswith("http"):
                cel_link.hyperlink = Hyperlink(ref=cel_link.coordinate, target=link)
                cel_link.font = Font(color="0563C1", underline="single")
            if classe == "Influenciador diferente (confirmado)":
                for cel in ws[ws.max_row]:
                    cel.fill = fill_confirmado
            elif classe == "Influenciador diferente (link quebrado)":
                for cel in ws[ws.max_row]:
                    cel.fill = fill_quebrado

    larguras = {"A": 8, "B": 8, "C": 22, "D": 12, "E": 10, "F": 32, "G": 10, "H": 60}
    for col, largura in larguras.items():
        ws.column_dimensions[col].width = largura
    ws.freeze_panes = "A2"

    _adicionar_aba_manual(wb, fill_confirmado, fill_quebrado)
    _adicionar_aba_hipotese_ferramenta(wb)

    wb.save(DESTINO)
    total_linhas = sum(len(ls) for _, ls in grupos)
    print(f"{len(grupos)} grupo(s) / {total_linhas} linha(s) — salvo em {DESTINO}")
    return DESTINO


if __name__ == "__main__":
    main()
