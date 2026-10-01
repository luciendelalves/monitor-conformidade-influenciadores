# -*- coding: utf-8 -*-
"""
Terceiro layout de pastas, para a analista que cobre sozinha a categoria
FUTEBOL, no Drive dela, separado do Drive do Marketing.

POR QUE ESTE TESTE FOI REESCRITO (21/09/2026)

O desenho de 12/09/2026 (pasta do influenciador achada por um mapa
@->apelido, sem bet, sem ano, só "DIVULGAÇÕES / MM. MÊS" dentro dela) foi
SUBSTITUÍDO por decisão do auditor, depois de achar a pasta de teste
compartilhada com pastas de bet (LOTTU, EDS) escritas tanto pela conta da
Responsável A quanto pela da Responsável B: nenhuma das duas estava com o layout futebol
ligado, e a instalação dela nunca chegou a usar o desenho antigo de
verdade.

O NOVO DESENHO: a Responsável B passa a ter uma pasta "Divulgações" própria, e a
partir dela o caminho é O MESMO da Responsável A (bet / mês / @handle / dia /
marcação / tipo), com UMA diferença: SEM O NÍVEL DE ANO. O mês continua na
grafia própria do futebol ("04. ABRIL", maiúscula), confirmado que fica
assim; o resto é literalmente o mesmo código do Marketing.

O que isso muda na prática: a pasta do influenciador volta a ser achada
pelo @, como no Marketing, não mais por um apelido num mapa. O mapa
`pasta_por_handle_futebol.json` e a função `pasta_do_handle_futebol` ficam
sem uso a partir de agora (não foram apagados, só não são mais chamados por
este fluxo).

Este teste não fala com o Drive: a árvore é um dublê, para a regra poder
ser conferida sem tocar em nada real.

    py testes\\teste_pastas_do_futebol.py
"""
import os
import sys
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fluxo_downloads as fluxo

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


# Árvore de mentira, no formato novo: bet direto na raiz ("Divulgações" já
# seria a raiz configurada, então aqui ela nem precisa aparecer, só o que
# fica dentro dela).
ARVORE = {
    "raiz": [{"name": "03. LOTTU", "id": "p_lottu"}],
    "p_lottu": [{"name": "04. ABRIL", "id": "lottu_abril"}],
    "lottu_abril": [{"name": "@rafalirarl", "id": "rafa_pasta"}],
}

criadas = []


def listar(id_pai):
    return list(ARVORE.get(id_pai, []))


def criar(nome, id_pai):
    criadas.append((nome, id_pai))
    novo = f"nova_{len(criadas)}"
    ARVORE.setdefault(id_pai, []).append({"name": nome, "id": novo})
    return novo


