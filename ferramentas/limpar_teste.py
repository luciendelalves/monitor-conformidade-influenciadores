# -*- coding: utf-8 -*-
r"""
A ÚNICA FERRAMENTA DESTA PASTA QUE ESCREVE. Zera registros para um novo teste.

    py ferramentas\limpar_teste.py conferir           mostra o que existe, sem apagar
    py ferramentas\limpar_teste.py tudo               apaga tudo
    py ferramentas\limpar_teste.py @maumauzk          apaga só o material dele

O QUE APAGA

    o material do Drive DE TESTE, para a LIXEIRA (30 dias para voltar)
    as linhas da Monitoramento DE TESTE
    as linhas da fila de downloads
    o log de fluxo, com cópia de segurança antes            (só no modo `tudo`)
    o cache de análise, com cópia de segurança antes        (só no modo `tudo`)
    o histórico de tarefas concluídas do trabalhador        (só no modo `tudo`)

O QUE **NUNCA** APAGA, E O MOTIVO

    A CONTAGEM DE CHAMADAS DO INSTAGRAM DO DIA. É a proteção que impede conta
    marcada, e foi repetição de chamada que marcou duas contas em agosto de 2026.
    Zerar isso é a única coisa nesta área que causa dano de verdade.

    O MAPA DE PERFIS (instagram_userids.json). Redescobrir cada número é a
    chamada mais cara e arriscada do programa, e ele não é registro de teste: é
    conhecimento acumulado.

    Credenciais, identificadores e o arquivo da conta do Instagram.

ANTES DE RODAR: ENCERRE O TRABALHADOR E A TELA.

Não é formalidade. O trabalhador guarda em memória os identificadores das pastas
do Drive. Com ele de pé, o próximo download depois da limpeza subiria PARA DENTRO
DA LIXEIRA, e o arquivo pareceria ter sumido. Esta ferramenta avisa se detectar o
trabalhador ativo, mas quem decide parar é você.
"""
import csv
import json
import os
import shutil
import sys
from datetime import datetime

from _base import (cabecalho, confirmar_drive_de_teste, contagem, linha,
                   pedir_argumento, secao)

import fluxo_downloads as fluxo
import pipeline_influenciadores as pipeline

BACKUP = os.path.join(fluxo.PASTA_TESTE, "backup_antes_de_limpar")


def titulo_da_planilha(planilha):
    import sheets_client
    meta = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().get(
            spreadsheetId=planilha, fields="properties(title)").execute())
    return meta.get("properties", {}).get("title") or ""


def exigir_planilha_de_teste():
    planilha = fluxo._planilha_monitoramento_id()
    if not planilha:
        raise SystemExit("RECUSADO: identificador da Monitoramento não configurado.")
    titulo = titulo_da_planilha(planilha)
    if "TESTE" not in titulo.upper():
        raise SystemExit(f"RECUSADO: a planilha {titulo!r} não tem TESTE no nome.")
    return planilha, titulo


def trabalhador_ativo():
    caminho = os.path.join(fluxo.PASTA_TESTE, "fila_trabalho", "trabalhador.json")
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, encoding="utf-8") as f:
            estado = json.load(f)
    except Exception:
        return None
    visto = estado.get("atualizado_em") or ""
    fazendo = estado.get("fazendo_agora") or []
    # O trabalhador reescreve esse arquivo com frequência. Se a marca de tempo é
    # de hoje e há algo em "fazendo agora", ele está trabalhando de verdade.
    hoje = datetime.now().strftime("%Y-%m-%d")
    if visto.startswith(hoje):
        return {"visto": visto, "fazendo": fazendo, "pid": estado.get("pid")}
    return None


