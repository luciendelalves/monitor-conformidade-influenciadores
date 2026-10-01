"""
Compara os vereditos da IA (cache local, resultados.json) contra as validações
manuais antigas que existiam na coluna F antes dela ser excluída da planilha
(backup salvo em producao/auditorias/avisos-influenciadores-portaria136/
backup_coluna_F_validacao_manual.json) — sem precisar o auditor revisar as
linhas manualmente uma por uma. Só aponta as DIVERGÊNCIAS pra conferência.

Achado importante: o backup foi feito ANTES de uma linha extra ter sido
inserida no topo da planilha (pra virar cabeçalho de verdade), então todo
número de linha do backup está 1 posição ATRÁS da posição atual — corrigido
abaixo (BACKUP_OFFSET). Se isso mudar de novo no futuro, ajuste essa constante
conferindo 1-2 casos manualmente primeiro.

Rodar: py comparar_com_validacao_manual.py
"""

import json
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "_drive_credenciais"))
import pipeline_influenciadores as pipeline

BACKUP_PATH = os.path.join(pipeline.BASE_DIR, "backup_coluna_F_validacao_manual.json")
BACKUP_OFFSET = 1  # backup foi feito 1 linha ANTES da inserção do cabeçalho


def classificar_humano(texto_humano):
    """Tenta mapear o texto livre da validação manual pro mesmo veredito
    resumido que a IA usa. Devolve None se não conseguir classificar com
    segurança (nesse caso a linha vai pro grupo 'não classificado', não pro
    grupo de divergência — evita falso alarme por não entender o texto)."""
    if not texto_humano or not str(texto_humano).strip():
        return None
    t = str(texto_humano).strip().lower()

    if t in ("ok", "okay", "conforme"):
        return "CONFORME"
    if "sem acesso" in t or "não consegu" in t or "nao consegu" in t or "quebrado" in t:
        return "SEM ACESSO À PASTA"
    if "vazia" in t or "vazio" in t or "sem vídeo" in t or "sem video" in t or "sem mídia" in t or "sem midia" in t:
        return "PASTA VAZIA"
    if "rede social" in t or "instagram" in t or "tiktok" in t:
        return "NÃO FOI POSSÍVEL ANALISAR (LINK DE REDE SOCIAL)"
    if "falta" in t or "sem advertência" in t or "sem advertencia" in t or "adequação regulatória" in t or "adequacao regulatoria" in t or "não conforme" in t or "nao conforme" in t:
        return "NÃO CONFORME"
    return None  # texto livre não reconhecido — não arrisca


def classificar_ia_resumido(rotulo_ia):
    """Reduz o rótulo completo da IA (que pode ter motivo entre parênteses)
    pra mesma granularidade grossa usada na comparação com o humano."""
    if not rotulo_ia:
        return None
    if rotulo_ia.startswith("NÃO CONFORME"):
        return "NÃO CONFORME"
    if rotulo_ia == "CONFORME":
        return "CONFORME"
    if rotulo_ia == "PASTA VAZIA":
        return "PASTA VAZIA"
    if rotulo_ia == "SEM ACESSO À PASTA":
        return "SEM ACESSO À PASTA"
    if rotulo_ia.startswith("NÃO FOI POSSÍVEL ANALISAR"):
        return "NÃO FOI POSSÍVEL ANALISAR (LINK DE REDE SOCIAL)"
    if rotulo_ia == "REQUER ANÁLISE HUMANA":
        return "REQUER ANÁLISE HUMANA"
    return None


def main():
    if not os.path.exists(BACKUP_PATH):
        raise SystemExit(f"Não achei o backup em: {BACKUP_PATH}")

    with open(BACKUP_PATH, encoding="utf-8") as f:
        backup = json.load(f)  # {"excel_row_antigo": "texto humano" ou None}

    print("Carregando planilha atual...")
    linhas = pipeline.carregar_planilha()
    row_para_link = {l["excel_row"]: l["link"] for l in linhas}

    print("Carregando cache local (resultados da IA)...")
    cache = pipeline.carregar_cache()

    divergentes = []
    concordantes = 0
    nao_classificados = 0
    sem_resultado_ia = 0

    for row_antigo_str, valor_humano in backup.items():
        if not valor_humano:
            continue
        row_antigo = int(row_antigo_str)
        row_atual = row_antigo + BACKUP_OFFSET
        link = row_para_link.get(row_atual)
        if not link:
            continue

        r_ia = cache.get(link)
        if r_ia is None:
            sem_resultado_ia += 1
            continue

        humano_resumido = classificar_humano(valor_humano)
        ia_rotulo = pipeline.formatar_para_planilha(r_ia)
        ia_resumido = classificar_ia_resumido(ia_rotulo)

        if humano_resumido is None:
            nao_classificados += 1
            continue

        if humano_resumido == ia_resumido:
            concordantes += 1
        else:
            divergentes.append({
                "excel_row_atual": row_atual,
                "influenciador": r_ia.get("influenciador"),
                "link": link,
                "validacao_humana_original": valor_humano,
                "veredito_ia": ia_rotulo,
            })

    print(f"\n{'='*70}")
    print(f"Concordam:            {concordantes}")
    print(f"Divergem:             {len(divergentes)}")
    print(f"Texto humano ambíguo (não classificado, ignorado): {nao_classificados}")
    print(f"Sem resultado da IA ainda (linha não processada):  {sem_resultado_ia}")
    print(f"{'='*70}\n")

    if divergentes:
        print("DIVERGÊNCIAS (conferir manualmente):\n")
        for d in divergentes:
            print(f"Linha {d['excel_row_atual']} — @{d['influenciador']}")
            print(f"  Humano disse: {d['validacao_humana_original']!r}")
            print(f"  IA disse:     {d['veredito_ia']!r}")
            print(f"  Link: {d['link']}")
            print()

        destino = os.path.join(pipeline.BASE_DIR, "divergencias_ia_vs_humano.json")
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(divergentes, f, ensure_ascii=False, indent=2)
        print(f"Lista completa salva em: {destino}")
    else:
        print("Nenhuma divergência encontrada nas linhas com validação humana anterior.")


if __name__ == "__main__":
    main()
