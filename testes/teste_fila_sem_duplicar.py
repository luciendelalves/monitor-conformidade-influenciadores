# -*- coding: utf-8 -*-
"""
Prova que duas pessoas mandando o MESMO endereço ao mesmo tempo geram um
download só.

POR QUE ESTE TESTE EXISTE (30/08/2026)

No teste das duas janelas, o auditor mandou o mesmo reel e o mesmo story pelas
duas, e baixou uma vez só. Ao conferir por que, apareceu que a proteção existia
mas não era à prova de simultaneidade: adicionar_na_fila lia a fila, decidia o
que era novo e acrescentava, com duas chamadas à planilha no meio. Isso dá
quase um segundo de janela. Duas pessoas dentro dela leem as duas a fila sem o
endereço, e as duas o acrescentam.

O teste das duas janelas passou porque os dois cliques foram separados por
segundos. Simultâneo de verdade é que expõe.

A consequência não é uma linha feia na planilha: é uma segunda chamada ao
Instagram para baixar o que já foi baixado. Chamada ao Instagram é o recurso
escasso deste programa, o teto do dia conta chamada e não vídeo, e foi
repetição de chamada que marcou duas contas em agosto. A conferência de vídeo
repetido que existe no envio não cobre isso: ela compara o conteúdo do arquivo
e só roda DEPOIS do download.

Aqui a planilha é substituída por um arquivo local, e os processos são de
verdade. Não fala com o Google nem com o Instagram.

    py testes\teste_fila_sem_duplicar.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

LINK = "https://www.instagram.com/miltinhooalves/reel/Dco-74xMtGx/"


# ------------------------------------------------------------------
# Modo filho: uma pessoa clicando em "Adicionar"
# ------------------------------------------------------------------
def modo_pessoa(arquivo_fila, arquivo_trava, nome, atraso_leitura, travado):
    """Chama a mesma função do programa, com a planilha trocada por um arquivo.

    `atraso_leitura` imita o tempo que as chamadas à planilha levam de verdade.
    Sem ele a janela de risco seria de microssegundos e o teste não provaria
    nada: o defeito existe justamente porque ali há ida e volta de rede.
    """
    import fluxo_downloads as fluxo

    fluxo.ARQUIVO_TRAVA_FILA = arquivo_trava

    def ler_fila_falsa():
        time.sleep(float(atraso_leitura))  # a ida e volta da planilha
        if not os.path.exists(arquivo_fila):
            return []
        with open(arquivo_fila, encoding="utf-8") as f:
            return json.load(f)

    class SheetsFalso:
        @staticmethod
        def adicionar_linhas(_id, _aba, _faixa, novas):
            time.sleep(float(atraso_leitura))  # a volta da escrita
            atual = ler_fila_falsa.__wrapped__() if False else (
                json.load(open(arquivo_fila, encoding="utf-8"))
                if os.path.exists(arquivo_fila) else [])
            for n in novas:
                # Monta a linha pelo mapa de colunas do próprio programa, e não
                # por posição escrita à mão. Em 31/08/2026 a coluna do link do
                # vídeo saiu da planilha, o programa passou a mandar 5 valores
                # em vez de 6, e este dublê quebrou por esperar 6. Assim ele
                # acompanha sozinho a próxima mudança de coluna.
                linha = {"numero_linha": len(atual) + 2}
                for nome, indice in fluxo.COL_FILA.items():
                    linha[nome] = n[indice] if len(n) > indice else ""
                atual.append(linha)
            with open(arquivo_fila, "w", encoding="utf-8") as f:
                json.dump(atual, f)

    sys.modules["sheets_client"] = SheetsFalso
    fluxo.ler_fila = ler_fila_falsa
    fluxo._planilha_fila_id = lambda: "planilha-de-mentira"

    if travado == "nao":
        # Versão sem trava, para provar que o defeito era real. Mesmo corpo da
        # função, sem o "with trava.travar".
        def sem_trava(itens):
            existentes = {x["link"] for x in fluxo.ler_fila() if x["link"]}
            novos = []
            for item in itens:
                influ, link = item[0], item[1]
                if link and link not in existentes:
                    novos.append([influ, link] + [""] * (len(fluxo.COL_FILA) - 2))
                    existentes.add(link)
            if novos:
                SheetsFalso.adicionar_linhas(None, None, None, novos)
            return len(novos), len(itens) - len(novos)
        add, dup = sem_trava([(nome, LINK, "", "EDS")])
    else:
        add, dup = fluxo.adicionar_na_fila([(nome, LINK, "", "EDS")])

    print(json.dumps({"nome": nome, "acrescentou": add, "era_repetido": dup}))


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


def rodada(travado, quantas_pessoas=4, atraso=0.4):
    pasta = tempfile.mkdtemp(prefix="fila_dup_")
    arquivo_fila = os.path.join(pasta, "fila.json")
    arquivo_trava = os.path.join(pasta, "trava")
    processos = [
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--pessoa",
             arquivo_fila, arquivo_trava, f"pessoa{i+1}", str(atraso), travado],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=BASE)
        for i in range(quantas_pessoas)
    ]
    saidas = []
    for p in processos:
        out, err = p.communicate(timeout=120)
        for linha in out.splitlines():
            if linha.strip().startswith("{"):
                saidas.append(json.loads(linha.strip()))
        if p.returncode != 0:
            print(f"      [processo saiu com {p.returncode}] {err.strip()[:200]}")

    linhas = []
    if os.path.exists(arquivo_fila):
        with open(arquivo_fila, encoding="utf-8") as f:
            linhas = json.load(f)
    return saidas, linhas


def rodar():
    print("--- 1. sem trava: o defeito que existia ate hoje ---")
    print("    (4 pessoas mandando o mesmo endereco ao mesmo tempo)")
    saidas, linhas = rodada("nao")
    vezes = Counter(l["link"] for l in linhas)[LINK]
    print(f"    o endereco entrou {vezes} vez(es) na fila")
    conferir(vezes > 1,
             "sem trava, o mesmo endereco entra mais de uma vez",
             f"entrou {vezes}x; se deu 1, a janela do teste foi curta demais")
    print(f"    -> seriam {vezes} chamadas ao Instagram para o mesmo video")

    print()
    print("--- 2. com a trava, que e como o programa esta agora ---")
    saidas, linhas = rodada("sim")
    vezes = Counter(l["link"] for l in linhas)[LINK]
    conferir(vezes == 1,
             "o endereco entra UMA vez so, mesmo com 4 pessoas simultaneas",
             f"entrou {vezes}x")
    acrescentou = sum(s["acrescentou"] for s in saidas)
    repetido = sum(s["era_repetido"] for s in saidas)
    conferir(acrescentou == 1,
             "so uma pessoa recebe 'adicionado'", f"{acrescentou}")
    conferir(repetido == len(saidas) - 1,
             "as outras recebem 'ja esta na fila', que e o aviso certo na tela",
             f"{repetido}")

    print()
    print("--- 3. o mesmo endereco repetido dentro de UM clique ---")
    import fluxo_downloads as fluxo
    import inspect
    fonte = inspect.getsource(fluxo.adicionar_na_fila)
    conferir("existentes.add(link)" in fonte,
             "conta o que acabou de entrar, senao passaria duas vezes na mesma lista")
    conferir("trava.travar" in fonte, "a funcao esta travada")

    print()
    print("--- 4. rodadas repetidas, porque corrida nao se prova uma vez ---")
    for i in range(3):
        _s, linhas = rodada("sim")
        vezes = Counter(l["link"] for l in linhas)[LINK]
        conferir(vezes == 1, f"rodada extra {i+1}: entrou 1 vez", f"entrou {vezes}x")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--pessoa":
        modo_pessoa(*sys.argv[2:])
    else:
        print("=" * 74)
        print("  Duas pessoas, o mesmo endereco, um download so")
        print("=" * 74)
        print()
        rodar()
        print()
        print("=" * 74)
        print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
        print("=" * 74)
        sys.exit(1 if falhas else 0)
