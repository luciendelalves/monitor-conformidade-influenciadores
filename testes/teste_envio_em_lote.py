# -*- coding: utf-8 -*-
"""
Prova que o envio de vários arquivos pela tela chega inteiro no trabalhador.

POR QUE ESTE TESTE EXISTE (30/08/2026)

O envio saiu de dentro da tela e passou para o trabalhador. O caminho ficou
mais longo: a tela grava os arquivos em disco, monta uma tarefa em JSON, e o
trabalhador lê essa tarefa e processa um por um.

Cada elo desse caminho pode perder coisa em silêncio. O que mais preocupa é a
data: ela sai da tela como objeto, precisa virar texto para caber no JSON, e
voltar a ser data do outro lado. Se voltar errada, o vídeo é arquivado no mês
errado e ninguém percebe.

Este teste NÃO fala com o Google. Ele substitui a parte que sobe para o Drive
por uma que só anota o que recebeu, e confere que chegou certo.

    py testes\teste_envio_em_lote.py
"""
import json
import os
import sys
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fila_trabalho
import fluxo_downloads as fluxo

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    print("--- 1. a tela guarda os arquivos ---")
    guardados = []
    for i, nome in enumerate(["14/08 - @lomma - tela 1.mp4",
                              "14/08 - @lomma - tela 2.mp4",
                              "foto do post.png"]):
        caminho = fluxo.guardar_envio(nome, b"conteudo de mentira %d" % i)
        guardados.append({"caminho": caminho, "nome": nome})
        existe = os.path.exists(caminho)
        conferir(existe, f"gravou {nome!r}", caminho)

    # Isto é sobre a pasta de ESPERA no servidor, não sobre o Drive. O Drive é
    # um só para todo mundo, organizado por bet, ano, mês e influenciador, e
    # nada aqui muda isso. O que se confere é que dois envios simultâneos, de
    # pessoas diferentes, com arquivo de mesmo nome, não se sobrescrevem
    # enquanto esperam o trabalhador pegar.
    conferir(len({os.path.dirname(g["caminho"]) for g in guardados}) == 3,
             "cada arquivo espera numa pasta própria, no servidor",
             "dois envios ao mesmo tempo não podem se sobrescrever na espera")

    # A barra do padrão do Marketing é nome válido no Drive e separador de
    # pasta no Windows. Já quebrou o programa três vezes.
    conferir(all("/" not in os.path.basename(g["caminho"]) for g in guardados),
             "a barra do nome virou algo que o Windows aceita gravar")

    print()
    print("--- 2. a tarefa cabe em JSON e sobrevive à ida e volta ---")
    campos = {
        "handle": "@lomma", "data": date(2026, 8, 14).isoformat(),
        "ciclo": "9", "marca": "EDS", "tipo": "STORIES", "tela": 3,
    }
    try:
        texto = json.dumps({"arquivos": guardados, "campos": campos})
        de_volta = json.loads(texto)
        conferir(True, "a tarefa vira JSON sem erro")
    except Exception as e:
        conferir(False, "a tarefa vira JSON sem erro", str(e)[:120])
        return

    conferir(de_volta["campos"]["data"] == "2026-08-14",
             "a data atravessou como texto", de_volta["campos"]["data"])
    conferir(len(de_volta["arquivos"]) == 3, "os três arquivos atravessaram")

    print()
    print("--- 3. o trabalhador entende o que recebeu ---")
    from datetime import datetime
    lida = datetime.strptime(de_volta["campos"]["data"][:10], "%Y-%m-%d").date()
    conferir(lida == date(2026, 8, 14),
             "a data voltou a ser data, e é a mesma", str(lida))
    conferir(fluxo.MESES[lida.month - 1] == "H AGOSTO",
             "o mês da planilha sai certo dessa data", fluxo.MESES[lida.month - 1])

    inicio = de_volta["campos"]["tela"]
    numeros = [(inicio + i) if inicio else None for i in range(3)]
    conferir(numeros == [3, 4, 5],
             "a numeração de tela avança em vez de repetir", str(numeros))

    print()
    print("--- 4. o trabalhador processa sem falar com o Google ---")
    recebidos = []

    def espiao(caminho, nome_original=None, **kw):
        recebidos.append({"nome": nome_original, "data": kw.get("data_manual"),
                          "tela": kw.get("tela"), "handle": kw.get("handle_manual")})
        return {"status": "OK"}

    original = fluxo.processar_arquivo_no_disco
    fluxo.processar_arquivo_no_disco = espiao
    try:
        import trabalhador
        tarefa = {"id": "teste", "tipo": fila_trabalho.ENVIAR_ARQUIVOS,
                  "rotulo": "teste", "dados": de_volta, "mensagens": []}
        resultado = trabalhador.executar_envio(tarefa)
    finally:
        fluxo.processar_arquivo_no_disco = original

    conferir(resultado["organizados"] == 3,
             "os três foram processados", str(resultado))
    conferir([r["nome"] for r in recebidos] == [g["nome"] for g in guardados],
             "chegaram com o nome ORIGINAL, não o ajustado para o disco",
             str([r["nome"] for r in recebidos]))
    conferir([r["tela"] for r in recebidos] == [3, 4, 5],
             "cada um recebeu seu número de tela", str([r["tela"] for r in recebidos]))
    conferir(all(r["data"] == date(2026, 8, 14) for r in recebidos),
             "todos receberam a data certa")

    print()
    print("--- 5. a limpeza aconteceu ---")
    conferir(not any(os.path.exists(g["caminho"]) for g in guardados),
             "os arquivos guardados foram apagados depois de processados")

    print()
    print("--- 6. o envio manda para análise no fim (23/09/2026) ---")
    # Achado testando de verdade: @apoline subiu uma foto pela tela e a linha
    # ficou "AGUARDANDO VALIDAÇÃO" para sempre, porque só a fila de downloads
    # chamava fluxo.enfileirar_analise. Este teste prova que executar_envio
    # passou a chamar também, só para os arquivos que subiram OK (com
    # "destino" preenchido), e não para os que falharam.
    mandados = []

    def espiao_com_destino(caminho, nome_original=None, **kw):
        if nome_original == "falhou.mp4":
            return {"status": "FALHA: mentira do teste"}
        return {"status": "OK", "destino": f"https://drive/{nome_original}"}

    def enfileirar_espiao(links, log_fn=print, criada_por=None):
        mandados.extend(links)
        return len(links)

    original_processar = fluxo.processar_arquivo_no_disco
    original_enfileirar = fluxo.enfileirar_analise
    fluxo.processar_arquivo_no_disco = espiao_com_destino
    fluxo.enfileirar_analise = enfileirar_espiao
    try:
        guardados_6 = [
            {"caminho": fluxo.guardar_envio("ok1.mp4", b"x"), "nome": "ok1.mp4"},
            {"caminho": fluxo.guardar_envio("ok2.mp4", b"x"), "nome": "ok2.mp4"},
            {"caminho": fluxo.guardar_envio("falhou.mp4", b"x"), "nome": "falhou.mp4"},
        ]
        tarefa_6 = {"id": "teste6", "tipo": fila_trabalho.ENVIAR_ARQUIVOS,
                   "rotulo": "teste", "criada_por": "auditor@empresa.com",
                   "dados": {"arquivos": guardados_6, "campos": {}}, "mensagens": []}
        import trabalhador
        trabalhador.executar_envio(tarefa_6)
    finally:
        fluxo.processar_arquivo_no_disco = original_processar
        fluxo.enfileirar_analise = original_enfileirar

    conferir(mandados == ["https://drive/ok1.mp4", "https://drive/ok2.mp4"],
             "só os que subiram OK, com o link de destino, vão para análise",
             str(mandados))


if __name__ == "__main__":
    print("=" * 70)
    print("  Envio em lote: da tela até o trabalhador")
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
        print("  PASSOU. O envio chega inteiro no trabalhador.")
    print("=" * 70)
    sys.exit(1 if falhas else 0)
