# -*- coding: utf-8 -*-
"""
A fricção do "Baixar de novo" numa linha já concluída precisa acontecer de
verdade, não só existir no código.

POR QUE ESTE TESTE EXISTE (23/09/2026)

O auditor perguntou se um download de vídeo já marcado "BAIXADO E
ORGANIZADO" era bug. Era: `e_status_sucesso` comparava o status da fila com
"OK", que é o vocabulário do LOG de fluxo (log_fluxo_completo.csv), não da
fila. A ÚNICA gravação de sucesso na fila, em todo o arquivo, escreve
"BAIXADO E ORGANIZADO" (conferido em 23/09/2026 contra a fila real: 14
linhas, todas com esse texto). Com a comparação errada, `e_status_sucesso`
nunca reconhecia sucesso nenhum, em nenhuma das QUATRO chamadas dela em
pages/1_Downloads_e_Organizacao.py.

O QUE ISSO SIGNIFICAVA NA PRÁTICA: o pedido do Marketing no go live foi
"impedir novos downloads de links já processados com sucesso", exigindo
motivo escrito e papel de supervisão ou coordenação. A fricção existia,
escrita, revisada, com comentário explicando o cuidado. E nunca acontecia:
qualquer pessoa clicava "Baixar de novo" numa linha já concluída sem digitar
motivo nenhum, porque a checagem que deveria exigir isso sempre concluía
"isto não é um sucesso".

Este é o tipo de defeito que FALHA EM SILÊNCIO: não dá erro, não aparece
aviso, o botão simplesmente funciona mais fácil do que devia. Só apareceu
porque alguém reparou que um vídeo já baixado foi baixado de novo sem
pedir explicação.

Não fala com o Google: só confere a função e o código-fonte da tela.

    py testes\\teste_reconhece_status_de_sucesso_na_fila.py
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


def rodar():
    print("--- 1. reconhece o ÚNICO texto de sucesso que a fila grava ---")
    conferir(fluxo.e_status_sucesso("BAIXADO E ORGANIZADO") is True,
             "'BAIXADO E ORGANIZADO' é reconhecido como sucesso",
             "é a única gravação de sucesso em todo o arquivo")
    conferir(fluxo.e_status_sucesso("baixado e organizado") is True,
             "sem depender de maiúscula")
    conferir(fluxo.e_status_sucesso("  BAIXADO E ORGANIZADO  ") is True,
             "sem depender de espaço nas pontas")

    print()
    print("--- 2. o texto antigo, errado, NÃO É o que se compara mais ---")
    # Este é o próprio bug, guardado ao contrário: se "OK" voltar a ser o
    # critério, a fricção do go live volta a nunca acontecer.
    conferir(fluxo.e_status_sucesso("OK") is False,
             "'OK' não é reconhecido: é vocabulário do log, não da fila",
             "voltar a comparar com isto reintroduz o bug de 23/09/2026")

    print()
    print("--- 3. falha não é sucesso, e continua sem fricção nenhuma ---")
    for falha in ("FALTA A BET", "FALTA PASTA NO DRIVE", "FORMATO NAO ACEITO",
                 "qualquer coisa que não seja o texto exato"):
        conferir(fluxo.e_status_sucesso(falha) is False,
                 f"'{falha}' não é sucesso")

    print()
    print("--- 4. vazio não é sucesso (linha pendente, nunca processada) ---")
    conferir(fluxo.e_status_sucesso("") is False, "string vazia")
    conferir(fluxo.e_status_sucesso(None) is False, "None, sem estourar erro")

    print()
    print("--- 5. é o MESMO texto que a fila de verdade grava ---")
    # A prova de que a função fala a língua certa: procura no código o ÚNICO
    # lugar que escreve sucesso na coluna status da fila, e confere que é a
    # mesma string, e não duas cópias que podem um dia divergir.
    fonte = open(os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8").read()
    gravacoes = fonte.count('"BAIXADO E ORGANIZADO"')
    conferir(gravacoes >= 2,
             "o texto aparece tanto na gravação quanto na comparação",
             f"achei {gravacoes} ocorrência(s)")

    print()
    print("--- 6. as quatro chamadas na tela continuam ligadas a esta função ---")
    tela = open(os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py"),
               encoding="utf-8").read()
    chamadas = tela.count("fluxo.e_status_sucesso(")
    conferir(chamadas == 4,
             "as quatro chamadas continuam existindo (link colado x2, lote x2)",
             f"achei {chamadas}; se sumir alguma, a fricção para de valer lá")


if __name__ == "__main__":
    print("=" * 74)
    print("  A fricção do Baixar de novo reconhece sucesso de verdade")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
