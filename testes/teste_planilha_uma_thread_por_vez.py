# -*- coding: utf-8 -*-
"""
Chamada a planilha acontece UMA POR VEZ, mesmo com duas threads.

POR QUE ESTE TESTE EXISTE (08/09/2026)

O trabalhador morreu com "Segmentation fault", exit 139, sem traceback nenhum,
no meio de um download. Erro de Python teria traceback e a tarefa marcada como
falha; ali nao houve nem um nem outro, e e assim que defeito em biblioteca
nativa aparece.

A CAUSA RAIZ: sheets_client guarda UM service em variavel de modulo
(`_service`) e entrega o mesmo objeto a qualquer thread. O cliente do Google
carrega um http por dentro que NAO e seguro para uso simultaneo. E `executar()`
ainda ZERA esse global quando ha erro de rede, o que uma thread pode fazer
enquanto a outra esta usando o objeto.

DUAS THREADS DO TRABALHADOR USAM ESSE MESMO CLIENTE, e uma delas e anterior a
qualquer mudanca recente:

  thread principal   escreve o veredito quando uma analise termina
                     (concluir_analise -> pipeline.gravar_veredito ->
                      sheets_client.escrever_lote)
  linha de download  escreve a linha da Monitoramento e o status da fila
                     (processar_fila)

As analises NAO entram nessa conta: rodam em ProcessPoolExecutor, e cada
processo tem o service proprio.

POR QUE O TESTE E ASSIM. Reproduzir o segfault de verdade exigiria bater na API
do Google com duas threads e ainda seria intermitente. O que da para afirmar de
forma deterministica e a INVARIANTE que evita o segfault: duas chamadas nunca
correm ao mesmo tempo. O dublê abaixo conta quantas estao dentro ao mesmo tempo,
e o teste exige que esse maximo seja 1.

Sem serializacao, o maximo observado e o numero de threads. Com ela, e 1.

Nao fala com o Google, nao le token, nao gasta chamada.

    py testes\teste_planilha_uma_thread_por_vez.py
"""
import os
import sys
import threading
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import sheets_client  # noqa: E402

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


QUANTAS_THREADS = 6


class ContadorDeSimultaneas:
    """Conta quantas chamadas estao dentro de executar() ao mesmo tempo."""

    def __init__(self):
        self.dentro = 0
        self.maximo = 0
        self.chamadas = 0
        self.trava = threading.Lock()

    def chamada(self):
        with self.trava:
            self.dentro += 1
            self.maximo = max(self.maximo, self.dentro)
            self.chamadas += 1
        # Segura um instante para as threads se sobreporem de verdade. Sem
        # isso, cada uma entraria e sairia antes da proxima chegar, e o teste
        # passaria sem provar nada.
        time.sleep(0.05)
        with self.trava:
            self.dentro -= 1
        return "ok"


def rodar():
    print("--- 1. duas ou mais threads nao entram juntas ---")
    contador = ContadorDeSimultaneas()
    erros = []

    def uma_thread():
        try:
            sheets_client.executar(contador.chamada)
        except Exception as e:
            erros.append(e)

    threads = [threading.Thread(target=uma_thread) for _ in range(QUANTAS_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    conferir(not erros, "nenhuma thread levantou erro", str(erros[:2]))
    conferir(contador.chamadas == QUANTAS_THREADS,
             f"as {QUANTAS_THREADS} chamadas aconteceram",
             f"aconteceram {contador.chamadas}")
    conferir(contador.maximo == 1,
             "e NUNCA houve duas ao mesmo tempo",
             f"o maximo simultaneo foi {contador.maximo}, e uso simultaneo "
             f"do cliente do Google derruba o processo com segfault")

    print()
    print("--- 2. a serializacao nao quebra a repeticao em erro de rede ---")
    # A repeticao existe desde 28/08/2026: uma oscilacao de rede derrubou o
    # carregamento da planilha, e a segunda tentativa saia na hora e caia junto.
    # Serializar nao pode ter desligado isso.
    tentativas = {"n": 0}

    def falha_uma_vez():
        tentativas["n"] += 1
        if tentativas["n"] == 1:
            raise TimeoutError("oscilacao de rede de mentira")
        return "veio na segunda"

    resultado = sheets_client.executar(falha_uma_vez, tentativas=3, espera_s=0)
    conferir(resultado == "veio na segunda",
             "erro de rede ainda e repetido e a chamada vinga",
             repr(resultado))
    conferir(tentativas["n"] == 2, "e foram exatamente duas tentativas",
             f"foram {tentativas['n']}")

    print()
    print("--- 3. chamada nao repetivel continua nao repetindo ---")
    # O caso e o append de linha nova: se o pedido chegou ao Google e so a
    # resposta se perdeu, repetir insere a mesma linha duas vezes, e linha
    # duplicada numa planilha de auditoria e pior que erro na tela.
    vezes = {"n": 0}

    def sempre_falha():
        vezes["n"] += 1
        raise TimeoutError("cai sempre")

    try:
        sheets_client.executar(sempre_falha, tentativas=3, espera_s=0,
                               repetivel=False)
    except Exception:
        pass
    conferir(vezes["n"] == 1,
             "com repetivel=False, tentou uma vez so",
             f"tentou {vezes['n']} vezes")

    print()
    print("--- 4. chamada de dentro de chamada nao trava ---")
    # Se a trava nao for reentrante, uma chamada aninhada na MESMA thread
    # espera por si mesma e o programa congela para sempre. Preferir travar
    # errado a congelar nao e opcao: congelado nao aparece em log nenhum.
    def por_fora():
        return sheets_client.executar(lambda: "de dentro")

    pronto = []

    def tentar_aninhado():
        pronto.append(sheets_client.executar(por_fora))

    t = threading.Thread(target=tentar_aninhado, daemon=True)
    t.start()
    t.join(timeout=10)
    conferir(pronto == ["de dentro"],
             "chamada aninhada na mesma thread completa",
             "se travou aqui, a trava nao e reentrante")


if __name__ == "__main__":
    print("=" * 74)
    print("  Chamada a planilha acontece uma por vez")
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
