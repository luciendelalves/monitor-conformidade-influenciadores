# -*- coding: utf-8 -*-
"""
Manda para análise, NESTA máquina, linhas que outra máquina baixou e deixou
paradas.

POR QUE EXISTE (22/09/2026)

A Responsável B está testando o layout de Futebol na máquina dela, baixa normal, o
vídeo sobe para o Drive e a linha nasce na Monitoramento, mas a análise nunca
acontece: a linha fica em AGUARDANDO VALIDAÇÃO para sempre. Medido no mesmo
dia com a linha 108 (@crissevieri.mov), e o que ficou provado é que o problema
NÃO está na linha nem no arquivo: mandada para análise desta máquina, ela saiu
CONFORME em menos de três minutos.

O problema está na FILA LOCAL dela, e a fila não é compartilhada: cada
instalação tem a sua, em arquivo. Daqui não dá para ver nem consertar a fila
de lá. Enquanto a causa de lá não é achada, isto aqui é a ponte: ela continua
testando o download sem ninguém mexer na máquina dela, e a análise roda aqui.

UMA SAÍDA SILENCIOSA QUE PODE SER A CAUSA, e que este programa também evita:
`enfileirar_analise` pula, sem dizer nada, qualquer vídeo cujo link já apareça
como pendente ou rodando na fila local. Tarefa presa nesse estado descarta em
silêncio toda tentativa seguinte daquele vídeo, para sempre. Aqui isso é
mostrado na tela em vez de ser engolido.

POR QUE VARRER PENDENTES NÃO ERA FEITO ANTES, e por que passou a ser

`enfileirar_analise` manda só as linhas do lote que acabou de baixar, e o
comentário dela diz o porquê: varrer tudo o que está pendente pegaria linha
antiga que alguém deixou de lado de propósito. Isso continua valendo, e é por
isso que aqui NADA acontece sem `--aplicar`, a lista do que vai ser mandado
aparece antes, e a varredura olha só os últimos dias (ver DIAS_PADRAO). Quem
pediu a varredura foi o auditor, em 22/09/2026, para a Responsável B não ficar
parada até sexta.

O QUE ESTE PROGRAMA NÃO FAZ

- Não escreve nada na planilha. Ele só cria tarefa na fila DESTA máquina; quem
  grava o veredito continua sendo o trabalhador, e só em célula vazia.
- Não gasta chamada do Instagram. O material já está no Drive.
- Não mexe em linha que já tem veredito, nem em linha marcada como sem
  arquivo.

PRECISA DO TRABALHADOR DE PÉ nesta máquina, senão a tarefa fica na fila
esperando. O programa avisa quando ele não está.

Uso:

    py analisar_pendentes.py                    mostra o que faria
    py analisar_pendentes.py --aplicar          manda para a fila
    py analisar_pendentes.py --dias 30          olha mais para trás
    py analisar_pendentes.py --de @crissevieri  só de um influenciador
    py analisar_pendentes.py --quem todos       não só as linhas da Responsável B
    py analisar_pendentes.py --aplicar --vigiar 10
                                                confere a cada 10 minutos

POR PADRÃO SÓ VARRE AS LINHAS DA RESPONSÁVEL B (ver QUEM_PADRAO). O fluxo da Responsável A
analisa normal, e varrer o dela seria mexer no que está funcionando.
"""
import os
import sys
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fila_trabalho
import fluxo_downloads as fluxo
import pipeline_influenciadores as pipeline

# Quantos dias para trás a varredura olha por padrão. Curto de propósito: o
# que é antigo disso tem chance de ter sido deixado de lado por alguém, e
# mandar para análise sozinho desfaria uma decisão humana sem perguntar.
DIAS_PADRAO = 7

# SÓ AS LINHAS DE QUEM ESTÁ COM PROBLEMA (22/09/2026, pedido do auditor).
#
# O fluxo da Responsável A analisa normal, e varrer as linhas dela seria mexer no que
# está funcionando: linha que ela deixou sem veredito pode ter sido decisão
# dela. Quem não analisa é a máquina da Responsável B, e é só o que esta varredura
# alcança por padrão. A coluna PEDIDO_POR da Monitoramento é quem diz de quem
# é cada linha.
#
# ISTO É PROVISÓRIO, e a data importa: vale enquanto a causa na máquina dela
# não for achada, para ela não ficar parada até sexta, 25/09/2026. Achada a
# causa, este programa deixa de ser necessário.
#
# Para varrer todo mundo:  --quem todos
# O valor aqui precisa ser um trecho que apareça dentro do e-mail de quem
# pediu o download (coluna PEDIDO_POR), não o nome por extenso.
QUEM_PADRAO = "responsavel.b"


