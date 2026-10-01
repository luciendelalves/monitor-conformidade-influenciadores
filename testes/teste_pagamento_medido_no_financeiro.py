# -*- coding: utf-8 -*-
"""
O Financeiro MOSTRA o pagamento post a post que já está na Monitoramento, sem
decidir nada com ele.

POR QUE ESTE ARQUIVO EXISTE (04/09/2026)

Pedido do auditor: ligar a correção de pagamento do Monitoramento (ver
teste_corrigir_pagamento.py) à aba Financeiro. Duas formas foram propostas:

    1. o Financeiro MOSTRA quantas linhas do ciclo estão como pago/pendente na
       Monitoramento, ao lado da decisão de quem fecha
    2. essa decisão SOME, e o fechamento decide sozinho a partir da
       Monitoramento

Resposta dele: "a primeira mesmo". Este teste prova que é isso que está
implementado: a contagem aparece, e continua sendo só leitura, mostrada para
quem fecha ver, sem virar a resposta de nada sozinha.

REVISADO EM 09/09/2026: o "rádio que já existe" da versão original deste
teste era "Este ciclo já foi pago?", removido no mesmo dia (ver o docstring de
pages/3_Financeiro.py). O que ficou de pé, e que este teste ainda prova, é
que a contagem post a post nunca decidiu nada sozinha, agora nem tem mais um
rádio ao lado para ser confundida com.

Rodar:

    py testes\teste_pagamento_medido_no_financeiro.py
"""
import os
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
    pagina = os.path.join(BASE, "pages", "3_Financeiro.py")
    with open(pagina, encoding="utf-8") as f:
        fonte = f.read()
    codigo = "\n".join(l for l in fonte.splitlines()
                       if not l.strip().startswith("#"))

    print("--- 1. a leitura da Monitoramento traz o PAGAMENTO da linha ---")
    conferir('"pagamento": campo(linha, "pagamento")' in codigo,
             "carregar() lê a coluna pagamento de cada linha",
             "sem isso não há o que contar")

    print()
    print("--- 2. a contagem é mostrada, sobre as linhas do ciclo escolhido ---")
    pos_contagem = fonte.find("_contagem_pagamento")
    conferir(pos_contagem != -1, "a contagem existe na tela")
    conferir("collections.Counter" in codigo,
             "conta de verdade os valores que existem, sem supor vocabulário "
             "fixo (PAGO/NÃO PAGO): se o Marketing escrever \"Pendente\", a "
             "contagem mostra \"Pendente\"")
    conferir('contagem["linhas"]' in fonte.split("_contagem_pagamento")[1][:200],
             "a contagem é sobre as linhas do CICLO escolhido, não da "
             "planilha inteira")

    print()
    print("--- 3. a contagem NÃO decide nada, e a tela avisa isso ---")
    # REVISADO EM 09/09/2026: não há mais um rádio de decisão para a contagem
    # pré-marcar; o que sobrou para provar é que o texto ao lado da contagem
    # continua avisando, por escrito, que ela é só leitura.
    conferir("não decide a solicitação abaixo" in fonte
             or "não decide" in fonte,
             "e o texto ao lado da contagem avisa isso para quem lê a tela")
    conferir("SITUACOES_DE_PAGAMENTO" not in codigo,
             "o vocabulário de pagamento do ciclo (NÃO PAGO/PARCIAL/PAGO) "
             "saiu junto com o rádio que ele alimentava",
             "ver o docstring do módulo, revisão de 09/09/2026")


if __name__ == "__main__":
    print("=" * 74)
    print("  O Financeiro mostra o pagamento da Monitoramento, sem decidir com ele")
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
