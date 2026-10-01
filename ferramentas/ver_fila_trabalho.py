# -*- coding: utf-8 -*-
r"""
O que está na fila LOCAL desta máquina, tarefa por tarefa.

POR QUE ESTA FERRAMENTA EXISTE (24/09/2026)

A máquina da Responsável B baixa normal, mas a análise nunca acontece, e a linha
fica em AGUARDANDO VALIDAÇÃO para sempre (achado em 21/09, ver a memória do
caso). Provado em 22/09 que não é a linha, o arquivo, nem o motor: mandada
para análise DESTA máquina, a mesma peça saiu CONFORME em minutos. O
problema está na fila local dela, que este projeto não consegue ver de
outro lugar (cada instalação tem a sua, em arquivo).

A PRINCIPAL SUSPEITA, ainda sem confirmação: `enfileirar_analise` (em
`fluxo_downloads.py`) pula, EM SILÊNCIO, qualquer vídeo cujo link já
apareça como pendente ou rodando na fila local
(`fila_trabalho.links_em_andamento()`). Uma tarefa VALIDAR que ficou presa
em "rodando" (o trabalhador caiu no meio de uma análise e nunca mais
reiniciou depois disso) bloqueia para sempre qualquer nova tentativa
daquele mesmo vídeo, porque a tarefa nunca chega a CONCLUIDA nem a FALHA.
`fila_trabalho.recuperar_orfas()` desprende isso, mas SÓ RODA NO INÍCIO do
trabalhador (`trabalhador.main`), então não ajuda se o processo nunca foi
reiniciado desde que a tarefa travou.

O QUE ESTA FERRAMENTA MOSTRA, para provar ou descartar essa suspeita sem
adivinhar: toda tarefa VALIDAR pendente, rodando, e as últimas terminadas
(certas e com falha), com quando entrou, quando começou (se rodando) e há
quanto tempo está lá. Uma tarefa "rodando" há mais de
MINUTOS_RODANDO_SUSPEITO é destacada, porque a análise de verdade leva
poucos minutos (medido em 22/09: saiu em menos de três).

Só leitura, mesma regra de toda ferramenta desta pasta. Não fala com o
Instagram nem com o Drive, só com os arquivos da fila local.

Uso, na máquina que se quer diagnosticar (a Responsável B roda isto NA DELA,
não daqui):

    py ferramentas\ver_fila_trabalho.py
"""
from _base import cabecalho, linha, secao

import os
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

# Medido em 22/09/2026: a análise real da linha 108 saiu CONFORME em menos
# de três minutos. Passar bem disso numa tarefa "rodando" é sinal de tarefa
# presa, não de análise lenta.
MINUTOS_RODANDO_SUSPEITO = 10


def _ha_quanto_tempo(texto_data):
    if not texto_data:
        return None
    try:
        quando = datetime.strptime(texto_data, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    minutos = (datetime.now() - quando).total_seconds() / 60
    return minutos


def _mostrar_tarefa(tarefa, mostrar_duracao=False):
    rotulo = tarefa.get("rotulo") or "(sem rótulo)"
    criada_por = tarefa.get("criada_por") or "?"
    criada_em = tarefa.get("criada_em") or "?"
    link = (tarefa.get("dados") or {}).get("link") or ""
    print(f"      {rotulo}")
    print(f"         criada por {criada_por}, em {criada_em}")
    if link:
        print(f"         link: {link}")
    if mostrar_duracao:
        comecou = tarefa.get("comecou_em")
        minutos = _ha_quanto_tempo(comecou)
        if minutos is not None:
            aviso = "  <<< SUSPEITA: rodando há tempo demais" if minutos > MINUTOS_RODANDO_SUSPEITO else ""
            print(f"         rodando desde {comecou} ({minutos:.0f} minuto(s)){aviso}")


def rodar():
    import fila_trabalho as fila

    cabecalho("Fila de trabalho DESTA máquina",
              f"pasta: {fila.PASTA_FILA}")

    de_pe, sinal = fila.trabalhador_de_pe()
    secao("o trabalhador está de pé, nesta máquina, agora?")
    linha("de pé", "sim" if de_pe else "NÃO")
    if sinal:
        linha("último sinal de vida", sinal.get("atualizado_em") or "?")
        linha("fazendo agora", sinal.get("fazendo_agora") or [])
    if not de_pe:
        print("      Sem o trabalhador de pé, nenhuma tarefa PENDENTE vai andar,")
        print("      mas isso não explica uma tarefa presa em RODANDO: essa só")
        print("      volta para PENDENTE quando o trabalhador reinicia de verdade.")

    secao("tarefas VALIDAR pendentes (esperando o trabalhador pegar)")
    pendentes = fila.listar(fila.PENDENTE, fila.VALIDAR)
    linha("quantas", len(pendentes))
    for tarefa in pendentes:
        _mostrar_tarefa(tarefa)

    secao("tarefas VALIDAR rodando agora")
    rodando = fila.listar(fila.RODANDO, fila.VALIDAR)
    linha("quantas", len(rodando))
    suspeitas = 0
    for tarefa in rodando:
        _mostrar_tarefa(tarefa, mostrar_duracao=True)
        minutos = _ha_quanto_tempo(tarefa.get("comecou_em"))
        if minutos is not None and minutos > MINUTOS_RODANDO_SUSPEITO:
            suspeitas += 1
    if suspeitas:
        print()
        print(f"      >>> {suspeitas} tarefa(s) rodando há mais de "
              f"{MINUTOS_RODANDO_SUSPEITO} minutos. Isto é o padrão exato "
              f"que faz enfileirar_analise pular o mesmo vídeo para sempre, "
              f"em silêncio: o link continua em fila_trabalho.links_em_andamento() "
              f"até essa tarefa terminar ou o trabalhador reiniciar "
              f"(recuperar_orfas só roda na abertura dele).")

    secao("últimas tarefas VALIDAR terminadas (certas e com falha)")
    for tarefa in fila.ultimas_terminadas(fila.VALIDAR, quantas=10):
        situacao = tarefa.get("situacao") or "?"
        print(f"      [{situacao}] ", end="")
        _mostrar_tarefa(tarefa)
        if situacao == fila.FALHA:
            print(f"         erro: {str(tarefa.get('erro') or '')[:200]}")

    secao("links que a fila considera \"já em andamento\" agora")
    links = fila.links_em_andamento()
    linha("quantos", len(links))
    for l in sorted(links):
        print(f"      {l}")
    if links:
        print()
        print("      Qualquer vídeo destes links, se mandado para análise de novo")
        print("      (pela tela ou por analisar_pendentes.py), é IGNORADO em")
        print("      silêncio agora. Se o link aqui corresponder a uma linha que")
        print("      está em AGUARDANDO VALIDAÇÃO há muito tempo, é a prova.")


if __name__ == "__main__":
    rodar()