def _data_do_download(linha):
    """A data em que o material foi capturado, ou None quando não dá para ler.

    NUNCA COMPARAR DATA COMO TEXTO neste projeto: `06/09/2026` volta do Sheets
    como `06/09/26`, e os dois formatos convivem na mesma coluna."""
    texto = str(linha.get("data_download") or "").strip()
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def pendentes_para_analisar(linhas, ja_na_fila=(), dias=DIAS_PADRAO, de=None,
                            hoje=None, quem=QUEM_PADRAO):
    """Quais linhas estão esperando análise e ainda não foram mandadas.

    Separado do resto de propósito, para o teste poder conferir a regra sem
    falar com planilha nenhuma. Devolve (para_mandar, presas), onde `presas`
    são as que já constam na fila desta máquina: elas não podem ser mandadas
    de novo, e é justamente nelas que mora a falha silenciosa que este
    programa existe para mostrar.

    Agrupa por link, como `enfileirar_analise` faz: um post pode ocupar mais
    de uma linha da planilha (carrossel), e todas precisam do mesmo veredito.
    """
    hoje = hoje or datetime.now().date()
    limite = hoje - timedelta(days=dias)
    ja_na_fila = set(ja_na_fila)
    procurado = (de or "").strip().lstrip("@").lower()
    de_quem = (quem or "").strip().lower()
    if de_quem == "todos":
        de_quem = ""

    por_link = {}
    for linha in linhas:
        if str(linha.get("veredito_na_planilha") or "").strip():
            continue  # já tem veredito, e o programa só escreve em célula vazia
        if not fluxo.tem_arquivo_para_analisar(linha.get("situacao")):
            continue  # linha sem arquivo para conferir
        link = str(linha.get("link") or "").strip()
        if not link:
            continue
        # Linha sem PEDIDO_POR fica de fora quando há filtro de pessoa: é linha
        # antiga ou preenchida à mão, e não dá para afirmar de quem é.
        if de_quem and de_quem not in str(linha.get("pedido_por") or "").lower():
            continue
        if procurado and procurado not in str(
                linha.get("influenciador") or "").lstrip("@").lower():
            continue
        quando = _data_do_download(linha)
        # Sem data legível, entra: é linha da automação sem carimbo, e deixar
        # de fora silenciosamente seria o mesmo tipo de sumiço que este
        # programa existe para acabar.
        if quando and quando < limite:
            continue
        por_link.setdefault(link, []).append(linha)

    para_mandar, presas = {}, {}
    for link, do_link in por_link.items():
        (presas if link in ja_na_fila else para_mandar)[link] = do_link
    return para_mandar, presas


def _uma_passada(dias, de, aplicar, quem=QUEM_PADRAO):
    linhas = pipeline.carregar_monitoramento()
    para_mandar, presas = pendentes_para_analisar(
        linhas, fila_trabalho.links_em_andamento(), dias=dias, de=de, quem=quem)

    if presas:
        print()
        print(f"{len(presas)} vídeo(s) JÁ ESTÃO na fila desta máquina, e por isso")
        print("não podem ser mandados de novo:")
        for do_link in presas.values():
            p = do_link[0]
            print(f"   linha {p['excel_row']:>4}  {p['influenciador']}  "
                  f"(esperando a fila daqui)")

    if not para_mandar:
        print()
        print("Nenhuma linha nova esperando análise.")
        return 0

    print()
    print(f"{len(para_mandar)} vídeo(s) esperando análise:")
    for do_link in para_mandar.values():
        p = do_link[0]
        linhas_txt = ", ".join(str(l["excel_row"]) for l in do_link)
        print(f"   linha {linhas_txt:>8}  {p['influenciador']:<24} "
              f"{p['data'] or 'sem data'}  baixado em "
              f"{p.get('data_download') or 'sem data'}")

    if not aplicar:
        print()
        print("Nada foi feito. Para mandar de verdade:  py analisar_pendentes.py --aplicar")
        return 0

    if not fila_trabalho.trabalhador_de_pe():
        print()
        print("ATENÇÃO: o trabalhador desta máquina não está de pé. As tarefas")
        print("ficam na fila esperando até alguém subir iniciar_trabalhador.bat.")

    quantas = 0
    for link, do_link in para_mandar.items():
        fila_trabalho.criar(
            fila_trabalho.VALIDAR,
            {"link": link,
             "excel_rows": [l["excel_row"] for l in do_link],
             "linha": do_link[0]},
            rotulo=f"{do_link[0]['influenciador']} · {do_link[0]['data'] or 'sem data'}",
            criada_por="analisar_pendentes (outra máquina baixou)")
        quantas += 1
    print()
    print(f"{quantas} vídeo(s) foram para a fila de análise desta máquina.")
    return quantas


def main():
    argumentos = sys.argv[1:]
    aplicar = "--aplicar" in argumentos

    def valor(nome, padrao):
        if nome in argumentos:
            posicao = argumentos.index(nome) + 1
            if posicao < len(argumentos):
                return argumentos[posicao]
        return padrao

    dias = int(valor("--dias", DIAS_PADRAO))
    de = valor("--de", None)
    quem = valor("--quem", QUEM_PADRAO)
    vigiar = valor("--vigiar", None)

    print("=" * 70)
    print("  Linhas esperando análise, baixadas em outra máquina")
    print("=" * 70)
    de_quem = "todo mundo" if str(quem).lower() == "todos" else f"quem baixou tem '{quem}' no nome"
    print(f"  últimos {dias} dia(s), {de_quem}" + (f", só de {de}" if de else ""))

    if not vigiar:
        _uma_passada(dias, de, aplicar, quem)
        return

    import time
    minutos = int(vigiar)
    print(f"  conferindo a cada {minutos} minuto(s). Ctrl+C para parar.")
    while True:
        print()
        print(f"--- {datetime.now():%H:%M:%S} ---")
        try:
            _uma_passada(dias, de, aplicar, quem)
        except Exception as e:
            # Uma falha de leitura não pode derrubar a vigia: ela existe
            # justamente para rodar sozinha enquanto ninguém olha.
            print(f"não consegui conferir agora: {str(e)[:160]}")
        time.sleep(minutos * 60)


if __name__ == "__main__":
    main()
