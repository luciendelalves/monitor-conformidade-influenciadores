# -*- coding: utf-8 -*-
r"""
A pergunta que o programa faz à visão sobre o #publi acerta quanto?

POR QUE ESTA FERRAMENTA EXISTE (08/09/2026)

A pergunta do publi era a única do dicionário `_PERGUNTAS_VISAO` que perguntava
por CONCEITO ("um selo ou marca indicando publicidade") em vez de nomear o texto
procurado, como as outras cinco fazem. O efeito medido: o modelo respondia sim
sempre que a faixa legal do rodapé caía no recorte, porque ela é, literalmente,
uma marca que indica publicidade autorizada. Ele respondia a pergunta que
recebeu.

    pergunta      acha o publi que existe   não inventa o que não há   geral
    conceitual          17/17 (100%)               1/10 (10%)           67%
    nomeando            17/17 (100%)              10/10 (100%)         100%

A ferramenta existe para essa conta poder ser REFEITA, e não repetida de memória.
Serve principalmente quando:

  - alguém mexer na pergunta do publi
  - trocar o modelo de visão
  - houver volume de peça do banner NOVO, posterior a 17/07/2026, porque este
    conjunto é todo do banner anterior

REPLICA A SEQUENCIA DO PROGRAMA: quadro mais nítido da peça, pergunta na faixa
de baixo e, se ela negar, na faixa de cima ampliada. Basta uma dizer sim. Então o
que sai daqui é a efetividade do PROGRAMA, não de uma pergunta isolada.

    py ferramentas\avaliar_pergunta_do_publi.py

Só lê o cache de análise. Não fala com o Instagram nem com a planilha. Leva
alguns segundos por peça, porque o modelo de visão é a parte lenta, e deixa a
máquina pesada enquanto roda.
"""
import os
import re
import sys
import time

from _base import cabecalho, linha, secao

import validar_avisos_portaria136 as motor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIDIA = os.path.join(os.path.dirname(BASE), "auditorias",
                     "avisos-influenciadores-portaria136", "midia")

# O CONJUNTO COM VERDADE CONHECIDA, montado em 08/09/2026.
#
# "OCR leu"  positivo de graça: a regex casou com texto real na peça, então a
#            marca está lá. Não depende de olho humano.
# "a olho"   o auditor abriu o quadro mais nítido e conferiu. São 5 positivos,
#            todos casos difíceis (publi pequeno ou claro sobre fundo claro,
#            sempre no topo), e 10 negativos.
#
# LIMITE QUE ACOMPANHA O NÚMERO: os rótulos "a olho" são de quem fez a medição,
# não de quem audita a peça, e todas as peças são do banner anterior a
# 17/07/2026. Serve para comparar uma pergunta com outra, não para afirmar taxa
# de conformidade.
CONJUNTO = [
    ("linha_108/frames_suellenalmeida.oficial's2026-2-5-12.25.841 story", True, "OCR leu"),
    ("linha_284/frames_recifeordinario_3840489070913260399", True, "OCR leu"),
    ("linha_379/frames_biankanicoli01's2026-3-5-10.1.551 story", True, "OCR leu"),
    ("linha_389/frames_dudafreiret's2026-3-6-10.14.476 story", True, "OCR leu"),
    ("linha_413/frames_marcelinho_jhonson's2026-3-7-7.56.11 story", True, "OCR leu"),
    ("linha_450/frames_bahiadohype's2026-3-7-7.35.804 story", True, "OCR leu"),
    ("linha_474/frames_leodocoque's2026-3-10-10.34.325 story", True, "OCR leu"),
    ("linha_494/frames_suellenalmeida.oficial's2026-3-10-11.43.421 story", True, "OCR leu"),
    ("linha_516/frames_suellenalmeida.oficial's2026-3-10-11.43.559 story", True, "OCR leu"),
    ("linha_542/frames_suellenalmeida.oficial's2026-3-12-13.13.183 story", True, "OCR leu"),
    ("linha_562/frames_tela 2", True, "OCR leu"),
    ("linha_576/frames_eudisbocuda's2026-3-12-14.41.493 story", True, "OCR leu"),
    ("linha_108/frames_suellenalmeida.oficial's2026-2-5-12.26.138 story", True, "a olho"),
    ("linha_186/frames_mudinhooff's2026-2-15-9.50.598 story", True, "a olho"),
    ("linha_363/frames_jojotodynho's2026-3-4-19.17.337 story", True, "a olho"),
    ("linha_492/frames_mudinhooff's2026-3-10-11.10.994 story", True, "a olho"),
    ("linha_521/frames_thamaramaiaof's2026-3-12-15.30.700 story", True, "a olho"),
    ("linha_128/frames_reservapretarara's2026-2-10-10.19.841 story", False, "a olho"),
    ("linha_330/frames_marimenezees_'s2026-3-2-10.51.120 story", False, "a olho"),
    ("linha_360/frames_gordaodaxj's2026-3-4-9.57.465 story", False, "a olho"),
    ("linha_385/frames_lilisantanaoficial's2026-3-6-10.16.86 story", False, "a olho"),
    ("linha_393/frames_lomma's2026-3-6-9.40.511 story", False, "a olho"),
    ("linha_418/frames_lomma's2026-3-7-7.45.945 story", False, "a olho"),
    ("linha_420/frames_djmaryduarte's2026-3-7-7.34.903 story", False, "a olho"),
    ("linha_460/frames_marimenezees_'s2026-3-9-12.15.296 story", False, "a olho"),
    ("linha_529/frames_patriciaaparada's2026-3-12-10.53.307 story", False, "a olho"),
    ("linha_572/frames_marcelinho_jhonson's2026-3-12-14.50.817 story", False, "a olho"),
]