def guardar_copia(caminho, rotulo):
    if not os.path.exists(caminho):
        return
    os.makedirs(BACKUP, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(BACKUP, f"{marca}_{os.path.basename(caminho)}")
    shutil.copy2(caminho, destino)
    linha(f"cópia de {rotulo}", destino, recuo=6)


def modo_conferir():
    raiz, nome_raiz = confirmar_drive_de_teste()
    planilha, titulo = exigir_planilha_de_teste()
    cabecalho("O que existe hoje (nada será apagado)")
    linha("Drive de teste", nome_raiz)
    linha("planilha", titulo)

    import drive_client_upload as dcu
    import sheets_client

    secao("Drive")
    pastas = dcu.listar_arquivos(raiz, so_pastas=True)
    linha("pastas no primeiro nível", f"{len(pastas)}  {[p['name'] for p in pastas]}")

    secao("planilha")
    valores = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha,
            range=f"'{fluxo.ABA_MONITORAMENTO}'!A2:{fluxo.ULTIMA_COLUNA_MON}20000",
        ).execute()).get("values", [])
    linha("linhas de dados", len(valores))

    secao("fila, log e cache")
    try:
        linha("linhas na fila", len(fluxo.ler_fila()))
    except Exception as e:
        linha("fila", f"não li: {str(e)[:70]}")
    if os.path.exists(fluxo.ARQUIVO_LOG):
        with open(fluxo.ARQUIVO_LOG, encoding="utf-8-sig", newline="") as f:
            linha("registros no log", len(list(csv.DictReader(f))))
    linha("entradas no cache", len(pipeline.carregar_cache()))

    secao("o que NÃO seria apagado")
    _p, _m, usados, restantes = fluxo.situacao_da_conta()
    linha("chamadas ao Instagram hoje", f"usadas {usados}, restam {restantes}")
    linha("conta configurada", "@" + fluxo.USUARIO_DOS_COOKIES)
    linha("perfis com número guardado", len(fluxo._ler_userids()))

    ativo = trabalhador_ativo()
    if ativo:
        secao("ATENÇÃO")
        print(f"   O trabalhador deu sinal de vida em {ativo['visto']} "
              f"(processo {ativo['pid']}).")
        if ativo["fazendo"]:
            print(f"   E está trabalhando agora em: {ativo['fazendo']}")
        print("   Encerre ele antes de limpar. Com ele de pé, o próximo download")
        print("   depois da limpeza sobe PARA DENTRO DA LIXEIRA.")


def limpar_drive(raiz):
    """De dentro para fora, item por item.

    Mandar a pasta de cima falha com 403 quando ela tem filho que o programa não
    criou: o token de escrita é do escopo drive.file. Item por item, o que ele
    criou vai para a lixeira e o resto é apenas relatado, que é melhor que a
    operação inteira falhar."""
    import drive_client_upload as dcu
    feitos = {"pastas": 0, "arquivos": 0}
    recusados = []

    def descer(id_pasta, caminho):
        for arquivo in dcu.listar_arquivos(id_pasta):
            try:
                dcu.mandar_para_lixeira(arquivo["id"])
                feitos["arquivos"] += 1
            except Exception as e:
                recusados.append((f"{caminho}/{arquivo['name']}", str(e)[:70]))
        for sub in dcu.listar_arquivos(id_pasta, so_pastas=True):
            descer(sub["id"], f"{caminho}/{sub['name']}")
            try:
                dcu.mandar_para_lixeira(sub["id"])
                feitos["pastas"] += 1
                print(f"      lixeira: {caminho}/{sub['name']}")
            except Exception as e:
                recusados.append((f"{caminho}/{sub['name']}", str(e)[:70]))

    descer(raiz, "")
    linha("para a lixeira", f"{feitos['pastas']} pasta(s), {feitos['arquivos']} arquivo(s)",
          recuo=6)
    if recusados:
        linha("recusados pelo Google", len(recusados), recuo=6)
        for caminho, _erro in recusados[:8]:
            print(f"         {caminho}")
        print("         (o token só alcança o que o programa criou;")
        print("          o resto se apaga pela mão, no Drive)")
    return feitos, recusados


