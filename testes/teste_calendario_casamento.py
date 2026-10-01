# -*- coding: utf-8 -*-
"""
Prova como o programa acha a linha certa no Calendário do Marketing.

POR QUE ESTE TESTE EXISTE (11/09/2026)

Medido nas abas AGO.26 e SET.26, 1.984 linhas reais, antes de desenhar:

  - o handle é escrito de qualquer jeito: com e sem @, com espaço no fim
    ("nathanqueiroz  "), em maiúscula ("@Giroquue")
  - a marca muda de aba para aba: agosto escreve EDSCAP, setembro EDS CAP
  - a chave (handle, marca, data) REPETE em cerca de 3% das linhas, sempre
    duas vezes, e é justamente quem posta dois stories no mesmo dia
    (andersonneiff, eduardagutierrez, weslleyof_)

A REGRA QUE SAI DISSO: entre as linhas que casam, escrever na primeira que
ainda está com Status vazio. Assim o primeiro story cai na primeira linha e o
segundo na segunda, sem o programa precisar saber qual é qual.

Nada aqui fala com o Google: são listas de mentira, no mesmo formato que a API
devolve.

    py testes\\teste_calendario_casamento.py
"""
import datetime
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def linha(handle, marca, data, status="", jogo="", horario="", monitorado=""):
    """Uma linha no formato que o Sheets devolve: lista de textos, A a I."""
    return [handle, marca, "Responsável", jogo, status, data, horario,
            monitorado, ""]


