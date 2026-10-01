# -*- coding: utf-8 -*-
r"""
O que a análise decidiu, e POR QUÊ.

SOMENTE LEITURA do cache local. Zero chamada ao Instagram e zero ao Drive.

    py ferramentas\ver_analise.py                    resumo por causa e por dia
    py ferramentas\ver_analise.py @andersonneiff     item por item, de um alvo
    py ferramentas\ver_analise.py causas             só o agrupamento por causa

POR QUE O AGRUPAMENTO POR CAUSA É O MODO PRINCIPAL

Em 02/09/2026 o auditor achou que a análise tinha "ficado menos assertiva",
olhando a proporção de Requer Verificação, que estava em 100% nos últimos dias.
O agrupamento por causa mostrou o que a proporção esconde: 24 dos 34 casos eram
"não achou aposta e não leu nenhum item", ou seja, material que ele mesmo havia
subido para testar e que não era peça publicitária. Para material que não é
anúncio, Requer Verificação é a resposta certa.

Ou seja: **a proporção de Requer Verificação não mede qualidade** enquanto a
amostra tiver material que não é publicidade. A causa mede.

E O MODO ALVO EXISTE porque foi assim que se descobriu que a IA de visão tem
falso positivo confirmado no publi: comparando, no mesmo clipe, o que o OCR leu
com o que a visão sugeriu.
"""
import re
import sys
from collections import Counter, defaultdict

from _base import cabecalho, contagem, linha, secao

import fluxo_downloads as fluxo
import pipeline_influenciadores as pipeline

CURTO = {"Conforme": "CONFORME", "Não Conforme": "NÃO CONFORME",
         "Requer Verificação": "REQUER"}

# Nomes que aparecem em material de teste do próprio projeto, e não em peça real.
E_TESTE = re.compile(r"teste[._]|arvore|organico\.0109|hierarquia", re.IGNORECASE)

# O item lido pelo OCR aparece na evidência como "rotulo: 'texto'".
LEU_ITEM = re.compile(r"(18\+|portaria|extra|ministério_fazenda|"
                      r"conteúdo_aposta|publi):\s*'", re.IGNORECASE)


def causa_de(registro):
    """Em qual causa aquele Requer Verificação cai.

    As causas são as que o motor produz de verdade, e não categorias
    inventadas: cada ramo do classificar_post gera um texto próprio."""
    motivo = str(registro.get("motivo") or "")
    evidencia = str(registro.get("evidencia") or "")
    leu_algum = bool(LEU_ITEM.search(evidencia))

    if "Pasta sem arquivo" in motivo or "pasta_vazia" in motivo:
        return "pasta vazia ou sem mídia"
    if "Falha ao acessar" in motivo:
        return "não consegui acessar o material"
    if "fora do escopo automático" in motivo:
        return "link de rede social ao vivo, fora do alcance"
    if "Nenhum arquivo do post parece conter" in motivo:
        return ("não achou aposta, MAS leu item do aviso" if leu_algum
                else "não achou aposta e NÃO leu nenhum item")
    if "CONFERIR NA PEÇA" in motivo or "IA de visão local sugere presença de" in motivo:
        return "item não lido, a visão sugere presença"
    if "mesmo aviso" in motivo:
        return "item do banner não lido, irmão confirmado no clipe"
    if "logo/interface de aposta" in motivo:
        return "a visão sugere logo de aposta, sem texto"
    if "fragmento do aviso" in motivo:
        return "fragmento do aviso encontrado, não fecha"
    return "outro: " + motivo[:60]


def separar(cache):
    reais, de_teste = [], []
    for r in cache.values():
        alvo = f"{r.get('arquivo') or ''} {r.get('influenciador') or ''}"
        (de_teste if E_TESTE.search(alvo) else reais).append(r)
    return reais, de_teste