def rodar():
    layout_original = fluxo.LAYOUT_PASTAS
    raiz_original = fluxo._pasta_raiz_drive
    try:
        fluxo.LAYOUT_PASTAS = fluxo.LAYOUT_FUTEBOL
        fluxo._pasta_raiz_drive = lambda: "raiz"

        print("--- 1. exige bet, igual ao Marketing (não exigia antes) ---")
        try:
            fluxo.caminho_ate_influenciador("rafalirarl", date(2026, 4, 22), None)
            conferir(False, "deveria ter recusado sem a bet")
        except fluxo.BetNaoInformada:
            conferir(True, "sem marca, recusa com BetNaoInformada")

        print()
        print("--- 2. exige data, igual ao Marketing ---")
        try:
            fluxo.caminho_ate_influenciador("rafalirarl", None, "LOTTU")
            conferir(False, "deveria ter recusado sem a data")
        except fluxo.PastaNaoExisteNoDrive as e:
            conferir("data" in str(e).lower(), "sem data, recusa explicando o motivo",
                     str(e)[:90])

        print()
        print("--- 3. com bet e data, o caminho é [bet, mês futebol, @handle], SEM ANO ---")
        caminho = fluxo.caminho_ate_influenciador("rafalirarl", date(2026, 4, 22), "LOTTU")
        conferir(caminho == ["03. LOTTU", "04. ABRIL", "@rafalirarl"],
                 "bet real, mês na grafia do futebol, @ literal, sem ano no meio",
                 str(caminho))

        print()
        print("--- 4. o mês continua na grafia própria do futebol ---")
        maio = fluxo.caminho_ate_influenciador("rafalirarl", date(2026, 5, 3), "LOTTU")
        conferir(maio[1] == "05. MAIO",
                 "maiúscula, como já era no layout futebol antigo", maio[1])

        print()
        print("--- 5. pastas_dentro_do_influenciador é a MESMA do Marketing agora ---")
        dentro_futebol = fluxo.pastas_dentro_do_influenciador(
            None, date(2026, 4, 22), "STORIES", "link")
        fluxo.LAYOUT_PASTAS = fluxo.LAYOUT_MARKETING
        dentro_marketing = fluxo.pastas_dentro_do_influenciador(
            None, date(2026, 4, 22), "STORIES", "link")
        fluxo.LAYOUT_PASTAS = fluxo.LAYOUT_FUTEBOL
        conferir(dentro_futebol == dentro_marketing,
                 "dia, marcação e tipo saem iguais nos dois layouts agora",
                 f"futebol={dentro_futebol} marketing={dentro_marketing}")
        conferir(dentro_futebol != ["DIVULGAÇÕES", "04. ABRIL"],
                 "e não é mais o desenho antigo (DIVULGAÇÕES + mês, sem mais nada)")

        print()
        print("--- 6. só a bet fica de fora; mês e @handle podem ser criados ---")
        criadas.clear()
        # "05. MAIO" e "@centraldotimao" não existem ainda dentro de LOTTU.
        destino = fluxo.descer_pelo_caminho(
            "raiz", ["03. LOTTU", "05. MAIO", "@centraldotimao"], listar,
            criar=criar, criar_somente_ultimos=2,
            autorizar=fluxo.impedimento_para_criar_pasta)
        conferir(bool(destino) and ("05. MAIO", "p_lottu") in criadas,
                 "cria o mês que faltava", str(criadas))
        conferir(any(n == "@centraldotimao" for n, _pai in criadas),
                 "e cria a pasta do influenciador pelo @, sem mapa nenhum",
                 str(criadas))

        print()
        print("--- 7. a bet nunca é criada, mesmo pedindo ---")
        criadas.clear()
        try:
            fluxo.descer_pelo_caminho(
                "raiz", ["02. ONA", "04. ABRIL", "@fulano"], listar,
                criar=criar, criar_somente_ultimos=2,
                autorizar=fluxo.impedimento_para_criar_pasta)
            conferir(False, "não deveria ter criado a bet")
        except fluxo.PastaNaoExisteNoDrive as e:
            conferir("02. ONA" in str(e), "recusa por faltar a bet, sem criar", str(e)[:90])
        conferir(not criadas, "e não criou nada no caminho", str(criadas))

        print()
        print("--- 8. a conta de níveis criáveis protege só 1 nível (a bet) ---")
        import inspect
        fonte = inspect.getsource(fluxo._pasta_de_destino_drive)
        conferir("len(segmentos) - 1" in fonte,
                 "o layout futebol calcula pelo tamanho do caminho menos 1, "
                 "não mais um número fixo pensado para 3 níveis")

        print()
        print("--- 9. o rótulo da raiz nas mensagens diz \"Divulgações\" ---")
        import re
        achou_rotulo = re.search(r'else\s+"Divulgações"', open(
            os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8").read())
        conferir(bool(achou_rotulo),
                 "existe um rótulo \"Divulgações\" no código, para as mensagens de erro")

    finally:
        fluxo.LAYOUT_PASTAS = layout_original
        fluxo._pasta_raiz_drive = raiz_original


if __name__ == "__main__":
    print("=" * 74)
    print("  Pastas do layout futebol: mesmo caminho da Responsável A, sem ano (21/09/2026)")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