def rodar():
    import calendario_divulgacoes as cal

    print("--- 1. normalização do handle, com os casos reais da planilha ---")
    for bruto in ("@Giroquue", "giroquue", "  giroquue  ", "@giroquue"):
        conferir(cal.normalizar_handle(bruto) == "giroquue",
                 f"{bruto!r} vira 'giroquue'", cal.normalizar_handle(bruto))
    conferir(cal.normalizar_handle("nathanqueiroz  ") == "nathanqueiroz",
             "espaço no fim não atrapalha")

    print()
    print("--- 2. normalização da marca resolve EDSCAP x EDS CAP ---")
    conferir(cal.normalizar_marca("EDS CAP") == cal.normalizar_marca("EDSCAP"),
             "as duas grafias viram a mesma coisa",
             f"{cal.normalizar_marca('EDS CAP')} x {cal.normalizar_marca('EDSCAP')}")
    conferir(cal.normalizar_marca(" lottu ") == "LOTTU", "e a caixa não importa")

    print()
    print("--- 3. a aba sai do mês da postagem ---")
    for data, esperado in ((datetime.date(2026, 9, 11), "SET.26"),
                           (datetime.date(2026, 8, 1), "AGO.26"),
                           (datetime.date(2025, 12, 31), "DEZ.25"),
                           (datetime.date(2026, 1, 5), "JAN.26")):
        conferir(cal.aba_do_mes(data) == esperado,
                 f"{data:%d/%m/%Y} é {esperado}", cal.aba_do_mes(data))
    conferir(cal.aba_do_mes(None) is None, "sem data, sem aba")

    print()
    print("--- 4. acha a linha, com o handle escrito diferente ---")
    linhas = [
        linha("@Giroquue", "EDS CAP", "11/09/2026"),
        linha("outrapessoa", "LOTTU", "11/09/2026"),
    ]
    n, motivo = cal.achar_linha(linhas, "giroquue", "EDSCAP",
                                datetime.date(2026, 9, 11))
    conferir(n == 3, "achou na primeira linha de dados, que é a 3", f"{n} {motivo}")

    print()
    print("--- 5. duas linhas iguais: preenche na ordem ---")
    # O caso do auditor: dois stories do mesmo influenciador, mesma marca,
    # mesmo dia. A planilha tem duas linhas, preenchidas em sequência.
    linhas = [
        linha("andersonneiff", "LOTTU", "11/09/2026", status="Publicada"),
        linha("andersonneiff", "LOTTU", "11/09/2026"),
    ]
    n, motivo = cal.achar_linha(linhas, "andersonneiff", "LOTTU",
                                datetime.date(2026, 9, 11))
    conferir(n == 4,
             "pula a que já tem Status e vai para a segunda", f"{n} {motivo}")

    print()
    print("--- 6. todas preenchidas: avisa, e não sobrescreve ---")
    linhas = [
        linha("andersonneiff", "LOTTU", "11/09/2026", status="Publicada"),
        linha("andersonneiff", "LOTTU", "11/09/2026", status="Não Postada"),
    ]
    n, motivo = cal.achar_linha(linhas, "andersonneiff", "LOTTU",
                                datetime.date(2026, 9, 11))
    conferir(n is None, "não devolve linha", str(n))
    conferir("já estão preenchidas" in motivo,
             "e o motivo diz que as linhas já estão preenchidas", motivo)

    print()
    print("--- 7. nenhuma linha casa: avisa o que procurou ---")
    linhas = [linha("outrapessoa", "LOTTU", "11/09/2026")]
    n, motivo = cal.achar_linha(linhas, "giroquue", "LOTTU",
                                datetime.date(2026, 9, 11))
    conferir(n is None, "não inventa linha", str(n))
    conferir("giroquue" in motivo, "e diz de quem estava procurando", motivo)

    print()
    print("--- 8. a data é comparada como DATA, não como texto ---")
    # 06/09/2026 gravado no Sheets volta como "06/09/26". Comparar texto faria
    # o casamento falhar em silêncio. Ver data_de_planilha.py.
    linhas = [linha("giroquue", "LOTTU", "06/09/26")]
    n, _ = cal.achar_linha(linhas, "giroquue", "LOTTU",
                           datetime.date(2026, 9, 6))
    conferir(n == 3, "ano com dois dígitos casa com a mesma data", str(n))
    n, _ = cal.achar_linha(linhas, "giroquue", "LOTTU",
                           datetime.date(2026, 9, 7))
    conferir(n is None, "e dia diferente não casa", str(n))

    print()
    print("--- 9. marca diferente NÃO casa, mesmo no mesmo dia ---")
    # Medido na planilha real: o mesmo influenciador aparece no mesmo dia com
    # marcas diferentes (@giroquue em EDS CAP e em LOTTU). Sem a marca na
    # chave, a entrega de uma marca iria para a linha da outra.
    linhas = [
        linha("giroquue", "EDS CAP", "11/09/2026"),
        linha("giroquue", "LOTTU", "11/09/2026"),
    ]
    n, _ = cal.achar_linha(linhas, "giroquue", "LOTTU",
                           datetime.date(2026, 9, 11))
    conferir(n == 4, "vai para a linha da marca certa, e não para a primeira",
             str(n))

    print()
    print("--- 10. os apelidos saem da própria planilha ---")
    linhas = [
        linha("a", "LOTTU", "11/09/2026", monitorado="Responsável F"),
        linha("b", "LOTTU", "11/09/2026", monitorado="Responsável G"),
        linha("c", "LOTTU", "11/09/2026", monitorado=""),
    ]
    apelidos = cal.apelidos_conhecidos(linhas)
    conferir("responsável f" in apelidos and "responsável g" in apelidos,
             "lê o vocabulário de quem monitora da coluna deles",
             str(sorted(apelidos)))
    conferir("" not in apelidos, "e vazio não vira apelido")

    print()
    print("--- 11. linha curta não estoura ---")
    # O Sheets devolve a linha CORTADA quando as últimas células estão vazias,
    # então linha de 3 itens é normal e não é defeito.
    n, _ = cal.achar_linha([["giroquue", "LOTTU"]], "giroquue", "LOTTU",
                           datetime.date(2026, 9, 11))
    conferir(n is None, "linha sem data simplesmente não casa", str(n))
    conferir(cal.apelidos_conhecidos([["giroquue"]]) == set(),
             "e a leitura de apelidos aguenta linha curta")

    print()
    print("--- 12. não importa fluxo_downloads no topo ---")
    # Importação nos dois sentidos com uma delas no topo é ciclo esperando
    # para acontecer. O fluxo_downloads importa este módulo dentro das funções.
    fonte = open(os.path.join(BASE, "calendario_divulgacoes.py"),
                 encoding="utf-8").read()
    topo = fonte.split("def ")[0]
    conferir("import fluxo_downloads" not in topo,
             "o import fica dentro das funções que precisam dele",
             "no topo, criaria importação circular com fluxo_downloads")


if __name__ == "__main__":
    print("=" * 74)
    print("  Achar a linha certa no Calendário")
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
