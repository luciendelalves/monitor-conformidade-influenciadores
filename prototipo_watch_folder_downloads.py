# -*- coding: utf-8 -*-
"""
Protótipo do "watch folder": simula o cenário em que uma ferramenta de
download de vídeo (usada pelo Marketing) salva um arquivo direto na pasta de
Downloads, e a automação identifica sozinha a qual influenciador/data ele
pertence a partir do nome do arquivo — e a partir daí sobe o vídeo pro Drive
e registra a linha na planilha da auditoria.

Fases:
  - Sem argumento: só detecta e loga (não sobe nada, não escreve em planilha).
  - Com "aplicar": além de detectar, sobe o vídeo pra uma pasta de TESTE no
    Drive (isolada, criada por este script, nunca mexe em pasta real do
    Marketing) e adiciona uma linha na planilha real da auditoria
    (AUDITORIA - VALIDAÇÃO MKT INFLU.xlsx, aba "Validação Regulatória de
    Publicações (SPA/+18)") — usando dados fictícios de teste, fáceis de
    filtrar e apagar depois (handle sempre reconhecível como teste).

Pasta monitorada: a pasta de Downloads real da máquina (a automação de
verdade agiria a partir do momento em que o arquivo aparece lá). Só arquivos
.mp4/.mov que baterem com um padrão de nome conhecido são processados;
qualquer outro arquivo do Downloads é ignorado (só o nome é lido, nunca o
conteúdo, e nada é movido/apagado da pasta original).

Uso:
    py prototipo_watch_folder_downloads.py            (simulação, só loga)
    py prototipo_watch_folder_downloads.py aplicar     (sobe pro Drive + grava na planilha)
"""
import csv
import os
import re
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_drive_credenciais"))

PASTA_BASE_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "teste_watch_folder")
PASTA_MONITORADA = os.path.join(os.path.expanduser("~"), "Downloads")
ARQUIVO_LOG = os.path.join(PASTA_BASE_LOG, "log_deteccoes.csv")
EXTENSOES_VIDEO = {".mp4", ".mov"}

NOME_PASTA_TESTE_DRIVE = "TESTE - Watch Folder - Não Usar"
PLANILHA_AUDITORIA_ID = "1Uzxi3K1o6Nq7bgUhLZNBIYm5Qw7hD9Y7FOtLxr4-V9w"
ABA_AUDITORIA = "Validação Regulatória de Publicações (SPA/+18)"

PADROES = [
    {
        "nome": "apostrofo_s_story",
        # ex: rafaelbarbosaof's2026-2-26-10.50.923 story.mp4
        "regex": re.compile(
            r"^(?P<handle>[a-zA-Z0-9_.]+)'s(?P<ano>\d{4})-(?P<mes>\d{1,2})-(?P<dia>\d{1,2})-\d{1,2}\.\d{1,2}\.\d+ story",
            re.IGNORECASE,
        ),
        "tipo": "STORIES",
    },
    {
        "nome": "underscore_numero_data",
        # ex: cassinha.161_3951472871360738423_2026-07-28.mp4
        "regex": re.compile(
            r"^(?P<handle>[a-zA-Z0-9_.]+?)_\d{10,}_(?P<ano>\d{4})-(?P<mes>\d{1,2})-(?P<dia>\d{1,2})",
        ),
        "tipo": None,  # esse padrão não permite inferir o tipo com segurança
    },
]


def identificar(nome_arquivo):
    base = os.path.splitext(nome_arquivo)[0]
    for padrao in PADROES:
        m = padrao["regex"].match(base)
        if m:
            g = m.groupdict()
            try:
                data = datetime(int(g["ano"]), int(g["mes"]), int(g["dia"]))
            except ValueError:
                continue
            return {
                "handle": "@" + g["handle"],
                "data": data.strftime("%Y-%m-%d"),
                "padrao": padrao["nome"],
                "tipo": padrao["tipo"] or "A CONFIRMAR",
            }
    return None