def modo_tudo():
    raiz, nome_raiz = confirmar_drive_de_teste()
    planilha, titulo = exigir_planilha_de_teste()
    ativo = trabalhador_ativo()
    cabecalho("LIMPANDO TUDO", f"{nome_raiz}  |  {titulo}")
    if ativo and ativo["fazendo"]:
        raise SystemExit(
            f"RECUSADO: o trabalhador está trabalhando agora em {ativo['fazendo']}.\n"
            f"Encerre ele e rode de novo. Com ele de pé, o próximo download\n"
            f"depois da limpeza sobe para dentro da lixeira.")
    if ativo:
        print(f"   AVISO: o trabalhador deu sinal de vida em {ativo['visto']}, "
              f"mas está ocioso.")
        print("   Se ele ainda estiver de pé, encerre e suba de novo depois.")
        print()

    import sheets_client

    secao("cópias de segurança")
    guardar_copia(fluxo.ARQUIVO_LOG, "log de fluxo")
    guardar_copia(pipeline.CACHE_PATH, "cache de análise")

    secao("Drive de teste")
    limpar_drive(raiz)

    secao("planilha de Monitoramento de teste")
    valores = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha,
            range=f"'{fluxo.ABA_MONITORAMENTO}'!A2:{fluxo.ULTIMA_COLUNA_MON}20000",
        ).execute()).get("values", [])
    linhas = list(range(2, len(valores) + 2))
    if linhas:
        apagadas = sheets_client.apagar_linhas(planilha, fluxo.ABA_MONITORAMENTO, linhas)
        linha("linhas apagadas", f"{apagadas} (cabeçalho preservado)", recuo=6)
    else:
        linha("linhas apagadas", "já estava vazia", recuo=6)

    secao("fila de downloads")
    linha("linhas apagadas", fluxo.limpar_fila(), recuo=6)

    secao("log de fluxo")
    if os.path.exists(fluxo.ARQUIVO_LOG):
        with open(fluxo.ARQUIVO_LOG, encoding="utf-8-sig", newline="") as f:
            leitor = csv.DictReader(f)
            campos = leitor.fieldnames or fluxo.CAMPOS_LOG
            antes = len(list(leitor))
        with open(fluxo.ARQUIVO_LOG, "w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=campos).writeheader()
        linha("registros retirados", f"{antes} (cabeçalho preservado)", recuo=6)

    secao("cache de análise")
    antes = len(pipeline.carregar_cache())
    with open(pipeline.CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f)
    linha("entradas apagadas", antes, recuo=6)

    secao("histórico de tarefas do trabalhador")
    concluida = os.path.join(fluxo.PASTA_TESTE, "fila_trabalho", "concluida")
    if os.path.isdir(concluida):
        arquivos = [f for f in os.listdir(concluida) if f.endswith(".json")]
        for nome in arquivos:
            os.remove(os.path.join(concluida, nome))
        linha("tarefas apagadas", len(arquivos), recuo=6)

    secao("o que NÃO foi tocado")
    _p, _m, usados, restantes = fluxo.situacao_da_conta()
    linha("chamadas ao Instagram hoje", f"usadas {usados}, restam {restantes}", recuo=6)
    linha("conta configurada", "@" + fluxo.USUARIO_DOS_COOKIES, recuo=6)
    linha("perfis com número guardado", len(fluxo._ler_userids()), recuo=6)

    print()
    print("   SUBA O TRABALHADOR E A TELA DE NOVO antes de testar.")


def modo_um(alvo):
    confirmar_drive_de_teste()
    exigir_planilha_de_teste()
    ativo = trabalhador_ativo()
    if ativo and ativo["fazendo"]:
        raise SystemExit(f"RECUSADO: o trabalhador está ocupado com {ativo['fazendo']}.")
    chave = fluxo.chave_de_pasta(alvo)
    cabecalho(f"Limpando o material de @{chave}")
    arquivos, linhas_apagadas = fluxo.remover_material_de_teste([chave])
    linha("itens para a lixeira no Drive", arquivos)
    linha("linhas apagadas da Monitoramento", linhas_apagadas)
    print()
    print("   O log e o cache NÃO foram tocados neste modo. Para zerar tudo,")
    print("   use o modo `tudo`.")


if __name__ == "__main__":
    modo = pedir_argumento(1, "conferir", "modo (conferir, tudo, @influenciador)")
    if modo == "conferir":
        modo_conferir()
    elif modo == "tudo":
        modo_tudo()
    else:
        modo_um(modo)
