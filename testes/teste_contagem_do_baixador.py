# -*- coding: utf-8 -*-
"""
Prova que a contagem de downloads do dia não se perde.

POR QUE ESTE TESTE EXISTE (30/08/2026)

O contador é o que vai dizer, depois de alguns dias de uso real, qual teto
diário faz sentido para a conta de cada pessoa. Hoje o teto está desligado
justamente porque o número anterior tinha sido escolhido no chute.

No primeiro uso real ele mentiu: dizia 2 quando o uso do dia tinha sido 4. A
causa foi um arquivo gravado por fora do programa, que ganhou uma marca
invisível no começo; a leitura falhou e o programa recomeçou do zero SEM
AVISAR.

Contador que se reinicia em silêncio é pior que contador nenhum: ele
subestima o uso, e subestimar uso é exatamente como se marca uma conta.

    py testes\teste_contagem_do_baixador.py
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "baixador_local"))

import baixador

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def escrever(conteudo, com_marca=False):
    """Grava o arquivo de contagem, opcionalmente com a marca invisível que o
    PowerShell e o Bloco de Notas acrescentam."""
    dados = conteudo.encode("utf-8")
    if com_marca:
        dados = b"\xef\xbb\xbf" + dados
    with open(baixador.ARQUIVO_CONTAGEM, "wb") as f:
        f.write(dados)


def rodar():
    hoje = datetime.now().strftime("%Y-%m-%d")
    baixador.ARQUIVO_CONTAGEM = os.path.join(tempfile.mkdtemp(), "contagem.json")

    print("--- 1. sem arquivo, começa do zero ---")
    conferir(baixador._ler_contagem()["baixados"] == 0, "começa em zero")

    print()
    print("--- 2. soma entre execuções, no mesmo dia ---")
    escrever(json.dumps({"dia": hoje, "baixados": 7}))
    lido = baixador._ler_contagem()
    conferir(lido["baixados"] == 7, "recupera o que já tinha sido contado", str(lido))
    lido["baixados"] += 1
    baixador._gravar_contagem(lido)
    conferir(baixador._ler_contagem()["baixados"] == 8,
             "somou em cima, em vez de recomeçar")

    print()
    print("--- 3. arquivo com a marca invisível NÃO zera ---")
    escrever(json.dumps({"dia": hoje, "baixados": 12}), com_marca=True)
    lido = baixador._ler_contagem()
    conferir(lido["baixados"] == 12,
             "leu apesar da marca deixada por editor de texto", str(lido))

    print()
    print("--- 4. dia novo recomeça, e isso é o certo ---")
    ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    escrever(json.dumps({"dia": ontem, "baixados": 30}))
    conferir(baixador._ler_contagem()["baixados"] == 0,
             "contagem de ontem não conta para hoje")

    print()
    print("--- 5. arquivo corrompido avisa, em vez de mentir calado ---")
    escrever("isto não é json")
    avisos = []
    original = baixador.dizer
    baixador.dizer = lambda m="": avisos.append(m)
    try:
        lido = baixador._ler_contagem()
    finally:
        baixador.dizer = original
    conferir(lido["baixados"] == 0, "recomeça do zero, que é o único caminho possível")
    conferir(any("AVISO" in a for a in avisos),
             "mas AVISA que o número vai ficar menor que o uso real",
             str(avisos))


if __name__ == "__main__":
    print("=" * 70)
    print("  Contagem de downloads do dia")
    print("=" * 70)
    print()
    rodar()
    print()
    print("=" * 70)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 70)
    sys.exit(1 if falhas else 0)
