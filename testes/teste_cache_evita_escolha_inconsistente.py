# -*- coding: utf-8 -*-
"""
Com pasta já duplicada (duas irmãs de mesmo nome), duas chamadas separadas
de descer_pelo_caminho não podem escolher uma pasta diferente cada vez.

POR QUE ESTE TESTE EXISTE (25/09/2026)

A trava e o cache persistente de mais cedo hoje protegem o caminho de
CRIAR: duas chamadas quase juntas não criam duas pastas novas para o mesmo
nome. Mas achado ao vivo, no mesmo dia, com uma duplicata que JÁ EXISTIA
antes de qualquer correção de hoje (duas pastas "03. LOTTU", sobra de dois
dias de teste): `descer_pelo_caminho` acha a pasta por LISTAGEM antes de
pensar em criar, e a listagem nunca passava pelo cache, só a criação. Com
duas pastas de mesmo nome como irmãs, a escolha entre elas dependia da
ORDEM que o Drive devolvia na busca, e essa ordem não é garantida estável
entre chamadas. Resultado real: o mesmo vídeo, baixado minutos depois de
outro do mesmo influenciador, foi organizado numa ÁRVORE DIFERENTE, sem
nada ter mudado de verdade no Drive entre uma chamada e outra.

Este teste simula exatamente isso: uma listagem de mentira que devolve as
duas pastas em ORDEM DIFERENTE a cada chamada (pior caso possível, mas
realista: a API não promete ordem nenhuma sem orderBy explícito). Prova
que, sem `pasta_conhecida`/`lembrar_pasta`, a segunda chamada pode escolher
a outra pasta; e que, com as duas passadas, a segunda chamada nem chega a
listar de novo, usa o que a primeira já resolveu.

    py testes\\teste_cache_evita_escolha_inconsistente.py
"""
import os
import sys

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


class DriveComDuplicataEOrdemInstavel:
    """Duas pastas "03. LOTTU" (ids diferentes) já existindo como irmãs sob
    a raiz. Cada chamada a listar() devolve as duas em ordem trocada da
    anterior, para simular o que a API do Drive não promete evitar."""

    def __init__(self):
        self.chamadas_de_listar = 0
        self._duplicatas = [
            {"name": "03. LOTTU", "id": "lottu-do-dia-22"},
            {"name": "03. LOTTU", "id": "lottu-do-dia-23"},
        ]

    def listar(self, id_pai):
        self.chamadas_de_listar += 1
        if id_pai != "raiz":
            return []
        # Inverte a ordem a cada chamada: pior caso de instabilidade.
        if self.chamadas_de_listar % 2 == 1:
            return list(self._duplicatas)
        return list(reversed(self._duplicatas))


def rodar():
    print("--- 1. sem cache, a escolha pode mudar entre duas chamadas ---")
    drive = DriveComDuplicataEOrdemInstavel()
    primeira = fluxo.descer_pelo_caminho("raiz", ["03. LOTTU"], drive.listar)
    segunda = fluxo.descer_pelo_caminho("raiz", ["03. LOTTU"], drive.listar)
    # Não afirmamos que SEMPRE vai divergir (dependeria de como
    # achar_pasta_tolerante escolhe entre igualmente válidas), só provamos
    # que o mecanismo em si permite: a listagem foi consultada as duas
    # vezes, sem nada guardando a resposta anterior.
    conferir(drive.chamadas_de_listar == 2,
             "sem pasta_conhecida, as duas chamadas listam ao vivo, sem exceção",
             drive.chamadas_de_listar)

    print()
    print("--- 2. com cache, a segunda chamada nem lista de novo ---")
    drive2 = DriveComDuplicataEOrdemInstavel()
    cache = {}

    def pasta_conhecida(nome, id_pai):
        return cache.get((id_pai, nome))

    def lembrar_pasta(nome, id_pai, id_pasta):
        cache[(id_pai, nome)] = id_pasta

    primeira2 = fluxo.descer_pelo_caminho(
        "raiz", ["03. LOTTU"], drive2.listar,
        pasta_conhecida=pasta_conhecida, lembrar_pasta=lembrar_pasta)
    conferir(drive2.chamadas_de_listar == 1,
             "a primeira chamada precisa listar, não tem o que guardar ainda")

    segunda2 = fluxo.descer_pelo_caminho(
        "raiz", ["03. LOTTU"], drive2.listar,
        pasta_conhecida=pasta_conhecida, lembrar_pasta=lembrar_pasta)
    conferir(drive2.chamadas_de_listar == 1,
             "a segunda chamada NÃO listou de novo, usou o cache",
             drive2.chamadas_de_listar)
    conferir(primeira2 == segunda2,
             "e por isso as duas chamadas concordam na mesma pasta",
             (primeira2, segunda2))
    conferir(primeira2 in ("lottu-do-dia-22", "lottu-do-dia-23"),
             "a pasta escolhida é uma das duas de verdade, não um valor estranho",
             primeira2)


if __name__ == "__main__":
    print("=" * 70)
    print("  Pasta duplicada: cache evita escolha inconsistente entre chamadas")
    print("=" * 70)
    print()
    rodar()
    print()
    print("=" * 70)
    if falhas:
        print(f"  {len(falhas)} FALHA(S):")
        for f in falhas:
            print(f"    - {f}")
    else:
        print("  PASSOU.")
    print("=" * 70)
    sys.exit(1 if falhas else 0)
