# -*- coding: utf-8 -*-
"""
Manda linhas já validadas voltarem para a fila de análise.

PARA QUE SERVE

Quando uma regra do motor muda, o que já foi analisado continua com o veredito
da regra antiga. Foi o caso de 29/08/2026, com a correção da amostragem de
quadros: até então os três quadros saíam todos do primeiro 0,7 segundo do
vídeo, então aviso que aparecia depois disso não era encontrado.

Reprocessar exige DUAS coisas, e é por isso que existe um programa para isso em
vez de fazer na mão:

1. Apagar a célula VALIDACAO da linha, senão a automação não escreve nela (ela
   só escreve em célula vazia, de propósito).
2. Apagar a análise guardada daquele vídeo, senão o trabalhador reaproveita o
   resultado antigo e não reanalisa nada. Esquecer este passo é o erro fácil:
   tudo parece funcionar e o veredito volta igual.

CUIDADO

Apagar a coluna VALIDACAO apaga também anotação que uma pessoa tenha escrito
ali à mão. Por isso o programa mostra o que vai apagar e só age com --aplicar.

Uso:
    py reprocessar_linhas.py 9                 (mostra o que faria)
    py reprocessar_linhas.py 9 --aplicar
    py reprocessar_linhas.py --todas --aplicar
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fila_trabalho
import fluxo_downloads as fluxo
import pipeline_influenciadores as pipeline
import sheets_client
import trava


def limpar_celulas(excel_rows):
    """Deixa a linha pronta para receber veredito novo."""
    planilha = fluxo._planilha_monitoramento_id()
    aba = fluxo.ABA_MONITORAMENTO
    conteudo = {
        "validacao": "",
        "evidencia": "",
        "validado_em": "",
        "situacao": fluxo.AGUARDANDO_VALIDACAO,
    }
    for chave, valor in conteudo.items():
        letra = fluxo.letra_da_coluna(fluxo.COL_MON[chave])
        sheets_client.escrever_lote(planilha, aba, letra,
                                    [(n, valor) for n in excel_rows])


def esquecer_analises(links):
    """Tira do registro só as análises destes vídeos, mantendo as outras.

    Lê e grava dentro da mesma trava: o trabalhador pode estar gravando
    análise de outro vídeo ao mesmo tempo, e sem isso uma das duas gravações
    se perderia."""
    with trava.travar(pipeline.CACHE_PATH):
        cache = pipeline.carregar_cache()
        tirados = [l for l in links if l in cache]
        for l in tirados:
            del cache[l]
        if tirados:
            pipeline._salvar_cache_sem_travar(cache)
    return tirados


def main():
    aplicar = "--aplicar" in sys.argv
    todas = "--todas" in sys.argv
    pedidas = {int(a) for a in sys.argv[1:] if a.isdigit()}

    if not todas and not pedidas:
        print(__doc__)
        return

    linhas = pipeline.carregar_monitoramento()
    alvo = [l for l in linhas if todas or l["excel_row"] in pedidas]
    if not alvo:
        print("Nenhuma das linhas pedidas tem vídeo para analisar. Nada feito.")
        return

    ja_na_fila = fila_trabalho.links_em_andamento()
    alvo = [l for l in alvo if l["link"] not in ja_na_fila]
    if not alvo:
        print("Todas as linhas pedidas já estão na fila. Nada feito.")
        return

    cache = pipeline.carregar_cache()
    print(f"{len(alvo)} linha(s) para reprocessar:")
    print()
    for l in alvo:
        veredito = l["veredito_na_planilha"] or "(sem veredito)"
        guardada = "sim" if l["link"] in cache else "não"
        print(f"  linha {l['excel_row']:>3} {l['influenciador']:<18} "
              f"{l['data'] or 'sem data':<12} veredito a apagar: {veredito[:44]}")
        print(f"      {'análise guardada a esquecer: ' + guardada}")
    print()

    if not aplicar:
        print("Nada foi alterado. Para valer, rode de novo com --aplicar")
        return

    de_pe, _ = fila_trabalho.trabalhador_de_pe()
    if not de_pe:
        print("AVISO: o trabalhador não está de pé. As tarefas ficam esperando "
              "na fila até alguém subir ele.")
        print()

    excel_rows = [l["excel_row"] for l in alvo]
    limpar_celulas(excel_rows)
    print(f"Células de veredito apagadas em {len(excel_rows)} linha(s).")

    esquecidas = esquecer_analises([l["link"] for l in alvo])
    print(f"{len(esquecidas)} análise(s) guardada(s) esquecida(s).")

    quem = fila_trabalho.quem_esta_usando()
    for l in alvo:
        fila_trabalho.criar(
            fila_trabalho.VALIDAR,
            {"link": l["link"], "excel_rows": [l["excel_row"]], "linha": l},
            rotulo=f"{l['influenciador']} · {l['data'] or 'sem data'}",
            criada_por=f"{quem} (reprocessamento)",
        )
    print(f"{len(alvo)} tarefa(s) na fila. Acompanhe pela tela ou pela janela "
          "do trabalhador.")


if __name__ == "__main__":
    main()