def resumo(mostrar_dias=True):
    cache = pipeline.carregar_cache()
    cabecalho("O que a análise decidiu", f"{len(cache)} entrada(s) no cache")
    if not cache:
        print("   O cache está vazio. Nada foi analisado ainda, ou ele foi limpo.")
        return

    reais, de_teste = separar(cache)
    linha("material real", len(reais))
    linha("material de teste do projeto", f"{len(de_teste)} (descartado das contas)")

    secao("classificação, só material real")
    contagem("veredito", Counter(CURTO.get(r.get("classificacao"), "?") for r in reais))

    if mostrar_dias:
        secao("por dia em que a análise rodou")
        por_dia = defaultdict(Counter)
        for r in reais:
            por_dia[str(r.get("processado_em") or "")[:10]][
                CURTO.get(r.get("classificacao"), "?")] += 1
        print(f"      {'dia':<12} {'total':>5} {'CONF':>5} {'N-CONF':>7} {'REQUER':>7}   % REQUER")
        print("      " + "-" * 58)
        for dia in sorted(por_dia):
            c = por_dia[dia]
            total = sum(c.values())
            pct = 100.0 * c["REQUER"] / total if total else 0
            print(f"      {dia:<12} {total:>5} {c['CONFORME']:>5} "
                  f"{c['NÃO CONFORME']:>7} {c['REQUER']:>7}   {pct:>5.0f}%")
        print()
        print("      A proporção de REQUER não mede qualidade enquanto a amostra")
        print("      tiver material que não é publicidade. Veja as causas abaixo.")

    secao("POR CAUSA, que é o que importa")
    causas = Counter(causa_de(r) for r in reais
                     if r.get("classificacao") == "Requer Verificação")
    contagem("causa do Requer Verificação", causas, limite=12)

    faltando = Counter()
    for r in reais:
        if r.get("classificacao") == "Não Conforme":
            for f in (r.get("faltando") or []):
                faltando[f] += 1
    if faltando:
        secao("o que faltou nos Não Conforme")
        contagem("item ausente", faltando, limite=8)

    sugestao = [r for r in reais
                if "IA de visão local sugere" in f"{r.get('motivo')} {r.get('evidencia')}"]
    if sugestao:
        secao("peças que dependem de sugestão da IA de visão")
        linha("quantas", len(sugestao))
        itens = Counter()
        for r in sugestao:
            texto = f"{r.get('motivo') or ''} {r.get('evidencia') or ''}"
            for achado in re.finditer(r"(\w[\wÀ-ÿ_+]*)\s*:\s*(?:IDENTIFICAÇÃO[^,]*)?"
                                      r"NÃO CONFIRMADO", texto):
                itens[achado.group(1)] += 1
            for achado in re.finditer(r"(\w[\wÀ-ÿ_+]*)\s*:\s*IA de visão", texto):
                itens[achado.group(1)] += 1
        contagem("item que recebeu a sugestão", itens, limite=8, recuo=6)
        print()
        print("      A IA de visão tem DOIS falsos positivos confirmados, os dois")
        print("      em itens que precisam estar escritos: um \"18+\" numa imagem")
        print("      que era print de conversa, e um publi que não estava na peça")
        print("      (@andersonneiff, 02/09/2026). Não confie na sugestão sozinha.")


def por_alvo(alvo):
    chave = fluxo.chave_de_pasta(alvo)
    cache = pipeline.carregar_cache()
    entradas = [r for r in cache.values()
                if chave in str(r.get("influenciador") or "").lower()
                or chave in str(r.get("arquivo") or "").lower()]
    cabecalho(f"Análise de @{chave}", f"{len(entradas)} entrada(s)")
    if not entradas:
        print("   Nada no cache para esse alvo.")
        return

    for r in sorted(entradas, key=lambda x: str(x.get("processado_em") or "")):
        print("-" * 74)
        print(f"{r.get('arquivo')}")
        print(f"   analisado em : {r.get('processado_em')}")
        print(f"   data do post : {r.get('data')}")
        print(f"   veredito     : {r.get('classificacao')}")
        print(f"   causa        : {causa_de(r)}")
        print(f"   motivo       : {str(r.get('motivo') or '')[:200]}")
        evidencia = str(r.get("evidencia") or "")
        print("   o que o OCR leu, item por item:")
        lidos = re.findall(r"([\wÀ-ÿ_+]+):\s*'([^']*)'", evidencia)
        if lidos:
            for rotulo, texto in lidos:
                print(f"      {rotulo:<20} {texto[:60]!r}")
        else:
            print("      (nenhum item reconhecido)")
        nao_confirmados = re.findall(r"([\wÀ-ÿ_+ ()#]+?):\s*(?:IDENTIFICAÇÃO[^.]*?)?"
                                     r"NÃO CONFIRMAD[OA]", evidencia)
        if nao_confirmados:
            print("   não confirmados por OCR:")
            for rotulo in nao_confirmados:
                print(f"      {rotulo.strip()}")
        if r.get("faltando"):
            print(f"   faltando: {', '.join(r['faltando'])}")
        if r.get("alerta_audio"):
            print(f"   alerta de áudio: {r['alerta_audio']}")
        if r.get("alerta_crianca"):
            print(f"   alerta de criança: {r['alerta_crianca']}")
        print(f"   link: {r.get('link')}")
        print()


if __name__ == "__main__":
    argumento = sys.argv[1] if len(sys.argv) > 1 else None
    if not argumento:
        resumo()
    elif argumento == "causas":
        resumo(mostrar_dias=False)
    else:
        por_alvo(argumento)
