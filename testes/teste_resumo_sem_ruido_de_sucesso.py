# -*- coding: utf-8 -*-
"""
Prova que resumo_da_tarefa não repete confirmação de sucesso nem o mesmo
aviso várias vezes, quando a rodada processa mais de um arquivo.

POR QUE ESTE TESTE EXISTE (25/09/2026)

O auditor mostrou a tela de acompanhamento com 3 arquivos numa rodada: cada
um gerou "subiu pro Drive de teste." e "Calendário não preenchido: ..." (a
mesma frase, repetida três vezes, porque era o mesmo influenciador na mesma
data). A caixa de "motivos", sempre visível sem precisar abrir nada, ficava
com 6 linhas para um resultado que já estava dito em uma: "3 de 3 baixados
e organizados." Pedido dele: deixar mais enxuto.

Corrigido em resumo_da_tarefa (fluxo_downloads.py): linha de puro sucesso
("subiu pro Drive de teste.", "Calendário preenchido (...)") sai da lista de
motivos, e motivo repetido aparece só uma vez. O que precisa de atenção
("Calendário não preenchido", falta de bet, falta de pasta etc.) continua
subindo, sem precisar abrir "Ver o que aconteceu".

CORRIGIDO DE NOVO NO MESMO DIA, ao vivo: a primeira versão deste teste usava
mensagem SEM o relógio na frente ("   -> subiu..."), e por isso passou
mesmo com o código ainda errado. De verdade, `fila_trabalho.anotar` grava
cada mensagem já com "HH:MM:SS " antes do texto, então a comparação
precisa tirar isso primeiro. As mensagens abaixo agora têm relógio, do
jeito que a tarefa de verdade grava.

    py testes\teste_resumo_sem_ruido_de_sucesso.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import fluxo_downloads as fluxo
import fila_trabalho as fila

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    # O CASO EXATO DA TELA (25/09/2026): três arquivos do mesmo influenciador
    # e data, todos baixados e organizados, e o Calendário sem linha pra
    # nenhum dos três.
    tarefa = {
        "situacao": fila.CONCLUIDA,
        "tipo": fila.BAIXAR_FILA,
        "terminou_em": "2026-09-23 14:25:04",
        "resultado": {"processados": 3, "organizados": 3},
        "mensagens": [
            "11:18:23 [Fila linha 24] | https://www.instagram.com/stories/exemplo/1/",
            "11:18:23    (organizando como @eduardagutierrez, que é o @ do próprio link)",
            "11:18:48    -> subiu pro Drive de teste.",
            "11:18:50    -> Calendário não preenchido: Não achei linha no Calendário "
            "para @eduardagutierrez, LOTTU, 23/09/2026.",
            "11:19:19 [Fila linha 25] | https://www.instagram.com/stories/exemplo/2/",
            "11:19:40    -> subiu pro Drive de teste.",
            "11:19:40    -> Calendário não preenchido: Não achei linha no Calendário "
            "para @eduardagutierrez, LOTTU, 23/09/2026.",
            "11:20:03 [Fila linha 26] | https://www.instagram.com/stories/exemplo/3/",
            "11:20:22    -> subiu pro Drive de teste.",
            "11:20:22    -> Calendário não preenchido: Não achei linha no Calendário "
            "para @eduardagutierrez, LOTTU, 23/09/2026.",
        ],
    }
    aparencia, texto, motivos = fluxo.resumo_da_tarefa(tarefa)

    conferir(aparencia == "ok", "aparência é ok, os três organizaram", aparencia)
    conferir(texto == "14:25: 3 de 3 baixados e organizados.",
             "texto continua contando certo", texto)
    conferir(not any("subiu pro drive de teste" in m.lower() for m in motivos),
             "confirmação de sucesso não aparece nos motivos", motivos)
    conferir(len(motivos) == 1,
             "o aviso repetido três vezes vira só uma linha", motivos)
    conferir("Calendário não preenchido" in motivos[0],
             "o aviso que precisa de atenção continua aparecendo", motivos)

    # UM SUCESSO SÓ, SEM AVISO NENHUM: a lista de motivos precisa continuar
    # podendo vir vazia, e o teto de 6 continua valendo, não só a dedup.
    tarefa_limpa = {
        "situacao": fila.CONCLUIDA,
        "tipo": fila.BAIXAR_FILA,
        "terminou_em": "2026-09-23 14:30:00",
        "resultado": {"processados": 1, "organizados": 1},
        "mensagens": [
            "11:29:40 [Fila linha 30] | https://www.instagram.com/stories/exemplo/4/",
            "11:29:55    -> subiu pro Drive de teste.",
            "11:29:56    -> Calendário preenchido (Status)",
        ],
    }
    _, _, motivos_limpos = fluxo.resumo_da_tarefa(tarefa_limpa)
    conferir(motivos_limpos == [],
             "sucesso limpo não deixa nenhum motivo pra mostrar", motivos_limpos)


if __name__ == "__main__":
    print("=" * 70)
    print("  resumo_da_tarefa não repete sucesso nem aviso igual")
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
