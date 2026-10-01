# -*- coding: utf-8 -*-
r"""
Reproduz de propósito, contra a CÓPIA DE TESTE da Monitoramento, a corrida
entre duas instalações em máquinas físicas diferentes escrevendo ao mesmo
tempo (18/09/2026).

FICA NA RAIZ, E NÃO EM `ferramentas\`, DE PROPÓSITO: as ferramentas daquela
pasta são de conferência, só leem, e `teste_ferramentas_de_conferencia.py`
prova isso (só `limpar_teste.py` escreve, e é regra do projeto). Este script
ESCREVE de propósito, para reproduzir a corrida, então mora ao lado de
`verificar_ambiente.py` e `preparar_copia.py`, que também são utilitários
manuais fora das duas pastas com regra própria.

POR QUE ESTE SCRIPT EXISTE

A trava de 16/09 (RLock) e a de 18/09 (trava.travar, arquivo em
%ProgramData%) só valem dentro de uma máquina. Responsável A e Responsável B, hoje,
escrevem na MESMA Monitoramento real de máquinas diferentes, então nenhuma
das duas travas as protege uma da outra. A correção (reler a linha depois de
escrever, e tentar de novo se vier diferente) precisa ser provada contra a
API de verdade, não só estruturalmente, antes de confiar nela na planilha
real.

COMO REPRODUZ SEM DUAS MÁQUINAS DE VERDADE

Sobe DOIS PROCESSOS separados (não threads: o ponto é que cada RLock e cada
trava de arquivo vive só no seu próprio processo). Cada um recebe um
%ProgramData% FALSO e DIFERENTE do outro, então a trava de 18/09 não os
protege um do outro, exatamente como não protegeria dois computadores
físicos distintos. Os dois também recebem
AUDITORIA_TESTE_ATRASO_CORRIDA_MONITORAMENTO, que alarga de propósito a
janela entre ler e escrever dentro de registrar_na_monitoramento (inerte
fora deste teste, ver o comentário da variável no próprio fluxo_downloads.py)
para a colisão acontecer sempre, em vez de depender da sorte do tempo de
rede.

O QUE PROVA sucesso: as DUAS linhas aparecem na Monitoramento de teste, cada
uma com o handle e o link que o processo correspondente mandou, sem uma
sobrescrever a outra. Se a proteção não existisse, o cenário normal seria as
duas calcularem a mesma próxima linha e uma delas desaparecer caladamente.

LIMPEZA: o script apaga as duas linhas de teste no final, com
ferramentas\limpar_teste.py, e avisa se algo não puder ser limpo.

USO

    py testar_corrida_entre_maquinas.py

ENCERRE O TRABALHADOR ANTES DE RODAR (mesma regra de sempre): ele guarda o
código antigo em memória, e senão este teste avalia a correção certa contra
um processo que ainda não a tem.
"""
import os
import subprocess
import sys
import tempfile
import time
import uuid

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

MARCA = uuid.uuid4().hex[:8]
HANDLE_A = f"@testecorrida{MARCA}a"
HANDLE_B = f"@testecorrida{MARCA}b"
LINK_A = f"https://teste.invalido/corrida/{MARCA}/a"
LINK_B = f"https://teste.invalido/corrida/{MARCA}/b"
ATRASO_SEGUNDOS = "4"

_SCRIPT_FILHO = r"""
import os, sys
sys.path.insert(0, {base!r})
sys.path.append(os.path.join({base!r}, "_drive_credenciais"))
import fluxo_downloads as fluxo
try:
    numero = fluxo.registrar_na_monitoramento(
        handle={handle!r}, data_video=None, rotulo_ciclo="TESTE CORRIDA",
        link_drive={link!r}, marca="TESTE", tipo="STORY", analisavel=False,
        pedido_por="teste_corrida")
    print("RESULTADO:" + str(numero))
except Exception as e:
    print("ERRO:" + repr(e))
"""