def carregar_ja_processados():
    if not os.path.exists(ARQUIVO_LOG):
        return set()
    with open(ARQUIVO_LOG, "r", encoding="utf-8", newline="") as f:
        return {linha["arquivo"] for linha in csv.DictReader(f)}


def gravar_log(linhas_novas):
    escreve_cabecalho = not os.path.exists(ARQUIVO_LOG)
    os.makedirs(PASTA_BASE_LOG, exist_ok=True)
    with open(ARQUIVO_LOG, "a", encoding="utf-8", newline="") as f:
        campos = ["arquivo", "handle_detectado", "data_detectada", "padrao_usado", "status", "link_drive", "processado_em"]
        writer = csv.DictWriter(f, fieldnames=campos)
        if escreve_cabecalho:
            writer.writeheader()
        writer.writerows(linhas_novas)


def main():
    aplicar = "aplicar" in sys.argv

    if not os.path.isdir(PASTA_MONITORADA):
        print(f"Pasta monitorada não encontrada: {PASTA_MONITORADA}")
        return

    ja_processados = carregar_ja_processados()
    arquivos = [
        f for f in os.listdir(PASTA_MONITORADA)
        if os.path.isfile(os.path.join(PASTA_MONITORADA, f)) and os.path.splitext(f)[1].lower() in EXTENSOES_VIDEO
    ]
    novos = [f for f in arquivos if f not in ja_processados]

    if not novos:
        print(f"Nenhum vídeo (.mp4/.mov) novo em {PASTA_MONITORADA}.")
        return

    id_pasta_teste = None
    if aplicar:
        import drive_client_upload
        import sheets_client
        id_pasta_teste = drive_client_upload.obter_ou_criar_pasta(NOME_PASTA_TESTE_DRIVE)
        print(f"Pasta de teste no Drive: '{NOME_PASTA_TESTE_DRIVE}' (id {id_pasta_teste})")

    linhas_log = []
    linhas_planilha = []
    for nome in novos:
        resultado = identificar(nome)
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not resultado:
            print(f"FALHA| {nome} -> não bateu com nenhum padrão conhecido (revisão manual necessária)")
            linhas_log.append({
                "arquivo": nome, "handle_detectado": "", "data_detectada": "",
                "padrao_usado": "", "status": "NÃO RECONHECIDO — revisão manual",
                "link_drive": "", "processado_em": agora,
            })
            continue

        print(f"OK   | {nome} -> handle={resultado['handle']} data={resultado['data']} tipo={resultado['tipo']} (padrão: {resultado['padrao']})")
        link_drive = ""
        status = "IDENTIFICADO (simulação, nada foi enviado)"

        if aplicar:
            caminho_completo = os.path.join(PASTA_MONITORADA, nome)
            _id_arquivo, link_drive = drive_client_upload.enviar_arquivo(caminho_completo, nome, id_pasta_teste)
            status = "IDENTIFICADO + ENVIADO AO DRIVE (teste)"
            print(f"       -> subiu pro Drive de teste: {link_drive}")

            ano = resultado["data"][:4]
            linhas_planilha.append([
                resultado["handle"], ano, resultado["data"], resultado["tipo"], link_drive,
            ])

        linhas_log.append({
            "arquivo": nome, "handle_detectado": resultado["handle"], "data_detectada": resultado["data"],
            "padrao_usado": resultado["padrao"], "status": status, "link_drive": link_drive,
            "processado_em": agora,
        })

    if aplicar and linhas_planilha:
        import sheets_client
        sheets_client.adicionar_linhas(PLANILHA_AUDITORIA_ID, ABA_AUDITORIA, "A:E", linhas_planilha)
        print(f"\n{len(linhas_planilha)} linha(s) gravada(s) na planilha da auditoria (aba '{ABA_AUDITORIA}').")

    gravar_log(linhas_log)
    print(f"\n{len(linhas_log)} arquivo(s) processado(s). Log atualizado em: {ARQUIVO_LOG}")
    if not aplicar:
        print("Modo simulação — nada foi enviado ao Drive nem gravado em planilha. Rode com 'aplicar' pra fazer de verdade.")


if __name__ == "__main__":
    main()
