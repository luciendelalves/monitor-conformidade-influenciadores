# -*- coding: utf-8 -*-
r"""
O estado do programa agora: planilhas, fila, log, cache, trabalhador, conta.

SOMENTE LEITURA. Zero chamada ao Instagram.

    py ferramentas\ver_registros.py                  visão geral
    py ferramentas\ver_registros.py @maumauzk        tudo o que existe dele

É A PRIMEIRA FERRAMENTA A RODAR quando algo parece estranho, porque ela responde
"o que existe" antes de qualquer teoria sobre por quê.

E ela mostra SEMPRE três coisas que não podem ser apagadas por engano: o contador
de chamadas do Instagram do dia, a conta configurada e o mapa de perfis. Foram
essas três que precisaram ser poupadas em cada limpeza de teste, e ter o número
delas à vista evita zerar o que protege a conta.
"""
import csv
import os
import sys
from collections import Counter

from _base import cabecalho, contagem, linha, pedir_argumento, secao

import fluxo_downloads as fluxo


def titulo_da_planilha(planilha):
    import sheets_client
    try:
        meta = sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().get(
                spreadsheetId=planilha, fields="properties(title)").execute())
        return meta.get("properties", {}).get("title") or "(sem título)"
    except Exception as e:
        return f"(não li: {str(e)[:60]})"


def ler_monitoramento():
    import sheets_client
    planilha = fluxo._planilha_monitoramento_id()
    if not planilha:
        return None, None, []
    valores = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha,
            range=f"'{fluxo.ABA_MONITORAMENTO}'!A2:{fluxo.ULTIMA_COLUNA_MON}20000",
        ).execute()).get("values", [])
    return planilha, titulo_da_planilha(planilha), valores