def quadro_mais_nitido(peca):
    pasta = os.path.join(MIDIA, peca.replace("/", os.sep))
    if not os.path.isdir(pasta):
        return None
    quadros = [os.path.join(pasta, a) for a in sorted(os.listdir(pasta))
               if a.lower().endswith(".jpg")]
    return max(quadros, key=motor.medir_nitidez) if quadros else None


def perguntar(imagem, pergunta):
    """A mesma checagem de resposta do programa: só 'sim' no começo conta."""
    try:
        resposta = motor._perguntar_ollama(imagem, pergunta)
    except Exception:
        resposta = ""
    return bool(re.match(r"\s*sim\b", resposta, re.IGNORECASE)), resposta


def como_o_programa(frame, pergunta):
    viu, cru = perguntar(motor.recortar_faixa_do_rodape(frame), pergunta)
    if viu:
        return True, "baixo", cru
    viu, cru = perguntar(motor.recortar_faixa_do_topo(frame), pergunta)
    return viu, ("cima" if viu else "nenhuma"), cru


if __name__ == "__main__":
    pergunta = motor._PERGUNTAS_VISAO["publi"]

    cabecalho("A pergunta do publi acerta quanto",
              "mede a pergunta que está EM PRODUÇÃO, lida do módulo")
    print(f"   {pergunta}")
    print()

    disponiveis = [(p, t, v) for p, t, v in CONJUNTO if quadro_mais_nitido(p)]
    linha("peças do conjunto", len(CONJUNTO))
    linha("encontradas no cache", len(disponiveis))
    if len(disponiveis) < len(CONJUNTO):
        linha("faltando", f"{len(CONJUNTO) - len(disponiveis)}, provavelmente "
                          f"apagadas do cache. O número sai sobre o que sobrou")
    if not disponiveis:
        print()
        print("   Nenhuma peça do conjunto está no cache. Não há o que medir.")
        sys.exit(0)

    print()
    vazias = 0
    resultados = []
    inicio = time.time()
    for i, (peca, tem, origem) in enumerate(disponiveis, 1):
        frame = quadro_mais_nitido(peca)
        viu, onde, cru = como_o_programa(frame, pergunta)
        if not str(cru).strip():
            vazias += 1
        certo = (viu == tem)
        resultados.append((tem, viu, certo, origem))
        print(f"   [{i:>2}/{len(disponiveis)}] verdade="
              f"{'TEM' if tem else 'nao'} visão={'SIM' if viu else 'nao'} "
              f"({onde:<8}) {'ok    ' if certo else 'ERRADO'} "
              f"{(time.time() - inicio) / i:.0f}s/peça  {peca[:34]}", flush=True)

    pos = [r for r in resultados if r[0]]
    neg = [r for r in resultados if not r[0]]
    vp = sum(1 for r in pos if r[1])
    vn = sum(1 for r in neg if not r[1])

    secao("RESULTADO")
    print(f"   {'':<24}{'visão SIM':>12}{'visão não':>12}")
    print(f"   {'TEM publi (verdade)':<24}{vp:>12}{len(pos) - vp:>12}")
    print(f"   {'não tem (verdade)':<24}{len(neg) - vn:>12}{vn:>12}")
    print()
    linha("acha o publi que existe", f"{vp}/{len(pos)}"
          + (f" ({vp / len(pos) * 100:.0f}%)" if pos else ""))
    linha("não inventa o que não há", f"{vn}/{len(neg)}"
          + (f" ({vn / len(neg) * 100:.0f}%)" if neg else ""))
    linha("acerto geral", f"{vp + vn}/{len(resultados)} "
          f"({(vp + vn) / len(resultados) * 100:.0f}%)")

    if vazias:
        secao("ATENÇÃO")
        print(f"   {vazias} resposta(s) do modelo vieram VAZIAS, e resposta vazia")
        print("   conta como 'não viu'. Confira se o Ollama está respondendo, senão")
        print("   o acerto nos negativos está inflado por silêncio.")

    secao("O QUE CADA ERRO CUSTA NA RÉGUA")
    print(f"   {len(neg) - vn} falso positivo: peça SEM publi vira REQUER")
    print("      VERIFICAÇÃO em vez de NÃO CONFORME, e a régua deixa de apontar")
    print("      violação real.")
    print(f"   {len(pos) - vp} falso negativo: peça COM publi vira NÃO CONFORME.")
    print("      É acusação errada contra influenciador, o erro mais caro.")
    print()
    print("=" * 74)