def _subir_processo(handle, link, pasta_program_data):
    os.makedirs(pasta_program_data, exist_ok=True)
    ambiente = dict(os.environ)
    ambiente["ProgramData"] = pasta_program_data
    ambiente["AUDITORIA_TESTE_ATRASO_CORRIDA_MONITORAMENTO"] = ATRASO_SEGUNDOS
    ambiente["PYTHONIOENCODING"] = "utf-8"
    codigo = _SCRIPT_FILHO.format(base=BASE, handle=handle, link=link)
    return subprocess.Popen(
        ["py", "-c", codigo], cwd=BASE, env=ambiente,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8")


def rodar():
    import fluxo_downloads as fluxo
    import sheets_client

    planilha = fluxo._planilha_monitoramento_id()
    if not planilha:
        print("[ FALHA] a cópia de teste da Monitoramento não está configurada "
              "(teste_watch_folder\\monitoramento_teste_id.txt). Sem ela não dá "
              "para testar nada.")
        return 1

    tmp_a = os.path.join(tempfile.gettempdir(), f"maquina_falsa_a_{MARCA}")
    tmp_b = os.path.join(tempfile.gettempdir(), f"maquina_falsa_b_{MARCA}")

    print("=" * 74)
    print("  Reprodução: duas máquinas diferentes escrevendo ao mesmo tempo")
    print("=" * 74)
    print(f"  handle A: {HANDLE_A}   handle B: {HANDLE_B}")
    print(f"  %ProgramData% falso A: {tmp_a}")
    print(f"  %ProgramData% falso B: {tmp_b}")
    print("  Disparando os dois processos, um atrás do outro, sem esperar...")
    print()

    p_a = _subir_processo(HANDLE_A, LINK_A, tmp_a)
    p_b = _subir_processo(HANDLE_B, LINK_B, tmp_b)

    saida_a, _ = p_a.communicate(timeout=60)
    saida_b, _ = p_b.communicate(timeout=60)

    print("  --- saída do processo A ---")
    print(" ", saida_a.strip().replace("\n", "\n  "))
    print("  --- saída do processo B ---")
    print(" ", saida_b.strip().replace("\n", "\n  "))
    print()

    atuais = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().get(
        spreadsheetId=planilha,
        range=f"'{fluxo.ABA_MONITORAMENTO}'!A2:{fluxo.ULTIMA_COLUNA_MON}20000").execute()).get("values", [])

    i_handle = fluxo.COL_MON["handle"] - 1
    i_arquivo = fluxo.COL_MON["arquivo"] - 1

    achou_a = any(len(l) > i_arquivo and l[i_handle] == HANDLE_A and l[i_arquivo] == LINK_A for l in atuais)
    achou_b = any(len(l) > i_arquivo and l[i_handle] == HANDLE_B and l[i_arquivo] == LINK_B for l in atuais)

    falhou = False
    if achou_a and achou_b:
        print("[  ok  ] as DUAS linhas existem na Monitoramento de teste, cada uma com o "
              "próprio conteúdo, nenhuma sobrescreveu a outra.")
    else:
        falhou = True
        print("[ FALHA] pelo menos uma linha se perdeu:")
        print(f"           handle A ({HANDLE_A}) apareceu? {achou_a}")
        print(f"           handle B ({HANDLE_B}) apareceu? {achou_b}")

    print()
    print("  Limpando as linhas de teste...")
    pasta_ferramentas = os.path.join(BASE, "ferramentas")
    for h in (HANDLE_A, HANDLE_B):
        r = subprocess.run(["py", "limpar_teste.py", h], cwd=pasta_ferramentas,
                            capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            print(f"  [aviso] limpeza de {h} terminou com código {r.returncode}, "
                  f"confira à mão: {(r.stdout or '')[-300:]} {(r.stderr or '')[-300:]}")
        else:
            print(f"  [ok] {h} limpo")

    print()
    print("=" * 74)
    print("  FALHOU." if falhou else "  PASSOU.")
    print("=" * 74)
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(rodar())
