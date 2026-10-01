# -*- coding: utf-8 -*-
"""
O CSS da identidade visual nao mira elemento por POSICAO.

POR QUE ESTE TESTE EXISTE (08/09/2026)

O proprio estilo.py avisa, na primeira linha do docstring dele: "o CSS aqui e
deliberadamente contido. Streamlit muda a estrutura interna das telas entre
versoes, entao quanto mais o estilo depende de detalhe interno, mais ele quebra
numa atualizacao".

O aviso foi desrespeitado no mesmo dia em que a tela foi reformada, e o defeito
apareceu na tela na hora. A regra escrita foi:

    [data-testid="stProgress"] > div > div { height: 5px; }

A intencao era afinar a barra de progresso. Lendo o codigo do proprio Streamlit
(static/Progress.*.js), o DOM e:

    div[data-testid="stProgress"]
      div            <- envolve o ROTULO, com paddingBottom de tema
        div          <- o markdown do texto
      ProgressBar
        div[data-testid="stProgressBarTrack"]   <- a barra de verdade

Ou seja, "> div > div" acertou o conteiner do TEXTO e achatou ele em 5px. O
resultado na tela: a frase "100% do que tem video ja validado" transbordou da
caixa e a barra ciano foi desenhada por cima dela. De quebra, o paddingBottom
que separava rotulo e barra foi destruido.

A CORRECAO NAO E "ajustar o numero de divs". Contar filhos e justamente o que
quebra na atualizacao seguinte. A correcao e mirar o testid nomeado, que e o
que as outras vinte regras do arquivo ja fazem.

Este teste trava a CLASSE do defeito, nao o caso.

    py testes\teste_estilo_nao_usa_seletor_posicional.py
"""
import os
import re
import sys

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
    import estilo

    # MEDE O CSS QUE E INJETADO, NAO A PROSA DO ARQUIVO. A primeira versao
    # deste teste leu o texto do arquivo inteiro e reprovou por causa do
    # proprio comentario que documenta o defeito: a convencao da casa e deixar
    # a versao errada escrita ao lado da correta, para ninguem reintroduzir.
    # Comentario de CSS sai antes da leitura, senao documentar o erro passa a
    # contar como comete-lo.
    fonte = re.sub(r"/\*.*?\*/", "", estilo._CSS, flags=re.DOTALL)

    print("--- 1. nenhum seletor desce por posicao a partir de um testid ---")
    # Procura padroes como `[data-testid="X"] > div > div` ou `... div > div`.
    # Um nivel ainda e defensavel em alguns casos; DOIS niveis de div anonima e
    # contar a estrutura interna do Streamlit, que muda sem avisar.
    posicionais = re.findall(r"\[data-testid=\"[^\"]+\"\][^{;\n]*>\s*div\s*>\s*div",
                             fonte)
    conferir(not posicionais,
             "nenhuma regra desce dois niveis de div anonima",
             f"achei {posicionais}")

    print()
    print("--- 2. a barra de progresso e mirada pelo nome dela ---")
    # stProgressBarTrack existe no Streamlit 1.59.2, conferido no JS estatico.
    # Se um dia sair, este teste falha e alguem confere de novo, em vez de a
    # tela quebrar em silencio.
    if "stProgress" in fonte:
        conferir("stProgressBarTrack" in fonte,
                 "a barra e mirada por stProgressBarTrack",
                 "mirar stProgress e descer por div acerta o rotulo, nao a barra")

    print()
    print("--- 3. o testid existe no Streamlit instalado ---")
    # Regra que mira nome inexistente nao quebra nada, mas tambem nao faz nada,
    # e fica no arquivo parecendo que funciona.
    import streamlit
    estatico = os.path.join(os.path.dirname(streamlit.__file__), "static")
    usados = set(re.findall(r"\[data-testid=\"(st[A-Za-z]+)\"\]", fonte))
    conferir(bool(usados), f"o arquivo mira {len(usados)} testid(s)")

    presentes = set()
    if os.path.isdir(estatico):
        for pasta, _d, arqs in os.walk(estatico):
            for a in arqs:
                try:
                    bruto = open(os.path.join(pasta, a), "rb").read()
                except Exception:
                    continue
                for nome in usados:
                    if nome.encode() in bruto:
                        presentes.add(nome)
    # NAO PROIBE mirar nome inexistente, EXIGE que se saiba qual e. Em grupo de
    # seletor a redundancia protege contra renomeacao, e o arquivo ja faz isso
    # de proposito com stMainBlockContainer e .block-container. O defeito real e
    # ninguem saber qual regra esta inativa, entao a lista tem de estar escrita.
    import estilo
    declarados = set(getattr(estilo, "TESTIDS_INATIVOS", set()))
    ausentes = sorted(usados - presentes - declarados)
    conferir(not ausentes,
             "todo testid ausente do Streamlit esta declarado como inativo",
             f"nao achei no Streamlit e nao esta em estilo.TESTIDS_INATIVOS: "
             f"{ausentes}")
    # E o inverso: nome declarado inativo que voltou a existir tem de sair da
    # lista, senao ela passa a mentir na direcao oposta.
    ressuscitados = sorted(declarados & presentes)
    conferir(not ressuscitados,
             "e nenhum declarado inativo voltou a existir sem sair da lista",
             f"existem no Streamlit agora: {ressuscitados}")


if __name__ == "__main__":
    print("=" * 74)
    print("  O CSS nao mira elemento por posicao")
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
