# -*- coding: utf-8 -*-
"""
A serialização de acesso à conta do Instagram entre máquinas funciona?

POR QUE ESTE TESTE EXISTE (22/09/2026)

Combinado com o auditor em 21/09/2026, depois de investigar o loop de
captcha na conta compartilhada da Responsável A: além da pausa compartilhada (já
commitada e sem teste próprio), a conta precisa de uma segunda proteção,
que evita duas ou mais máquinas automatizarem chamada na MESMA conta ao
mesmo tempo, e não só reagir depois que o Instagram já reclamou.

O mecanismo (aguardar_vez_da_conta, liberar_vez_da_conta,
_uso_em_andamento_de_outra_maquina) usa a mesma aba Estado_Instagram da
pausa compartilhada, só acrescentando linha. Este teste substitui
sheets_client por uma planilha de mentira, em memória, e não fala com o
Google nem com o Instagram.

    py testes\teste_serializar_acesso_instagram.py
"""
import os
import sys
import threading
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

OK, FALTA = "  ok  ", "FALTA"
falhas = []


def conferir(rotulo, condicao):
    print(f"[{OK if condicao else FALTA}] {rotulo}")
    if not condicao:
        falhas.append(rotulo)


class SheetsFalso:
    """Guarda as linhas de Estado_Instagram numa lista em memória, no mesmo
    formato que a API de verdade devolveria (lista de listas)."""
    linhas = []

    @staticmethod
    def adicionar_linhas(planilha, aba, faixa, novas):
        SheetsFalso.linhas.extend(list(n) for n in novas)

    @staticmethod
    def executar(fn, repetivel=True):
        return fn()

    @staticmethod
    def get_service():
        class _Values:
            def get(self, spreadsheetId, range):
                class _Chamada:
                    def execute(self):
                        return {"values": [list(l) for l in SheetsFalso.linhas]}
                return _Chamada()

        class _Sheets:
            def values(self):
                return _Values()

        class _Servico:
            def spreadsheets(self):
                return _Sheets()
        return _Servico()


def preparar():
    import fluxo_downloads as fluxo
    import registro_fechamentos
    SheetsFalso.linhas = []
    sys.modules["sheets_client"] = SheetsFalso
    fluxo._planilha_fechamentos_id = lambda: "planilha-de-mentira"
    registro_fechamentos.garantir_cabecalho = lambda *a, **k: 0
    fluxo.USUARIO_DOS_COOKIES = "conta_teste_serializacao"
    fluxo.SEGUNDOS_ENTRE_TENTATIVAS_VEZ_DA_CONTA = 0.05
    fluxo.SEGUNDOS_LIMITE_ESPERA_VEZ_DA_CONTA = 0.3
    return fluxo


def testar_uso_em_andamento():
    print("\n--- 1. quem está usando a conta agora, lendo a aba ---")
    fluxo = preparar()
    os.environ["COMPUTERNAME"] = "MAQUINA-A"

    conferir("ninguém usando: aba vazia devolve None",
              fluxo._uso_em_andamento_de_outra_maquina("conta_teste_serializacao") is None)

    SheetsFalso.linhas.append(
        ["2026-09-22 10:00:00", "conta_teste_serializacao", "MAQUINA-B", "inicio_uso", "", ""])
    conferir("MAQUINA-B com inicio_uso em aberto: aparece como dona",
              fluxo._uso_em_andamento_de_outra_maquina("conta_teste_serializacao") == "MAQUINA-B")

    SheetsFalso.linhas.append(
        ["2026-09-22 10:05:00", "conta_teste_serializacao", "MAQUINA-B", "fim_uso", "", ""])
    conferir("depois do fim_uso, ninguém mais está usando",
              fluxo._uso_em_andamento_de_outra_maquina("conta_teste_serializacao") is None)

    SheetsFalso.linhas.append(
        ["2026-09-22 10:10:00", "conta_teste_serializacao", "MAQUINA-A", "inicio_uso", "", ""])
    conferir("inicio_uso da PRÓPRIA máquina não conta como outra máquina usando",
              fluxo._uso_em_andamento_de_outra_maquina("conta_teste_serializacao") is None)


