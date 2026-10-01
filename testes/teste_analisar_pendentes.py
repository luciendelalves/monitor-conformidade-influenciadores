# -*- coding: utf-8 -*-
"""A varredura de linhas paradas não pode pegar o que não é dela.

POR QUE ESTE TESTE EXISTE (22/09/2026)

A máquina da Responsável B baixa e organiza normal, mas a análise nunca acontece: a
linha fica em AGUARDANDO VALIDAÇÃO para sempre. Medido no mesmo dia com a
linha 108 (@crissevieri.mov): mandada para análise de OUTRA máquina, saiu
CONFORME em menos de três minutos. Ou seja, a linha e o arquivo estavam bons,
e o problema está na fila local dela, que não é compartilhada.

Enquanto a causa de lá não é achada, `analisar_pendentes.py` é a ponte. E uma
varredura assim é perigosa por natureza, porque desfaz decisão humana sem
perguntar. Daí as quatro regras que este teste guarda:

1. NÃO mexe em linha que já tem veredito. A automação só escreve em célula
   vazia, então reanalisar por cima seria trabalho jogado fora, e apagar o
   veredito de alguém seria pior.
2. NÃO mexe em linha sem arquivo para conferir (N/A, link de YouTube, linha do
   Marketing preenchida à mão).
3. SÓ as linhas de quem está com problema. Varrer as da Responsável A, cujo fluxo
   funciona, seria mexer no que está de pé: linha sem veredito lá pode ser
   decisão dela.
4. SÓ os últimos dias. Linha antiga tem chance de ter sido deixada de lado de
   propósito.

E mais uma, que é o motivo de a varredura existir: vídeo que já está na fila
local NÃO pode ser mandado de novo, mas precisa APARECER, porque é
exatamente aí que mora a falha silenciosa (`enfileirar_analise` descarta
repetido sem dizer nada).

Não fala com planilha nenhuma: as linhas são de mentira.

Rodar:

    py testes\\teste_analisar_pendentes.py
"""
import os
import sys
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import analisar_pendentes as varredura

falhas = []
HOJE = date(2026, 9, 22)


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def linha(excel_row, **troca):
    base = {
        "excel_row": excel_row,
        "influenciador": "@crissevieri.mov",
        "data": "2026-09-21",
        "data_download": "22/09/2026",
        "link": f"https://drive.google.com/file/d/id{excel_row}/view",
        "situacao": "AGUARDANDO VALIDAÇÃO",
        "veredito_na_planilha": "",
        "pedido_por": "responsavel.b@empresa.com",
        "marcacao": "LINK",
    }
    base.update(troca)
    return base


def rodar():
    print("--- 1. o caso normal: linha da Responsável B, parada, recente ---")
    mandar, presas = varredura.pendentes_para_analisar([linha(108)], hoje=HOJE)
    conferir(len(mandar) == 1, "entra na varredura", str(len(mandar)))
    conferir(not presas, "e não aparece como presa", str(presas))

    print()
    print("--- 2. o que NÃO pode ser tocado ---")
    casos = [
        ("já tem veredito", linha(201, veredito_na_planilha="CONFORME")),
        ("veredito de recusa também", linha(202, veredito_na_planilha="NÃO CONFORME")),
        ("sem arquivo para conferir (N/A)", linha(203, situacao="N/A")),
        ("texto antigo de sem arquivo", linha(204, situacao="SEM ARQUIVO")),
        ("situação vazia, linha preenchida à mão", linha(205, situacao="")),
        ("sem endereço nenhum", linha(206, link="")),
        ("baixada há muito tempo", linha(207, data_download="01/08/2026")),
    ]
    for descricao, l in casos:
        mandar, _ = varredura.pendentes_para_analisar([l], hoje=HOJE)
        conferir(not mandar, f"fica de fora: {descricao}", str(list(mandar)))

    print()
    print("--- 3. só as linhas de quem está com problema ---")
    das_duas = [linha(300), linha(301, influenciador="@carlinhos",
                                  pedido_por="responsavel.a@empresa.com")]
    mandar, _ = varredura.pendentes_para_analisar(das_duas, hoje=HOJE)
    conferir(len(mandar) == 1, "pega uma das duas", str(len(mandar)))
    linhas_pegas = [l[0]["excel_row"] for l in mandar.values()]
    conferir(linhas_pegas == [300],
             "e é a da Responsável B, não a da Responsável A", str(linhas_pegas))

    mandar, _ = varredura.pendentes_para_analisar(das_duas, hoje=HOJE, quem="todos")
    conferir(len(mandar) == 2, "com --quem todos, pega as duas", str(len(mandar)))

    mandar, _ = varredura.pendentes_para_analisar(
        [linha(302, pedido_por="")], hoje=HOJE)
    conferir(not mandar,
             "linha sem quem baixou fica de fora quando há filtro de pessoa",
             str(list(mandar)))

    print()
    print("--- 4. vídeo já na fila aparece, mas não é mandado de novo ---")
    l = linha(400)
    mandar, presas = varredura.pendentes_para_analisar(
        [l], ja_na_fila=[l["link"]], hoje=HOJE)
    conferir(not mandar, "não manda de novo", str(list(mandar)))
    conferir(len(presas) == 1,
             "e APARECE como presa, que é onde mora a falha silenciosa",
             str(presas))

    print()
    print("--- 5. carrossel: várias linhas, um veredito só ---")
    mesmo = "https://drive.google.com/file/d/mesmo/view"
    mandar, _ = varredura.pendentes_para_analisar(
        [linha(500, link=mesmo), linha(501, link=mesmo), linha(502, link=mesmo)],
        hoje=HOJE)
    conferir(len(mandar) == 1, "vira uma tarefa só", str(len(mandar)))
    conferir(sorted(l["excel_row"] for l in list(mandar.values())[0]) == [500, 501, 502],
             "com as três linhas juntas")

    print()
    print("--- 6. data ilegível não some em silêncio ---")
    mandar, _ = varredura.pendentes_para_analisar(
        [linha(600, data_download="")], hoje=HOJE)
    conferir(len(mandar) == 1,
             "linha sem data de download entra em vez de sumir", str(len(mandar)))

    print()
    print("--- 7. a janela de dias é respeitada nas duas pontas ---")
    mandar, _ = varredura.pendentes_para_analisar(
        [linha(700, data_download="16/09/2026")], hoje=HOJE, dias=7)
    conferir(len(mandar) == 1, "dentro dos 7 dias entra", str(len(mandar)))
    mandar, _ = varredura.pendentes_para_analisar(
        [linha(701, data_download="14/09/2026")], hoje=HOJE, dias=7)
    conferir(not mandar, "fora dos 7 dias não entra", str(list(mandar)))
    mandar, _ = varredura.pendentes_para_analisar(
        [linha(702, data_download="14/09/2026")], hoje=HOJE, dias=30)
    conferir(len(mandar) == 1, "e --dias 30 alcança ela", str(len(mandar)))

    print()
    print("--- 8. data de dois dígitos, como o Sheets devolve ---")
    mandar, _ = varredura.pendentes_para_analisar(
        [linha(800, data_download="22/09/26")], hoje=HOJE)
    conferir(len(mandar) == 1,
             "22/09/26 é lida como data, não como texto estranho", str(len(mandar)))


if __name__ == "__main__":
    print("=" * 74)
    print("  Varredura de linhas paradas esperando análise")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