def ler_log():
    if not os.path.exists(fluxo.ARQUIVO_LOG):
        return []
    with open(fluxo.ARQUIVO_LOG, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def campo(linha_, indice):
    return str(linha_[indice]).strip() if len(linha_) > indice else ""


def visao_geral():
    cabecalho("Estado do programa agora", f"layout de pastas: {fluxo.LAYOUT_PASTAS}")

    secao("planilha de Monitoramento")
    planilha, titulo, valores = ler_monitoramento()
    if not planilha:
        linha("planilha", "identificador não configurado")
    else:
        linha("título", titulo)
        if "TESTE" not in (titulo or "").upper():
            print("      ATENÇÃO: o título não tem TESTE. Confirme que é a cópia certa.")
        linha("linhas de dados", len(valores))
        i_h = fluxo.COL_MON["handle"] - 1
        i_sit = fluxo.COL_MON["situacao"] - 1
        i_val = fluxo.COL_MON["validacao"] - 1
        i_marc = fluxo.COL_MON["marcacao"] - 1
        if valores:
            por_influ = Counter(fluxo.chave_de_pasta(campo(l, i_h)) for l in valores
                                if campo(l, i_h))
            situacoes = Counter(campo(l, i_sit) or "(vazia)" for l in valores)
            vereditos = Counter(campo(l, i_val) or "(vazio)" for l in valores)
            # Passou de uma contagem de orgânicos para as três marcações
            # (03/09/2026). Vale ver as três: é a marcação que decide a pasta, e
            # ela vai decidir a régua da análise.
            marcacoes = Counter(fluxo.marcacao_de_celula(campo(l, i_marc))
                                for l in valores)
            linha("influenciadores distintos", len(por_influ))
            contagem("marcação", marcacoes, limite=5, recuo=6)
            contagem("situação", situacoes, limite=8, recuo=6)
            contagem("veredito", vereditos, limite=10, recuo=6)

    secao("fila de downloads")
    try:
        fila = fluxo.ler_fila()
        linha("linhas", len(fila))
        pendentes = [x for x in fila if x["link"] and not x["status"]]
        linha("ainda sem baixar", len(pendentes))
        if fila:
            contagem("status", Counter(x["status"] or "(vazio)" for x in fila),
                     limite=8, recuo=6)
    except Exception as e:
        linha("fila", f"não li: {str(e)[:80]}")

    secao("log de fluxo")
    registros = ler_log()
    linha("arquivo", fluxo.ARQUIVO_LOG)
    linha("registros", len(registros))
    if registros:
        contagem("estágio", Counter(r.get("estagio") or "?" for r in registros),
                 limite=8, recuo=6)
        ok = sum(1 for r in registros if (r.get("status") or "").upper() == "OK")
        linha("com status OK", f"{ok} de {len(registros)}")
        linha("mais recente", registros[-1].get("quando"))

    secao("cache de análise")
    import pipeline_influenciadores as pipeline
    cache = pipeline.carregar_cache()
    linha("entradas", len(cache))
    if cache:
        contagem("classificação",
                 Counter(str(r.get("classificacao")) for r in cache.values()),
                 limite=6, recuo=6)

    secao("trabalhador")
    caminho = os.path.join(fluxo.PASTA_TESTE, "fila_trabalho", "trabalhador.json")
    if os.path.exists(caminho):
        import json
        with open(caminho, encoding="utf-8") as f:
            estado = json.load(f)
        linha("visto em", estado.get("atualizado_em"))
        linha("processo", estado.get("pid"))
        fazendo = estado.get("fazendo_agora") or []
        linha("fazendo agora", fazendo if fazendo else "nada (ocioso)")
    else:
        linha("trabalhador", "sem sinal de vida gravado")

    secao("O QUE NÃO PODE SER APAGADO POR ENGANO")
    pode, motivo, usados, restantes = fluxo.situacao_da_conta()
    linha("conta configurada", "@" + fluxo.USUARIO_DOS_COOKIES)
    origem = ("conta_instagram.txt" if os.path.exists(fluxo.ARQUIVO_CONTA_INSTAGRAM)
              else "variável ou valor do código")
    linha("de onde vem o nome", origem)
    linha("chamadas ao Instagram hoje", f"usadas {usados}, restam {restantes}")
    linha("conta do dia nesta máquina", fluxo.conta_do_dia_nesta_maquina() or "nenhuma ainda")
    if not pode:
        print(f"      BLOQUEADA AGORA: {motivo[:150]}")
    linha("perfis com número guardado", len(fluxo._ler_userids()))
    print()
    print("   Zerar a contagem remove a proteção contra bloqueio de conta.")
    print("   Apagar o mapa de perfis faz o programa gastar de novo a chamada")
    print("   mais arriscada que ele tem, uma vez por influenciador.")


def por_influenciador(alvo):
    chave = fluxo.chave_de_pasta(alvo)
    cabecalho(f"Tudo o que existe de @{chave}")

    secao("planilha de Monitoramento")
    planilha, titulo, valores = ler_monitoramento()
    i_h = fluxo.COL_MON["handle"] - 1
    minhas = [(n, l) for n, l in enumerate(valores, start=2)
              if fluxo.chave_de_pasta(campo(l, i_h)) == chave]
    linha("linhas", [n for n, _l in minhas] or "nenhuma")
    for n, l in minhas:
        print(f"      linha {n}: tipo={campo(l, fluxo.COL_MON['tipo'] - 1)!r} "
              f"ciclo={campo(l, fluxo.COL_MON['ciclo'] - 1)!r} "
              # RENOMEADO EM 23/09/2026: a coluna virou MARCACAO em 03/09/2026
              # (era ORGANICO), e esta ferramenta de conferência não tinha
              # acompanhado. Ficava travando com KeyError sempre que alguém
              # tentava usar ver_registros.py num influenciador de verdade.
              f"marcacao={campo(l, fluxo.COL_MON['marcacao'] - 1)!r}")
        print(f"         veredito: {campo(l, fluxo.COL_MON['validacao'] - 1)[:90]!r}")

    secao("fila de downloads")
    try:
        fila = [x for x in fluxo.ler_fila()
                if fluxo.chave_de_pasta(x["influenciador"]) == chave
                or f"/{chave}/" in (x["link"] or "").lower()]
        linha("linhas", len(fila))
        for x in fila:
            print(f"      linha {x['numero_linha']}: status={x['status']!r} "
                  f"marcacao={x['marcacao']!r}")
            print(f"         {x['link']}")
    except Exception as e:
        linha("fila", f"não li: {str(e)[:80]}")

    secao("log de fluxo")
    registros = [r for r in ler_log()
                 if fluxo.chave_de_pasta(r.get("handle") or "") == chave
                 or f"/{chave}/" in (r.get("origem") or "").lower()]
    linha("registros", len(registros))
    for r in registros[-10:]:
        print(f"      {r.get('quando')}  estágio={r.get('estagio')}  "
              f"data_vídeo={r.get('data_video')!r}  status={str(r.get('status'))[:60]}")

    secao("cache de análise")
    import pipeline_influenciadores as pipeline
    entradas = [r for r in pipeline.carregar_cache().values()
                if fluxo.chave_de_pasta(str(r.get("influenciador") or "")) == chave
                or chave in str(r.get("arquivo") or "").lower()]
    linha("entradas", len(entradas))
    for r in entradas:
        print(f"      {r.get('arquivo')}  [{r.get('processado_em')}]")
        print(f"         {r.get('classificacao')}: {str(r.get('motivo') or '')[:100]}")

    secao("Drive")
    try:
        pastas = fluxo.pastas_de_influenciador_no_teste(chave)
        linha("pastas", len(pastas))
        for caminho, ident in pastas:
            print(f"      {caminho}")
    except Exception as e:
        linha("Drive", f"não li: {str(e)[:80]}")

    secao("número do perfil no Instagram")
    guardado = fluxo.userid_guardado(chave)
    if guardado:
        linha("guardado", "sim")
        print("      link de Story sem o número da peça pode funcionar,")
        print("      se ele tiver UM story só no ar.")
    else:
        linha("guardado", "não")
        print("      link de Story SEM o número da peça vai ser barrado,")
        print("      para não gastar a consulta que já levou 429.")


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    if alvo:
        por_influenciador(alvo)
    else:
        visao_geral()
