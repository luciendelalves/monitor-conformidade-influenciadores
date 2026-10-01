"""
Sincroniza a planilha de trabalho da Auditoria ("AUDITORIA - VALIDAÇÃO MKT
INFLU") com a planilha real de origem do Marketing ("Marketing de Influência",
aba "Monitoramento") — copia só as linhas com link que ainda não existem na
nossa planilha. Só LÊ a planilha do Marketing, nunca escreve nela; a escrita
acontece exclusivamente na cópia de trabalho da própria Auditoria.

Uso:
    py sincronizar_planilha_marketing.py            -> só mostra o que seria adicionado (não grava nada)
    py sincronizar_planilha_marketing.py aplicar     -> grava de fato as linhas novas

Novidade não vira aviso de conformidade sozinha: a linha só é copiada (colunas
A-E, os mesmos dados brutos que o Marketing já tem). A classificação (coluna F
em diante) continua sendo gerada depois, pelo app de validação, do jeito de
sempre.
"""

import os
import sys
import tempfile

import openpyxl

sys.path.append(os.path.join(os.path.dirname(__file__), "_drive_credenciais"))
import drive_client
import sheets_client
import pipeline_influenciadores as pipeline

MARKETING_FILE_ID = "13uLhupENDl6bSHfRioaQz0mcZUio_IOojp1_c1CFhQU"
MARKETING_ABA = "Monitoramento"

# O escopo real da auditoria começa em maio/2026 (jan-abr foram excluídos de
# propósito, não é lacuna esquecida) — confirmado com o auditor antes de fixar
# essa data, pra não confundir "fora do escopo" com "backlog perdido".
DATA_MINIMA = "2026-05-01"

# A planilha da Auditoria hoje só cobre esses tipos (confirmado por contagem
# real antes de escrever este script). LIVE (Twitch/YouTube/Kick) é um formato
# tecnicamente diferente — não dá pra baixar e rodar OCR/transcrição numa live
# do mesmo jeito que num Story/Reel/Feed gravado — por isso fica de fora até
# haver uma decisão explícita de expandir o escopo pra esse formato.
TIPOS_NO_ESCOPO = {"STORIES", "REELS", "FEED", "X/TWITTER"}


def carregar_novidades_marketing():
    with tempfile.TemporaryDirectory() as tmp:
        dest = os.path.join(tmp, "marketing.xlsx")
        drive_client.export_file(
            MARKETING_FILE_ID,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            dest,
        )
        wb = openpyxl.load_workbook(dest, data_only=True)
        ws = wb[MARKETING_ABA]
        linhas = []
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
            # Colunas do Monitoramento (a coluna A da aba é vazia, por isso o
            # índice 0 nunca é usado aqui): B=influenciador, L=ano,
            # M=data_post, O=tipo, R=marca, T=link.
            influ, ano, data_post, tipo, marca, link = row[1], row[11], row[12], row[14], row[17], row[19]
            if not link or not data_post or not hasattr(data_post, "strftime"):
                continue
            data_str = data_post.strftime("%Y-%m-%d")
            if data_str < DATA_MINIMA:
                continue
            linhas.append({
                "influenciador": influ,
                "ano": int(ano) if ano else data_post.year,
                "data": data_post,
                "data_str": data_str,
                "tipo": tipo,
                "marca": marca,
                "link": link.strip() if isinstance(link, str) else link,
            })
        return linhas


def detectar_novidades():
    marketing = carregar_novidades_marketing()
    existentes = pipeline.carregar_planilha()
    links_existentes = {l["link"].strip() for l in existentes if l.get("link")}
    candidatas = [l for l in marketing if l["link"] not in links_existentes]

    tipo_ok = [l for l in candidatas if (l["tipo"] or "").upper() in TIPOS_NO_ESCOPO]
    fora_do_escopo = [l for l in candidatas if (l["tipo"] or "").upper() not in TIPOS_NO_ESCOPO]

    # O Marketing usa a própria coluna de link como bloco de notas às vezes
    # ("ADICIONAR LINK (JOÃO)", "PERDI DE BAIXAR MUITO STORY", "ORGÂNICO") —
    # isso não é uma URL e não pode virar linha na planilha da Auditoria como
    # se fosse um link de verdade.
    no_escopo = [l for l in tipo_ok if isinstance(l["link"], str) and l["link"].startswith("http")]
    link_invalido = [l for l in tipo_ok if l not in no_escopo]

    # Mais antigas primeiro, pra ficar na mesma ordem cronológica do resto da planilha.
    no_escopo.sort(key=lambda l: l["data_str"])
    return no_escopo, fora_do_escopo, link_invalido


def main():
    aplicar = len(sys.argv) > 1 and sys.argv[1] == "aplicar"

    novas, fora_do_escopo, link_invalido = detectar_novidades()

    if fora_do_escopo:
        from collections import Counter
        contagem = Counter((l["tipo"] or "").upper() for l in fora_do_escopo)
        print(f"{len(fora_do_escopo)} linha(s) do Marketing NÃO foram consideradas (tipo fora do escopo atual — {dict(contagem)}).")
        print()

    if link_invalido:
        print(f"{len(link_invalido)} linha(s) do Marketing têm tipo no escopo mas a coluna LINK não é uma URL real (ex: nota tipo 'ADICIONAR LINK (...)') — ficaram de fora também, listadas abaixo pra você repassar ao Marketing se quiser:")
        for l in link_invalido[:15]:
            print(f"  {l['influenciador']} | {l['data_str']} | {l['link']!r}")
        if len(link_invalido) > 15:
            print(f"  ... e mais {len(link_invalido) - 15}")
        print()

    print(f"{len(novas)} linha(s) nova(s) encontrada(s) no Marketing (a partir de {DATA_MINIMA}, tipos {sorted(TIPOS_NO_ESCOPO)}) que ainda não estão na planilha da Auditoria.")
    print()
    for l in novas[:20]:
        print(f"  {l['influenciador']} | {l['tipo']} | {l['marca']} | {l['data_str']} | {l['link']}")
    if len(novas) > 20:
        print(f"  ... e mais {len(novas) - 20}")

    if not aplicar:
        print()
        print("Modo pré-visualização — nada foi gravado. Rode com o argumento 'aplicar' para gravar na planilha da Auditoria.")
        return

    if not novas:
        print("Nada para gravar.")
        return

    linhas_para_gravar = [
        [l["influenciador"], l["ano"], l["data_str"], l["tipo"], l["link"]]
        for l in novas
    ]
    sheets_client.adicionar_linhas(pipeline.PLANILHA_ID, pipeline.NOME_ABA_SHEETS, "A:E", linhas_para_gravar)
    print(f"{len(novas)} linha(s) gravada(s) na planilha da Auditoria.")


if __name__ == "__main__":
    main()
