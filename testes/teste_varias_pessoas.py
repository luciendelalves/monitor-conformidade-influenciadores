# -*- coding: utf-8 -*-
"""
Prova que a fila aguenta várias pessoas ao mesmo tempo.

POR QUE ESTE TESTE EXISTE (30/08/2026)

Toda a reformulação de julho e agosto (trabalhador separado, fila em disco,
trava entre processos) foi feita para o programa poder ser usado por cinco
pessoas ao mesmo tempo num servidor. O que existia até hoje provava a TRAVA
(240 escritas simultâneas num arquivo), não a FILA.

São coisas diferentes. A trava responde "duas escritas ao mesmo tempo se
perdem?". A fila responde "duas pessoas mandando trabalho ao mesmo tempo, com
o trabalhador consumindo no meio, alguma tarefa se perde ou é feita duas
vezes?". Analisar o mesmo vídeo duas vezes gasta minutos de máquina à toa;
perder uma tarefa faz um vídeo nunca ser analisado e ninguém notar.

Aqui os processos são de VERDADE, criados pelo sistema operacional, não linhas
de execução dentro do mesmo Python. Linha de execução compartilha memória e
esconde justamente o tipo de problema que só aparece entre processos, que é o
caso real: cada pessoa numa aba, o trabalhador em outro programa.

Usa uma pasta de fila só dele, descartada no fim. Não toca na fila real, não
fala com o Drive, não fala com o Instagram.

    py testes\teste_varias_pessoas.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

PESSOAS = ["Ana", "Bruno", "Carla", "Diego", "Elisa"]
TAREFAS_POR_PESSOA = 12
TRABALHADORES = 2


# ------------------------------------------------------------------
# Modos filho: é isto que roda em cada processo separado
# ------------------------------------------------------------------
def _preparar_fila(pasta):
    import fila_trabalho as fila
    fila.PASTA_FILA = pasta
    fila.garantir_pastas()
    return fila


def modo_pessoa(pasta, nome, quantas):
    """Uma pessoa mandando trabalho, como se estivesse clicando na tela."""
    fila = _preparar_fila(pasta)
    criadas = []
    for i in range(int(quantas)):
        t = fila.criar("validar", {"quem": nome, "n": i},
                       rotulo=f"{nome} pediu {i}", criada_por=nome)
        criadas.append(t["id"])
    print(json.dumps({"papel": "pessoa", "nome": nome, "criadas": criadas}))


def modo_trabalhador(pasta, nome, segundos):
    """Um trabalhador consumindo a fila, como o trabalhador.py faz."""
    fila = _preparar_fila(pasta)
    pegas = []
    limite = time.time() + float(segundos)
    ocioso = 0
    while time.time() < limite:
        t = fila.proxima()
        if t is None:
            ocioso += 1
            if ocioso > 40:
                break
            time.sleep(0.02)
            continue
        ocioso = 0
        pegas.append(t["id"])
        fila.concluir(t, {"feito_por": nome})
    print(json.dumps({"papel": "trabalhador", "nome": nome, "pegas": pegas}))


# ------------------------------------------------------------------
# Teste
# ------------------------------------------------------------------
falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def _lancar(args):
    return subprocess.Popen(
        [sys.executable, os.path.abspath(__file__)] + args,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=BASE)


def _colher(processos):
    saidas = []
    for p in processos:
        out, err = p.communicate(timeout=180)
        for linha in out.splitlines():
            linha = linha.strip()
            if linha.startswith("{"):
                saidas.append(json.loads(linha))
        if p.returncode != 0:
            print(f"   [processo saiu com {p.returncode}] {err.strip()[:300]}")
    return saidas


def parte_1_ninguem_perde_nem_repete(pasta):
    print("--- 1. cinco pessoas mandando enquanto dois trabalhadores consomem ---")
    processos = []
    # Todos começam praticamente juntos, que é o ponto: pessoas criando
    # enquanto trabalhadores retiram, sem ordem combinada entre eles.
    for nome in PESSOAS:
        processos.append(_lancar(["--pessoa", pasta, nome, str(TAREFAS_POR_PESSOA)]))
    for i in range(TRABALHADORES):
        processos.append(_lancar(["--trabalhador", pasta, f"T{i+1}", "25"]))

    saidas = _colher(processos)
    criadas = [i for s in saidas if s["papel"] == "pessoa" for i in s["criadas"]]
    pegas = [i for s in saidas if s["papel"] == "trabalhador" for i in s["pegas"]]
    esperado = len(PESSOAS) * TAREFAS_POR_PESSOA

    conferir(len(criadas) == esperado,
             f"as {esperado} tarefas foram criadas", f"criadas {len(criadas)}")

    repetidas = [i for i, n in Counter(pegas).items() if n > 1]
    conferir(not repetidas,
             "nenhuma tarefa foi pega por mais de um trabalhador",
             f"{len(repetidas)} repetida(s): {repetidas[:5]}")

    fila = _preparar_fila(pasta)
    sobraram = fila.contar(fila.PENDENTE) + fila.contar(fila.RODANDO)
    conferir(len(set(pegas)) + sobraram == esperado,
             "nenhuma tarefa se perdeu",
             f"pegas {len(set(pegas))} + na fila {sobraram} != {esperado}")

    concluidas = fila.contar(fila.CONCLUIDA)
    conferir(concluidas == len(set(pegas)),
             f"as {len(set(pegas))} pegas terminaram registradas",
             f"concluidas {concluidas}")

    por_trabalhador = {s["nome"]: len(s["pegas"]) for s in saidas
                       if s["papel"] == "trabalhador"}
    print(f"         (divisão do trabalho: {por_trabalhador})")


def parte_2_cada_um_so_tira_o_seu(pasta):
    print()
    print("--- 2. tirar da fila não pode levar o trabalho dos outros ---")
    fila = _preparar_fila(pasta)
    fila.esvaziar_tudo()

    for nome in PESSOAS[:3]:
        for i in range(4):
            fila.criar("validar", {"n": i}, rotulo=f"{nome} {i}", criada_por=nome)

    contagem = fila.pendentes_por_pessoa()
    conferir(contagem == {n: 4 for n in PESSOAS[:3]},
             "a tela consegue dizer quantas são de cada um antes do clique",
             str(contagem))

    apagadas = fila.cancelar_pendentes(de_quem="Bruno")
    conferir(apagadas == 4, "tirou as 4 do Bruno", f"tirou {apagadas}")

    depois = fila.pendentes_por_pessoa()
    conferir("Bruno" not in depois, "as do Bruno sumiram")
    conferir(depois.get("Ana") == 4 and depois.get("Carla") == 4,
             "as das outras pessoas continuam intactas", str(depois))

    # O caso perigoso: sem dizer de quem, leva tudo. Continua existindo de
    # propósito, mas a tela nunca deve chamar assim sem avisar.
    todas = fila.cancelar_pendentes()
    conferir(todas == 8, "sem dizer de quem, leva tudo (comportamento esperado)",
             f"levou {todas}")


def parte_3_trabalhador_que_morre(pasta):
    print()
    print("--- 3. trabalhador que morre no meio não leva a tarefa junto ---")
    fila = _preparar_fila(pasta)
    fila.esvaziar_tudo()

    for i in range(3):
        fila.criar("validar", {"n": i}, rotulo=f"tarefa {i}", criada_por="Ana")

    pega = fila.proxima()
    conferir(pega is not None, "o trabalhador pegou uma tarefa")
    conferir(fila.contar(fila.RODANDO) == 1, "ela está marcada como em andamento")

    # Aqui o trabalhador "morre": ninguém conclui nem falha a tarefa.
    recuperadas = fila.recuperar_orfas()
    conferir(len(recuperadas) == 1,
             "ao subir de novo, a tarefa interrompida volta para a fila",
             f"recuperou {len(recuperadas)}")
    conferir(fila.contar(fila.RODANDO) == 0, "não sobrou nada preso em andamento")
    conferir(fila.contar(fila.PENDENTE) == 3,
             "as três voltam a estar esperando", f"{fila.contar(fila.PENDENTE)}")

    de_novo = fila.proxima()
    conferir(de_novo is not None and de_novo["id"] == pega["id"],
             "e é a mesma tarefa, não uma cópia",
             f"{de_novo and de_novo['id']} vs {pega['id']}")
    msgs = " ".join(de_novo.get("mensagens") or [])
    conferir("voltou para a fila" in msgs,
             "a tarefa carrega o registro de que foi reiniciada", msgs[:80])


def parte_4_criar_e_consumir_ao_mesmo_tempo(pasta):
    print()
    print("--- 4. criar e consumir ao mesmo tempo, sem intervalo ---")
    fila = _preparar_fila(pasta)
    fila.esvaziar_tudo()

    # Trabalhador sobe ANTES de existir trabalho, e fica girando em vazio.
    # É o cenário que mais expõe corrida: ele consulta a pasta no exato
    # instante em que outro processo está gravando um arquivo lá dentro.
    trab = [_lancar(["--trabalhador", pasta, f"T{i+1}", "20"]) for i in range(TRABALHADORES)]
    time.sleep(0.3)
    pessoas = [_lancar(["--pessoa", pasta, n, "10"]) for n in PESSOAS[:3]]

    saidas = _colher(pessoas + trab)
    criadas = [i for s in saidas if s["papel"] == "pessoa" for i in s["criadas"]]
    pegas = [i for s in saidas if s["papel"] == "trabalhador" for i in s["pegas"]]

    conferir(len(criadas) == 30, "as 30 foram criadas", f"{len(criadas)}")
    conferir(len(pegas) == len(set(pegas)),
             "nenhuma foi pega duas vezes mesmo com o trabalhador girando em vazio",
             f"{len(pegas)} pegas, {len(set(pegas))} distintas")
    conferir(set(pegas) <= set(criadas),
             "nenhuma tarefa fantasma apareceu")
    sobraram = fila.contar(fila.PENDENTE) + fila.contar(fila.RODANDO)
    conferir(len(set(pegas)) + sobraram == 30,
             "a conta fecha", f"{len(set(pegas))} + {sobraram}")


def rodar():
    pasta = tempfile.mkdtemp(prefix="fila_teste_")
    try:
        parte_1_ninguem_perde_nem_repete(pasta)
        parte_2_cada_um_so_tira_o_seu(pasta)
        parte_3_trabalhador_que_morre(pasta)
        parte_4_criar_e_consumir_ao_mesmo_tempo(pasta)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--pessoa":
        modo_pessoa(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) > 1 and sys.argv[1] == "--trabalhador":
        modo_trabalhador(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("=" * 76)
        print("  Várias pessoas usando a mesma fila ao mesmo tempo")
        print("=" * 76)
        print()
        rodar()
        print()
        print("=" * 76)
        print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
        print("=" * 76)
        sys.exit(1 if falhas else 0)
