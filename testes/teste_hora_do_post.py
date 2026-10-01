# -*- coding: utf-8 -*-
"""
Prova que a hora da postagem para de ser descartada, e chega em horário de
Brasília.

POR QUE ESTE TESTE EXISTE (11/09/2026)

O Calendário de Divulgações do Marketing tem coluna de Horário, e o auditor
perguntou se dava para estimar. Não precisa estimar: o Instagram já manda a
hora exata, e o programa jogava fora, ficando só com a data, em três lugares
(`item.date_utc.date()`, `post.date_utc.date()` e
`datetime.fromtimestamp(...).date()`).

O CUIDADO QUE ESTE TESTE PROTEGE: `date_utc` é UTC. Escrever direto na planilha
sairia 3 horas adiantado, e ninguém percebe olhando a tela, porque 22:17 e
19:17 são igualmente plausíveis para um story.

    py testes\\teste_hora_do_post.py
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


def rodar():
    import fluxo_downloads as fluxo

    print("--- 1. UTC vira horário de Brasília ---")
    # 02/08/2026 às 01:17 UTC é 01/08/2026 às 22:17 em Brasília. O DIA muda, e
    # é por isso que a conversão não é enfeite.
    utc = datetime.datetime(2026, 8, 2, 1, 17, tzinfo=datetime.timezone.utc)
    aqui = fluxo.hora_de_brasilia(utc)
    conferir(aqui is not None, "converte em vez de devolver nada")
    conferir(aqui.hour == 22 and aqui.minute == 17,
             "a hora bate com o horário de Brasília", str(aqui))
    conferir(aqui.day == 1,
             "e o DIA volta para o anterior, quando é o caso", str(aqui))

    print()
    print("--- 2. sem hora, devolve None em vez de inventar ---")
    conferir(fluxo.hora_de_brasilia(None) is None,
             "None entra, None sai",
             "inventar meia-noite faria a planilha afirmar algo que ninguém mediu")

    print()
    print("--- 3. hora que já vem sem fuso é tratada como UTC ---")
    # O instaloader entrega `date_utc` sem informação de fuso colada. Tratar
    # como horário local faria a conversão acontecer duas vezes, ou nenhuma,
    # dependendo da máquina.
    ingenua = datetime.datetime(2026, 8, 2, 1, 17)
    conferir(fluxo.hora_de_brasilia(ingenua).hour == 22,
             "sem fuso declarado, assume UTC",
             str(fluxo.hora_de_brasilia(ingenua)))

    print()
    print("--- 4. baixar_video carrega a hora até quem chamou ---")
    import inspect
    fonte = inspect.getsource(fluxo.baixar_video)
    conferir("hora_post" in fonte,
             "o caminho de download carrega a hora",
             "sem isso a coluna Horário do Calendário fica vazia para sempre")

    print()
    print("--- 5. os três lugares que cortavam a hora foram corrigidos ---")
    inteiro = open(os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8").read()
    conferir("item.date_utc.date(), handle" not in inteiro,
             "o caminho de story não corta mais a hora ali")
    conferir(inteiro.count("hora_de_brasilia(") >= 3,
             "e os três caminhos passam pela conversão",
             f"achei {inteiro.count('hora_de_brasilia(')} usos")

    print()
    print("--- 6. o fuso está escrito como -3, e não vem de biblioteca ---")
    # O Brasil não tem horário de verão desde 2019. Depender de base de fusos
    # do sistema seria mais uma coisa para faltar na máquina nova da analista.
    # PROCURA O USO, E NÃO A PALAVRA. A primeira versão desta linha proibia
    # "zoneinfo" no arquivo inteiro, e reprovava o próprio comentário que
    # explica por que não usamos zoneinfo. É o mesmo tropeço já registrado na
    # seção 6 de teste_link_de_story_sem_numero.py.
    conferir("import zoneinfo" not in inteiro and "from zoneinfo" not in inteiro,
             "não importa zoneinfo, que é dependência a mais para instalar")
    conferir(getattr(fluxo, "FUSO_DE_BRASILIA", None) is not None,
             "e o fuso é declarado num lugar só, com nome")


if __name__ == "__main__":
    print("=" * 74)
    print("  A hora da postagem")
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
