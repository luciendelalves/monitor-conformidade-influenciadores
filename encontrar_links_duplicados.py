"""
Varre a planilha inteira procurando links do Drive usados em mais de uma
linha — achado real de auditoria: a mesma pasta apareceu em datas/posts
diferentes (ex: linhas 164/192 do @capitaopitomba, 109/127 entre @feijhonys
e @joaovictorr10), o que geralmente indica erro de cadastro do Marketing.

Rodar: py encontrar_links_duplicados.py
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "_drive_credenciais"))
import pipeline_influenciadores as pipeline


def main():
    linhas = pipeline.carregar_planilha()
    link_para_linhas = {}
    for l in linhas:
        link_para_linhas.setdefault(l["link"], []).append(l)

    duplicados = {link: ls for link, ls in link_para_linhas.items() if len(ls) > 1}

    if not duplicados:
        print("Nenhum link duplicado encontrado.")
        return

    print(f"{len(duplicados)} link(s) duplicado(s) encontrado(s):\n")
    for link, ls in duplicados.items():
        linhas_str = ", ".join(str(l["excel_row"]) for l in ls)
        influenciadores = {l["influenciador"] for l in ls}
        aviso_influ = " (INFLUENCIADORES DIFERENTES!)" if len(influenciadores) > 1 else ""
        print(f"Linhas {linhas_str}{aviso_influ}")
        for l in ls:
            print(f"  - linha {l['excel_row']}: @{l['influenciador']} — {l['data']}")
        print(f"  link: {link}\n")


if __name__ == "__main__":
    main()