def testar_espera_ate_a_outra_maquina_liberar():
    print("\n--- 2. espera enquanto outra máquina está usando, e segue quando ela libera ---")
    fluxo = preparar()
    os.environ["COMPUTERNAME"] = "MAQUINA-A"
    SheetsFalso.linhas.append(
        ["2026-09-22 10:00:00", "conta_teste_serializacao", "MAQUINA-B", "inicio_uso", "", ""])

    mensagens = []
    resultado = {}

    def liberar_depois_de_um_tempinho():
        time.sleep(0.15)
        SheetsFalso.linhas.append(
            ["2026-09-22 10:00:20", "conta_teste_serializacao", "MAQUINA-B", "fim_uso", "", ""])

    t = threading.Thread(target=liberar_depois_de_um_tempinho)
    t.start()
    inicio = time.time()
    resultado["marcou"] = fluxo.aguardar_vez_da_conta(log_fn=mensagens.append)
    duracao = time.time() - inicio
    t.join()

    conferir("esperou de verdade, não passou direto (>= 0.1s)", duracao >= 0.1)
    conferir("avisou que estava esperando",
              any("Esperando" in m for m in mensagens))
    conferir("devolveu True (marcou uso)", resultado["marcou"] is True)
    conferir("gravou o próprio início de uso ao sair da espera",
              any(l[2] == "MAQUINA-A" and l[3] == "inicio_uso" for l in SheetsFalso.linhas))


def testar_desiste_depois_do_limite():
    print("\n--- 3. desiste de esperar depois do limite, e segue mesmo assim ---")
    fluxo = preparar()
    os.environ["COMPUTERNAME"] = "MAQUINA-A"
    # MAQUINA-B nunca libera: simula um processo que caiu no meio do caminho.
    SheetsFalso.linhas.append(
        ["2026-09-22 10:00:00", "conta_teste_serializacao", "MAQUINA-B", "inicio_uso", "", ""])

    mensagens = []
    inicio = time.time()
    marcou = fluxo.aguardar_vez_da_conta(log_fn=mensagens.append)
    duracao = time.time() - inicio

    conferir("respeitou o limite de espera, não travou pra sempre",
              duracao < 2)
    conferir("avisou que estava seguindo mesmo com a outra máquina marcada",
              any("Seguindo mesmo assim" in m for m in mensagens))
    conferir("devolveu True mesmo assim (não trava o trabalho)", marcou is True)


def testar_liberar_vez_da_conta():
    print("\n--- 4. liberar grava fim_uso, e libera quem estava esperando ---")
    fluxo = preparar()
    os.environ["COMPUTERNAME"] = "MAQUINA-A"

    fluxo.aguardar_vez_da_conta()  # marca uso desta máquina
    conferir("depois de marcar, outra máquina veria esta em uso",
              fluxo._uso_em_andamento_de_outra_maquina("conta_teste_serializacao") is None)  # não é "outra" pra si mesma

    os.environ["COMPUTERNAME"] = "MAQUINA-C"
    conferir("de outra máquina, MAQUINA-A aparece como dona",
              fluxo._uso_em_andamento_de_outra_maquina("conta_teste_serializacao") == "MAQUINA-A")

    os.environ["COMPUTERNAME"] = "MAQUINA-A"
    fluxo.liberar_vez_da_conta()
    os.environ["COMPUTERNAME"] = "MAQUINA-C"
    conferir("depois de liberar, MAQUINA-C não vê mais ninguém usando",
              fluxo._uso_em_andamento_de_outra_maquina("conta_teste_serializacao") is None)


def testar_planilha_nao_configurada_nao_trava_ninguem():
    print("\n--- 5. sem a planilha de fechamentos configurada, não espera nem falha ---")
    fluxo = preparar()
    fluxo._planilha_fechamentos_id = lambda: None
    marcou = fluxo.aguardar_vez_da_conta()
    conferir("devolve False (nada a liberar depois)", marcou is False)


def testar_fila_tem_link_do_instagram():
    print("\n--- 6. só espera a vez quando a fila realmente tem link do Instagram ---")
    fluxo = preparar()
    fluxo.ler_fila = lambda: [{"link": "https://www.youtube.com/watch?v=abc"}]
    conferir("fila só com YouTube: não precisa esperar vez nenhuma",
              fluxo.fila_tem_link_do_instagram() is False)
    fluxo.ler_fila = lambda: [{"link": "https://www.instagram.com/p/abc/"}]
    conferir("fila com Instagram: precisa esperar a vez",
              fluxo.fila_tem_link_do_instagram() is True)


if __name__ == "__main__":
    computername_original = os.environ.get("COMPUTERNAME")
    try:
        testar_uso_em_andamento()
        testar_espera_ate_a_outra_maquina_liberar()
        testar_desiste_depois_do_limite()
        testar_liberar_vez_da_conta()
        testar_planilha_nao_configurada_nao_trava_ninguem()
        testar_fila_tem_link_do_instagram()
    finally:
        if computername_original is None:
            os.environ.pop("COMPUTERNAME", None)
        else:
            os.environ["COMPUTERNAME"] = computername_original

    print("\n" + "=" * 74)
    if falhas:
        print(f"FALHOU: {len(falhas)} conferência(s) não passaram.")
        for f in falhas:
            print(f"  - {f}")
        sys.exit(1)
    print("PASSOU.")
    print("=" * 74)
