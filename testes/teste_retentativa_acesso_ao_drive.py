# -*- coding: utf-8 -*-
"""
Um 404 logo depois do upload não pode virar "SEM ACESSO À PASTA" definitivo.

POR QUE ESTE TESTE EXISTE (22/09/2026)

Medido na Monitoramento de teste, com uma linha real da Responsável A: o vídeo
subiu ao Drive às 15:05:18 e a análise tentou lê-lo às 15:05, no mesmo
minuto, e levou 404. A linha 100, da MESMA pessoa, na MESMA máquina, com os
MESMOS tokens, analisada às 15:07, fechou CONFORME. O arquivo da primeira
abre normalmente pelo token de leitura quando consultado depois.

A CAUSA: o upload usa o token de ESCRITA (drive_file_token.json, escopo
drive.file) e a análise lê com o de LEITURA (drive_token.json, escopo
drive.readonly), que é outra autorização. O Google leva alguns segundos para
tornar um arquivo recém-criado visível para uma autorização diferente da que
o criou.

O QUE PIORAVA: `_com_retentativas`, em drive_client.py, só repete em erro de
rede (SSLError, ConnectionError, TimeoutError, OSError). HttpError não herda
de nenhum desses, então o 404 falhava de primeira. E como gravar_veredito só
escreve em célula vazia, a linha nunca mais era reanalisada sozinha: um
tropeço de segundos virava rótulo permanente numa planilha de auditoria.

Este teste não fala com o Drive: o buscador de material é um dublê, para a
regra de repetição poder ser conferida sem rede e sem cota.

Rodar:

    py testes\\teste_retentativa_acesso_ao_drive.py
"""
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import pipeline_influenciadores as pipeline
from googleapiclient.errors import HttpError

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def erro_http(status):
    resposta = type("Resp", (), {"status": status, "reason": "de mentira"})()
    return HttpError(resposta, b"{}")


LINHA = {"excel_row": 999, "tipo_link": "DRIVE_FILE",
         "drive_id": "id_de_mentira", "data": None}


def rodar():
    print("--- 1. só 404 e 403 contam como janela de propagação ---")
    for status, esperado in ((404, True), (403, True), (500, False), (400, False)):
        conferir(pipeline._e_janela_de_propagacao(erro_http(status)) is esperado,
                 f"status {status} repete? {esperado}")
    conferir(pipeline._e_janela_de_propagacao(ValueError("outra coisa")) is False,
             "erro que não é da API do Drive não repete")

    guardados = {
        "buscar": pipeline._buscar_material_do_drive,
        "midia": pipeline.MIDIA_DIR,
        "espera": pipeline.ESPERA_ENTRE_TENTATIVAS_S,
        "classificar": pipeline.motor.classificar_post,
    }
    pasta_tmp = tempfile.mkdtemp(prefix="teste_retentativa_")
    try:
        pipeline.MIDIA_DIR = pasta_tmp
        pipeline.ESPERA_ENTRE_TENTATIVAS_S = 0  # não dorme de verdade no teste
        pipeline.motor.classificar_post = lambda *a, **k: {
            "classificacao": "Conforme", "motivo": "", "evidencia": ""}

        print()
        print("--- 2. 404 na primeira, sucesso na segunda: analisa normal ---")
        tentativas = {"n": 0}

        def falha_uma_vez(linha, row_dir, arquivos, drive_id_por_nome):
            tentativas["n"] += 1
            if tentativas["n"] == 1:
                raise erro_http(404)
            arquivos.append(os.path.join(row_dir, "video.mp4"))
            drive_id_por_nome["video.mp4"] = "abc"

        pipeline._buscar_material_do_drive = falha_uma_vez
        r = pipeline.processar_linha(dict(LINHA))
        conferir(tentativas["n"] == 2, "tentou duas vezes", str(tentativas["n"]))
        conferir(r.get("classificacao") == "Conforme",
                 "e a segunda tentativa valeu, sem carimbar falha de acesso",
                 str(r.get("classificacao")) + " / " + str(r.get("motivo"))[:60])

        print()
        print("--- 3. 404 sempre: desiste depois do limite, e explica ---")
        tentativas["n"] = 0

        def falha_sempre(linha, row_dir, arquivos, drive_id_por_nome):
            tentativas["n"] += 1
            raise erro_http(404)

        pipeline._buscar_material_do_drive = falha_sempre
        r = pipeline.processar_linha(dict(LINHA))
        conferir(tentativas["n"] == pipeline.TENTATIVAS_ACESSO_DRIVE,
                 f"tentou {pipeline.TENTATIVAS_ACESSO_DRIVE} vezes antes de desistir",
                 str(tentativas["n"]))
        conferir("Falha ao acessar material" in str(r.get("motivo")),
                 "e o motivo continua sendo o de sempre, que vira SEM ACESSO À PASTA",
                 str(r.get("motivo"))[:80])

        print()
        print("--- 4. erro que NÃO é de propagação falha de primeira ---")
        tentativas["n"] = 0

        def erro_de_verdade(linha, row_dir, arquivos, drive_id_por_nome):
            tentativas["n"] += 1
            raise ValueError("id malformado")

        pipeline._buscar_material_do_drive = erro_de_verdade
        r = pipeline.processar_linha(dict(LINHA))
        conferir(tentativas["n"] == 1,
                 "não repete erro que não tem chance de melhorar sozinho",
                 str(tentativas["n"]))

        print()
        print("--- 5. pasta sem mídia continua sendo pasta vazia, não erro de acesso ---")
        tentativas["n"] = 0

        def nao_acha_nada(linha, row_dir, arquivos, drive_id_por_nome):
            tentativas["n"] += 1  # não acrescenta arquivo nenhum

        pipeline._buscar_material_do_drive = nao_acha_nada
        r = pipeline.processar_linha(dict(LINHA))
        conferir(tentativas["n"] == 1,
                 "pasta vazia não fica repetindo à toa", str(tentativas["n"]))
        conferir("pasta_vazia_ou_sem_midia" in str(r.get("motivo")),
                 "e continua sendo classificada como pasta vazia",
                 str(r.get("motivo"))[:80])

        print()
        print("--- 6. a mídia baixada é zerada entre tentativas ---")
        tentativas["n"] = 0
        vistos = []

        def deixa_lixo_e_falha(linha, row_dir, arquivos, drive_id_por_nome):
            tentativas["n"] += 1
            vistos.append(list(arquivos))
            arquivos.append(f"parcial_{tentativas['n']}.mp4")
            if tentativas["n"] < 3:
                raise erro_http(404)

        pipeline._buscar_material_do_drive = deixa_lixo_e_falha
        pipeline.processar_linha(dict(LINHA))
        conferir(all(v == [] for v in vistos),
                 "cada tentativa começa com a lista de arquivos vazia",
                 str(vistos))

    finally:
        pipeline._buscar_material_do_drive = guardados["buscar"]
        pipeline.MIDIA_DIR = guardados["midia"]
        pipeline.ESPERA_ENTRE_TENTATIVAS_S = guardados["espera"]
        pipeline.motor.classificar_post = guardados["classificar"]


if __name__ == "__main__":
    print("=" * 74)
    print("  Retentativa de acesso ao Drive na análise (janela de propagação)")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
