# -*- coding: utf-8 -*-
"""
Prova que o campo Jogo entra na fila SEM deslocar as colunas antigas.

POR QUE ESTE TESTE EXISTE (11/09/2026)

O Calendário de Divulgações do Marketing tem uma coluna Jogo (o que a peça
divulga: CHUTE PREMIADO + AVIATOR, Mega Odds, Jogo do Chapéu). Reconhecer isso
por visão foi descartado pelo auditor: vira campo digitado na tela, junto com o
link, e viaja na linha da fila até a escrita no Calendário.

O RISCO QUE ESTE TESTE PROTEGE: a fila é uma planilha que já tem linhas
gravadas. Coluna nova no MEIO desloca tudo o que já está lá, em silêncio, e o
sintoma aparece longe da causa (um link virando marca, uma marca virando
ciclo). A coluna nova tem que entrar no FIM, como a `quem_pediu` entrou em
02/09/2026.

    py testes\\teste_campo_jogo_na_fila.py
"""
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


def rodar():
    import fluxo_downloads as fluxo

    print("--- 1. as colunas antigas continuam onde estavam ---")
    ANTIGAS = {"influenciador": 0, "link": 1, "status": 2, "ciclo": 3,
               "marca": 4, "marcacao": 5, "quem_pediu": 6}
    for nome, posicao in ANTIGAS.items():
        conferir(fluxo.COL_FILA[nome] == posicao,
                 f"{nome} continua na posição {posicao}",
                 str(fluxo.COL_FILA.get(nome)))

    print()
    print("--- 2. o jogo entrou no FIM ---")
    conferir(fluxo.COL_FILA["jogo"] == 7,
             "jogo é a coluna H", str(fluxo.COL_FILA.get("jogo")))
    conferir(fluxo.ULTIMA_COLUNA_FILA == "H",
             "e a leitura da fila vai até H", fluxo.ULTIMA_COLUNA_FILA)
    conferir(fluxo.letra_da_coluna_fila("jogo") == "H",
             "a letra calculada bate com a coluna",
             fluxo.letra_da_coluna_fila("jogo"))

    print()
    print("--- 3. a linha nova leva o jogo, na posição certa ---")
    # Exercita adicionar_na_fila de verdade, com a planilha dublada, para
    # provar a POSIÇÃO do valor na linha, e não só o dicionário de colunas.
    import types
    gravadas = []
    falso = types.ModuleType("sheets_client")
    falso.adicionar_linhas = lambda pid, aba, faixa, linhas: gravadas.extend(linhas)
    antigo = sys.modules.get("sheets_client")
    guardado = (fluxo.ler_fila, fluxo._planilha_fila_id)
    try:
        sys.modules["sheets_client"] = falso
        fluxo.ler_fila = lambda: []
        fluxo._planilha_fila_id = lambda: "planilha_de_mentira"
        fluxo.adicionar_na_fila([("", "https://www.instagram.com/stories/x/1/",
                                  "Ciclo 2", "LOTTU", "", "Responsável E",
                                  "CHUTE PREMIADO + AVIATOR")])
        conferir(len(gravadas) == 1, "gravou uma linha", str(gravadas))
        linha = gravadas[0] if gravadas else []
        conferir(len(linha) == 8, "com oito colunas", str(len(linha)))
        conferir(linha[fluxo.COL_FILA["jogo"]] == "CHUTE PREMIADO + AVIATOR",
                 "e o jogo na coluna do jogo", str(linha))
        conferir(linha[fluxo.COL_FILA["quem_pediu"]] == "Responsável E",
                 "sem empurrar quem pediu para o lado", str(linha))
        conferir(linha[fluxo.COL_FILA["marca"]] == "LOTTU",
                 "nem a marca", str(linha))
    finally:
        fluxo.ler_fila, fluxo._planilha_fila_id = guardado
        if antigo is not None:
            sys.modules["sheets_client"] = antigo
        else:
            sys.modules.pop("sheets_client", None)

    print()
    print("--- 4. quem não digita jogo não quebra nada ---")
    # A chamada com seis itens é a que existia antes desta mudança, e continua
    # valendo: o jogo é opcional.
    gravadas.clear()
    antigo = sys.modules.get("sheets_client")
    guardado = (fluxo.ler_fila, fluxo._planilha_fila_id)
    try:
        sys.modules["sheets_client"] = falso
        fluxo.ler_fila = lambda: []
        fluxo._planilha_fila_id = lambda: "planilha_de_mentira"
        fluxo.adicionar_na_fila([("", "https://www.instagram.com/stories/y/2/",
                                  "", "EDS", "", "Responsável E")])
        linha = gravadas[0] if gravadas else []
        conferir(len(linha) == 8, "a linha continua com oito colunas",
                 str(len(linha)))
        conferir(linha[fluxo.COL_FILA["jogo"]] == "",
                 "e o jogo fica vazio, não None nem 'None'", repr(linha[7]))
    finally:
        fluxo.ler_fila, fluxo._planilha_fila_id = guardado
        if antigo is not None:
            sys.modules["sheets_client"] = antigo
        else:
            sys.modules.pop("sheets_client", None)

    print()
    print("--- 5. a leitura da fila devolve o jogo ---")
    import inspect
    fonte = inspect.getsource(fluxo.ler_fila)
    conferir('jogo=pega("jogo")' in fonte,
             "ler_fila entrega o jogo para quem processa",
             "sem isto o valor fica na planilha e nunca chega ao Calendário")

    print()
    print("--- 6. a tela manda o jogo junto com o link ---")
    caminho = os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py")
    tela = open(caminho, encoding="utf-8").read()
    conferir("jogo_novo" in tela, "a tela tem o campo do jogo")
    conferir("identidade.quem_sou_eu(), jogo_novo" in tela,
             "e ele vai na chamada da fila, depois de quem pediu",
             "fora de ordem, o jogo entraria na coluna de outra coisa")


if __name__ == "__main__":
    print("=" * 74)
    print("  O campo Jogo na fila")
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
