# -*- coding: utf-8 -*-
"""
O contador de "usados hoje" soma todas as máquinas que dividem a mesma conta?

POR QUE ESTE TESTE EXISTE (24/09/2026)

Pendência levantada em 22/09, adiada pra 23/09, e 23/09 acabou virando outro
assunto inteiro (Cadastro, envio). `conta["usados"]` (o "X de Y hoje" da
tela) só contava o que ESTA máquina fez. Com a conta da Responsável A dividida
entre 5 ou mais máquinas físicas, cada tela mostrava só a própria metade.

A saída reaproveita o mesmo mecanismo append-only já usado pela pausa
compartilhada (aba Estado_Instagram, uma linha por evento, nunca célula
reescrita): toda chamada de verdade grava um evento "uso", e
situacao_da_conta soma as linhas "uso" de hoje daquela conta antes de
mostrar o número, no mesmo ritmo (throttle de
SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO) que já vale para a pausa.

CONTINUA SENDO RECOMENDAÇÃO, NÃO TRAVA (decisão de 17/09): o número certo
importa para quem decide se continua, não para bloquear ninguém.

Este teste substitui sheets_client por uma planilha de mentira, em
memória, e isola o arquivo local de estado numa pasta temporária: não fala
com o Google nem toca no contador de verdade desta máquina.

    py testes\teste_contador_uso_compartilhado.py
"""
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

OK, FALTA = "  ok  ", "FALTA"
falhas = []


def conferir(rotulo, condicao, detalhe=""):
    print(f"[{OK if condicao else FALTA}] {rotulo}" + (f"   {detalhe}" if detalhe and not condicao else ""))
    if not condicao:
        falhas.append(rotulo)


class SheetsFalso:
    """Mesmo dublê de teste_serializar_acesso_instagram.py: guarda as linhas
    de Estado_Instagram numa lista em memória, no formato que a API de
    verdade devolveria."""
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


def preparar(pasta):
    import fluxo_downloads as fluxo
    import registro_fechamentos
    SheetsFalso.linhas = []
    sys.modules["sheets_client"] = SheetsFalso
    fluxo._planilha_fechamentos_id = lambda: "planilha-de-mentira"
    registro_fechamentos.garantir_cabecalho = lambda *a, **k: 0
    fluxo.ARQUIVO_ESTADO_CONTA = os.path.join(pasta, "estado_conta_instagram.json")
    fluxo.USUARIO_DOS_COOKIES = "conta_teste_contador"
    fluxo.SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO = 0
    fluxo._ULTIMA_SINCRONIA_ESTADO_COMPARTILHADO["quando"] = 0.0
    fluxo._ULTIMA_SINCRONIA_USO_COMPARTILHADO["quando"] = 0.0
    return fluxo


def testar_registra_evento_uso_ao_contar():
    print("\n--- 1. cada chamada registra um evento 'uso' na aba compartilhada ---")
    fluxo = preparar(tempfile.mkdtemp(prefix="contador_uso_"))
    os.environ["COMPUTERNAME"] = "MAQUINA-A"

    fluxo._contar_uso_instagram()
    fluxo._contar_uso_instagram()

    usos = [l for l in SheetsFalso.linhas if len(l) >= 4 and l[3] == "uso"]
    conferir("gravou uma linha 'uso' por chamada", len(usos) == 2, str(usos))
    conferir("com a conta certa", all(l[1] == "conta_teste_contador" for l in usos))
    conferir("com a máquina certa", all(l[2] == "MAQUINA-A" for l in usos))


