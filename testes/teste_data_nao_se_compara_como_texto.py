# -*- coding: utf-8 -*-
"""
Data de célula se compara como DATA, nunca como texto.

POR QUE ESTE ARQUIVO EXISTE (07/09/2026)

O auditor baixou duas telas do mesmo story, no mesmo dia, e elas saíram como
POST 1 e POST 2: "cada pacote de story conta como 1 post, ou seja, aqui era para
estar post 1 e 1".

O EFEITO ERA GRAVE, não cosmético: a cota do contrato é contada em POSTS. Duas
telas do mesmo dia viravam duas entregas onde houve uma, e a conferência de cota
ficava inflada sem ninguém perceber. Um influenciador que publicasse cinco telas
num dia apareceria com cinco posts entregues.

A REGRA ESTAVA CERTA DESDE 03/09/2026, A COMPARAÇÃO ESTAVA ERRADA. O programa
grava "06/09/2026"; o Google Sheets reconhece aquilo como data, guarda como
número de série e devolve, na leitura, o formato de exibição da coluna:
"06/09/26". Então "06/09/26" != "06/09/2026", cada tela parecia um dia novo, e o
número incrementava.

O MESMO DEFEITO ESTAVA NO FILTRO "só os baixados hoje" da tela de validação, que
comparava `data_download` com "%d/%m/%Y" e por isso provavelmente nunca achou
nada.

A LIÇÃO QUE ESTE TESTE PROTEGE: quando a planilha é a camada de guarda, o
formato de exibição é do Marketing, muda quando eles quiserem, e não é contrato
de dado. Comparar data como texto é apostar num formato que não é nosso.

Rodar:

    py testes\teste_data_nao_se_compara_como_texto.py
"""
import os
import sys
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    import fluxo_downloads as fluxo

    print("--- 1. o leitor reconhece as grafias do dado real ---")
    esperado = date(2026, 9, 6)
    for bruto in ("06/09/26", "06/09/2026", "2026-09-06", "06-09-2026",
                  "06.09.2026", "46271", 46271):
        conferir(fluxo.data_de_celula(bruto) == esperado,
                 f"{bruto!r} vira 06/09/2026",
                 str(fluxo.data_de_celula(bruto)))
    # 46271 e o numero de serie do Sheets, que vem quando a leitura e feita sem
    # formatacao. Sem trata-lo, mudar o modo de leitura quebraria a contagem.
    conferir(fluxo.data_de_celula("46271") == esperado,
             "inclusive o numero de serie do Sheets")

    print()
    print("--- 2. o que NAO e data devolve None, e nao chuta ---")
    for bruto in ("", None, "oi", "sem data", "  ", "0", "999999999"):
        conferir(fluxo.data_de_celula(bruto) is None,
                 f"{bruto!r} devolve None", str(fluxo.data_de_celula(bruto)))

    print()
    print("--- 3. mesmo_dia FALHA PARA FALSO quando nao sabe ---")
    # Dizer "mesmo dia" sem saber juntaria posts de dias diferentes num numero
    # so, que e o erro contrario e igualmente ruim.
    conferir(fluxo.mesmo_dia("06/09/26", "06/09/2026") is True,
             "duas grafias do mesmo dia sao o mesmo dia")
    conferir(fluxo.mesmo_dia("06/09/26", date(2026, 9, 6)) is True,
             "texto e objeto date tambem se comparam")
    conferir(fluxo.mesmo_dia("06/09/26", "07/09/2026") is False,
             "dias diferentes NAO sao o mesmo dia")
    for a, b in (("oi", "06/09/2026"), ("", ""), (None, "06/09/2026"),
                 ("06/09/26", None)):
        conferir(fluxo.mesmo_dia(a, b) is False,
                 f"ilegivel ({a!r}, {b!r}) responde FALSO, nao verdadeiro")

    print()
    print("--- 4. O CASO DO AUDITOR: duas telas, mesmo dia, POST 1 e 1 ---")
    C = fluxo.COL_MON
    larg = max(C.values())

    def linha(handle, data, ciclo, tipo, post, marc="LINK"):
        l = [""] * larg
        l[C["handle"] - 1] = handle
        l[C["data_post"] - 1] = data
        l[C["ciclo"] - 1] = ciclo
        l[C["tipo"] - 1] = tipo
        l[C["post"] - 1] = post
        l[C["marcacao"] - 1] = marc
        return l

    # a planilha devolve o ano com DOIS digitos, que era o que quebrava
    ja = [linha("@andersonneiff", "06/09/26", "4", "STORIES", "1")]
    n = fluxo._numero_do_post(ja, "@andersonneiff", "4", "STORIES",
                              date(2026, 9, 6), "LINK")
    conferir(n == 1, "segunda tela do MESMO dia reaproveita o POST 1", f"veio {n}")

    print()
    print("--- 5. e o dia NOVO continua incrementando ---")
    # A correcao nao pode achatar tudo em 1: dia novo e post novo, senao a cota
    # contaria uma entrega onde houve varias.
    n2 = fluxo._numero_do_post(ja, "@andersonneiff", "4", "STORIES",
                               date(2026, 9, 7), "LINK")
    conferir(n2 == 2, "primeira tela do dia seguinte vira POST 2", f"veio {n2}")

    print()
    print("--- 6. ORGANICO no mesmo dia continua sendo outro post ---")
    # Decisao do auditor em 03/09/2026, depois de falar com o Marketing: peca
    # organica e link no mesmo dia sao entregas de tipo diferente, dois posts.
    n3 = fluxo._numero_do_post(ja, "@andersonneiff", "4", "STORIES",
                               date(2026, 9, 6), "ORGANICO")
    conferir(n3 == 1, "organico tem contagem propria, nao herda a do link",
             f"veio {n3}")

    print()
    print("--- 7. tres telas seguidas no mesmo dia: 1, 1, 1 ---")
    acum, saiu = [], []
    for _ in range(3):
        p = fluxo._numero_do_post(acum, "@x", "1", "STORIES",
                                  date(2026, 9, 6), "LINK")
        saiu.append(p)
        acum.append(linha("@x", "06/09/26", "1", "STORIES", str(p)))
    conferir(saiu == [1, 1, 1], "as tres recebem POST 1", str(saiu))

    print()
    # SECAO 8 REMOVIDA EM 14/09/2026: testava o filtro "so os baixados hoje" da
    # tela app_validacao_influenciadores.py, que saiu do programa (Validacao
    # Regulatoria) sem esse filtro ser recriado no Monitoramento. Historico da
    # secao no Git, se um filtro de data equivalente nascer em outro lugar.
    print("--- 9. o PERIODO do aviso do Financeiro ordena por DATA ---")
    # O MESMO DEFEITO, EM OUTRO LUGAR (07/09/2026). O periodo do ciclo era
    # sorted() em cima do texto DD/MM/AA, o que ordena pelo DIA. Medido nas
    # 24.334 linhas reais da Monitoramento do Marketing: 822 dos 1.057 ciclos
    # com mais de uma data saiam com o intervalo errado, varios terminando
    # antes de comecar ("01/02/24 a 31/01/24"), e isso ia no texto que a pessoa
    # cola no WhatsApp do Financeiro.
    with open(os.path.join(BASE, "pages", "3_Financeiro.py"),
              encoding="utf-8") as f:
        fin = f.read()
    conferir("fluxo.data_de_celula(e[\"data_post\"])" in fin,
             "o periodo passa cada data pelo leitor de data")
    conferir('sorted({e["data_post"]' not in fin,
             "e nao sobrou sorted() direto no texto da data",
             "ordenar DD/MM/AA como texto ordena pelo dia")
    conferir("ilegível" in fin or "ilegivel" in fin,
             "data ilegivel e dita no proprio periodo, nao sumida em silencio")

    print()
    print("--- 10. e a prova do intervalo com o caso real invertido ---")
    # Caso medido de @sheldonsh1 ciclo 1: por texto dava 01/02/24 a 31/01/24.
    caso = ["02/01/24", "01/02/24", "31/01/24"]
    por_texto = sorted(caso)
    por_data = sorted(caso, key=lambda x: fluxo.data_de_celula(x))
    conferir((por_texto[0], por_texto[-1]) == ("01/02/24", "31/01/24"),
             "por texto o intervalo sai invertido (o defeito)",
             f"{por_texto[0]} a {por_texto[-1]}")
    conferir((por_data[0], por_data[-1]) == ("02/01/24", "01/02/24"),
             "por data o intervalo sai certo",
             f"{por_data[0]} a {por_data[-1]}")

    # -----------------------------------------------------------------
    # A REVISAO DE 07/09/2026 ACHOU A CORRECAO PELA METADE EM TRES LUGARES.
    # O dia ALVO passava pelo leitor de data desde a correcao da manha, mas a
    # contagem dos OUTROS dias, a chave da cota e o piso do numero de serie
    # continuavam errados. Os tres afetavam numero de auditoria.
    # -----------------------------------------------------------------
    print()
    print("--- 11. numero pequeno NAO vira data de 1900 ---")
    # Aceitava serie de 1 a 100000, entao "6" digitado sozinho na coluna de data
    # virava 05/01/1900 e "2026" virava 18/07/1905. Nao caia no ramo de "data
    # ilegivel" que existe para avisar: entrava como data valida, ordenava antes
    # de todas e ia para o texto colado no WhatsApp do Financeiro.
    for bruto in ("6", "31", "1", "2026", "100", "36525"):
        conferir(fluxo.data_de_celula(bruto) is None,
                 f"{bruto!r} nao e data", str(fluxo.data_de_celula(bruto)))
    conferir(fluxo.data_de_celula("46271") == date(2026, 9, 6),
             "e a serie real de 2026 continua sendo lida")

    print()
    print("--- 12. os OUTROS dias tambem se contam como data ---")
    ja2 = [linha("@x", "05/09/26", "1", "STORIES", "1"),
           linha("@x", "05/09/2026", "1", "STORIES", "1")]
    n = fluxo._numero_do_post(ja2, "@x", "1", "STORIES", date(2026, 9, 7), "LINK")
    conferir(n == 2, "duas grafias do mesmo dia contam UM dia, nao dois",
             f"veio {n}, e a cota e contada em POSTS")

    print()
    print("--- 13. a chave da COTA usa data, e nao texto ---")
    # Este era o mais direto no resultado: e a contagem que alimenta o
    # fechamento do ciclo no Financeiro.
    import escopo_e_entrega as ee

    def entrega(d, p):
        return {"handle": "x", "ciclo": "1", "tipo": "STORIES", "data_post": d,
                "post": p, "marcacao": "LINK", "situacao": "Conforme",
                "marca": "EDS", "link": "a"}

    c1 = ee.contar_entregas([entrega("05/09/26", "1"),
                             entrega("05/09/2026", "1")], "x", "1")
    conferir(sum(c1["entregue"].values()) == 1,
             "mesmo dia e mesmo POST, grafias diferentes: conta 1",
             str(sum(c1['entregue'].values())))
    c2 = ee.contar_entregas([entrega("05/09/26", "1"),
                             entrega("06/09/26", "1")], "x", "1")
    conferir(sum(c2["entregue"].values()) == 2,
             "e dias diferentes continuam contando 2",
             str(sum(c2['entregue'].values())))

    print()
    print("--- 14. a regra de data existe em UM lugar so ---")
    # Duas copias da mesma regra divergem na primeira mudanca, e foi exatamente
    # o que aconteceu entre a manha e a tarde de 07/09/2026.
    import re
    definicoes = 0
    for nome in ("fluxo_downloads.py", "escopo_e_entrega.py",
                 "data_de_planilha.py", os.path.join("pages", "3_Financeiro.py")):
        with open(os.path.join(BASE, nome), encoding="utf-8") as f:
            if re.search(r"^def data_de_celula", f.read(), re.M):
                definicoes += 1
    conferir(definicoes == 1, "data_de_celula definida uma unica vez",
             f"definida em {definicoes} arquivos")
    with open(os.path.join(BASE, "escopo_e_entrega.py"), encoding="utf-8") as f:
        motor = f.read()
    conferir("import fluxo_downloads" not in motor,
             "e o motor da auditoria continua sem importar o fluxo de downloads",
             "escopo_e_entrega e modulo puro, isso e propriedade a preservar")

    print()
    print("--- 15. as leituras da planilha nao tem teto de linha ---")
    # A Monitoramento real ja tem 24.334 linhas e a faixa terminava em 20000.
    # A entrega acima disso nao vinha, o ciclo aparecia INCOMPLETO e nada dizia
    # que houve corte.
    for nome in (os.path.join("pages", "3_Financeiro.py"),
                 os.path.join("pages", "2_Monitoramento.py")):
        with open(os.path.join(BASE, nome), encoding="utf-8") as f:
            conferir("ULTIMA_COLUNA_MON}20000" not in f.read(),
                     f"{os.path.basename(nome)} le ate a ultima linha com conteudo")


if __name__ == "__main__":
    print("=" * 74)
    print("  Data de celula se compara como DATA, nunca como texto")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    if falhas:
        print(f"  {len(falhas)} FALHA(S):")
        for f in falhas:
            print(f"    - {f}")
    else:
        print("  PASSOU.")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