def testar_soma_entre_maquinas():
    print("\n--- 2. situacao_da_conta soma o que outras máquinas já fizeram hoje ---")
    fluxo = preparar(tempfile.mkdtemp(prefix="contador_uso_"))
    os.environ["COMPUTERNAME"] = "MAQUINA-A"

    for _ in range(3):
        fluxo._contar_uso_instagram()
    _pode, _motivo, usados_a, _r = fluxo.situacao_da_conta()
    conferir("só com esta máquina, mostra 3", usados_a == 3, str(usados_a))

    # Outra máquina, MESMA conta, grava 4 usos direto na planilha
    # compartilhada (sem passar pelo _contar_uso_instagram desta máquina,
    # simulando o que a MAQUINA-B faria na dela).
    hoje = fluxo.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for _ in range(4):
        SheetsFalso.linhas.append([hoje, "conta_teste_contador", "MAQUINA-B", "uso", "", ""])

    _pode2, _motivo2, usados_soma, restantes_soma = fluxo.situacao_da_conta()
    conferir("agora soma as duas máquinas: 3 + 4 = 7", usados_soma == 7, str(usados_soma))
    conferir("e o restante bate com a soma, não só com o local",
             restantes_soma == max(0, fluxo.limite_diario_vigente() - 7), str(restantes_soma))


def testar_nunca_volta_pra_tras():
    print("\n--- 3. o contador local nunca desce, mesmo se a leitura da planilha atrasar ---")
    fluxo = preparar(tempfile.mkdtemp(prefix="contador_uso_"))
    os.environ["COMPUTERNAME"] = "MAQUINA-A"

    for _ in range(5):
        fluxo._contar_uso_instagram()
    _pode, _motivo, usados_antes, _r = fluxo.situacao_da_conta()
    conferir("chegou a 5 com as próprias chamadas", usados_antes == 5, str(usados_antes))

    # Simula a planilha "atrasada": as linhas de hoje ficaram só com 2
    # (rede lenta, ainda propagando). A leitura não pode fazer o contador
    # local RECUAR de 5 para 2.
    SheetsFalso.linhas = SheetsFalso.linhas[:2]
    fluxo._ULTIMA_SINCRONIA_USO_COMPARTILHADO["quando"] = 0.0
    _pode2, _motivo2, usados_depois, _r2 = fluxo.situacao_da_conta()
    conferir("continua em 5, não recuou para 2", usados_depois == 5, str(usados_depois))


def testar_respeita_o_intervalo_de_sincronia():
    print("\n--- 4. não lê a planilha a cada chamada, respeita o intervalo ---")
    fluxo = preparar(tempfile.mkdtemp(prefix="contador_uso_"))
    os.environ["COMPUTERNAME"] = "MAQUINA-A"
    fluxo.SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO = 9999  # bem no futuro

    fluxo._contar_uso_instagram()
    fluxo.situacao_da_conta()  # esta sincroniza (é a primeira, marca "quando")

    # Grava um "uso" de outra máquina DEPOIS da sincronia, direto na planilha.
    hoje = fluxo.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    SheetsFalso.linhas.append([hoje, "conta_teste_contador", "MAQUINA-B", "uso", "", ""])

    _pode, _motivo, usados, _r = fluxo.situacao_da_conta()
    conferir("ainda mostra 1: não releu a planilha antes do intervalo passar",
             usados == 1, str(usados))


def testar_planilha_nao_configurada_nao_afeta_o_contador_local():
    print("\n--- 5. sem a planilha de fechamentos configurada, o contador local continua sozinho ---")
    fluxo = preparar(tempfile.mkdtemp(prefix="contador_uso_"))
    fluxo._planilha_fechamentos_id = lambda: None
    os.environ["COMPUTERNAME"] = "MAQUINA-A"

    fluxo._contar_uso_instagram()
    fluxo._contar_uso_instagram()
    _pode, _motivo, usados, _r = fluxo.situacao_da_conta()
    conferir("segue contando só o local, sem quebrar", usados == 2, str(usados))
    conferir("e não gravou nada na aba (a planilha nem existe)",
             not SheetsFalso.linhas, str(SheetsFalso.linhas))


if __name__ == "__main__":
    computername_original = os.environ.get("COMPUTERNAME")
    try:
        testar_registra_evento_uso_ao_contar()
        testar_soma_entre_maquinas()
        testar_nunca_volta_pra_tras()
        testar_respeita_o_intervalo_de_sincronia()
        testar_planilha_nao_configurada_nao_afeta_o_contador_local()
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
