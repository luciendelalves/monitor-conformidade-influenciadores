# -*- coding: utf-8 -*-
"""
Prova quais termos contam como declaração de publicidade, e quais NÃO contam.

POR QUE ESTA LISTA É DECISÃO DE AUDITORIA, e não de programação: ela decide
conformidade. Ampliar demais perde achado (peça sem declaração passa como
declarada); estreitar demais cria achado falso (peça que declarou com outra
palavra sai como Não Conforme). Os termos abaixo foram aprovados pelo auditor em
02/09/2026, um por um.

O DEFEITO QUE A AMPLIAÇÃO CORRIGIU, e ele era de simetria: a pergunta que o
programa faz à IA DE VISÃO é mais ampla do que o OCR conseguia confirmar. A
pergunta diz "selo ou marca indicando publicidade, parceria paga ou CONTEÚDO
PATROCINADO", e "patrocinado" não estava na lista do OCR. Então peça que
declarava com "conteúdo patrocinado" caía em Requer Análise, ou em Não Conforme
quando a visão também não pegava. Erro na direção acusatória.

TERMOS RECUSADOS PELO AUDITOR, e por isso testados como NÃO reconhecidos:
"recebido", "oferecido por" e "presente de". Nenhum é necessariamente declaração
de publicidade paga.

    py testes\teste_termos_de_publicidade.py
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


# Aprovados pelo auditor. O texto vem do OCR, então vale em qualquer caixa.
#
# AMPLIADO EM 08/09/2026, a pedido do auditor, que passou a lista dele:
# "#publicidade, #publi, #anúncio, #patrocinado ou Parceria paga com [Nome da
# Marca]". Quatro dos cinco já eram reconhecidos. Entraram:
#
#   publipost solto      "#publipost" já valia, a palavra sem cerquilha não.
#                        Entra sem ressalva porque não é palavra com outro
#                        sentido: só existe como marcação de publicidade.
#   #anúncio             SÓ COM CERQUILHA, e a diferença é deliberada. "Anúncio"
#                        é palavra comum e aparece na tela falando de outra
#                        coisa. Aceitar solto faria peça SEM declaração passar
#                        como declarada, que é o erro que perde achado. Mesmo
#                        critério já aplicado ao "#ad", que também não vale solto.
#
# SEM ACENTO TAMBÉM VALE, porque o OCR come acento com frequência. É o mesmo
# motivo pelo qual as regras de duas palavras aceitam espaço opcional.
RECONHECIDOS = [
    "#publi", "publi", "#publicidade", "publicidade",
    "#publipost", "publipost", "publiposts", "#publiposts",
    "#anúncio", "#anuncio", "#ANÚNCIO", "#anúncios", "#anuncios",
    "parceria paga", "PARCERIA PAGA", "Parceria paga com a Lottu",
    "patrocinado", "PATROCINADO",
    "patrocinada", "patrocinados", "conteúdo patrocinado",
    "#ad", "#ads", "pago por", "paga por", "pago pela Lottu", "paga pelo EDS",
]

# NÃO podem ser reconhecidos. Cada um por um motivo diferente, anotado ao lado.
RECUSADOS = [
    ("patrocinador oficial", "fala do patrocínio de um time, não da peça"),
    ("vou publicar amanhã", "\"publicar\" não é declaração de publicidade"),
    ("publico", "palavra comum, e a terminação não é de declaração"),
    ("adm", "não pode casar com o #ad"),
    ("recebido", "recusado pelo auditor: não é publicidade paga"),
    ("oferecido por", "recusado pelo auditor"),
    ("presente de", "recusado pelo auditor"),
    # A CONTRAPARTIDA DE ACEITAR "#anúncio" (08/09/2026). A cerquilha é o que
    # separa a marcação da palavra. Sem esta linha, a ampliação de hoje passaria
    # a declarar publicidade em qualquer peça que escreva "anúncio" na tela.
    ("anúncio", "palavra comum: sem cerquilha não é declaração"),
    ("anuncio", "idem, sem acento"),
    ("veja o anúncio de hoje", "frase corrente, não declara publicidade"),
    ("anunciante", "quem anuncia, não a marcação da peça"),
    ("", "texto vazio não declara nada"),
]


def rodar():
    import validar_avisos_portaria136 as motor

    print("--- 1. os termos aprovados são reconhecidos ---")
    for termo in RECONHECIDOS:
        conferir(bool(motor.REGEX_PUBLI.search(termo)), f"reconhece {termo!r}")

    print()
    print("--- 2. e os recusados NÃO são ---")
    for termo, motivo in RECUSADOS:
        conferir(not motor.REGEX_PUBLI.search(termo),
                 f"recusa {termo!r}", motivo)

    print()
    print("--- 3. reconhece dentro de uma frase, como o OCR entrega ---")
    # O OCR não devolve o termo isolado: devolve a tela inteira numa string.
    tela = ("JOGUE COM RESPONSABILIDADE #publi APOSTE AGORA NA LOTTU "
            "MINISTERIO DA FAZENDA ADVERTE APOSTA NAO E INVESTIMENTO")
    conferir(bool(motor.REGEX_PUBLI.search(tela)),
             "acha o termo no meio do texto da tela inteira")

    print()
    print("--- 4. a pergunta à IA de visão e a lista do OCR estão alinhadas ---")
    # Era o defeito: a visão era perguntada sobre "conteúdo patrocinado" e o OCR
    # não tinha essa palavra, então a resposta correta da visão virava dúvida.
    #
    # ESTA SEÇÃO ERA VAZIA E PASSAVA POR ENGANO (corrigido em 08/09/2026). Ela
    # tentava `motor.PERGUNTAS_VISAO`, e o dicionário se chama
    # `_PERGUNTAS_VISAO`, com sublinhado. O hasattr dava falso SEMPRE, e a
    # reserva procurava a frase no CÓDIGO INTEIRO. Bastava a frase existir em
    # qualquer comentário para o teste aprovar, o que aconteceu no dia em que a
    # pergunta foi reescrita: ela deixou de citar "conteúdo patrocinado" e o
    # teste continuou verde, porque a frase antiga estava no comentário que
    # explicava a mudança.
    pergunta = getattr(motor, "_PERGUNTAS_VISAO", {}).get("publi", "")
    conferir(bool(pergunta),
             "achei a pergunta do publi no dicionário da visão",
             "se o nome do dicionário mudar, este teste tem de acompanhar, "
             "e não cair numa busca no fonte que aprova qualquer coisa")

    # A PERGUNTA TEM DE NOMEAR TEXTO, E NÃO PERGUNTAR POR CONCEITO.
    #
    # Medido em 08/09/2026, em 27 peças com verdade conhecida: perguntando por
    # conceito ("marca indicando publicidade"), o acerto era 67%, e a visão
    # dizia sim em 9 de 10 peças SEM publi, porque a faixa legal do rodapé é,
    # literalmente, uma marca que indica publicidade autorizada. Nomeando o
    # texto, o acerto foi 100%. É o mesmo padrão das outras cinco perguntas do
    # dicionário, que todas citam a frase literal que procuram.
    termos_citados = re.findall(r"'([^']+)'", pergunta)
    conferir(len(termos_citados) >= 4,
             f"a pergunta nomeia texto literal ({len(termos_citados)} termo(s))",
             "pergunta conceitual faz o modelo responder pela faixa legal")

    # SIMETRIA, agora conferida termo por termo em vez de numa palavra só:
    # tudo o que a visão é perguntada, o OCR precisa saber confirmar. Sem isso,
    # resposta certa da visão vira dúvida na classificação.
    for termo in termos_citados:
        conferir(bool(motor.REGEX_PUBLI.search(termo)),
                 f"o OCR confirma {termo!r}, que a pergunta cita")


if __name__ == "__main__":
    print("=" * 74)
    print("  Termos que contam como declaração de publicidade")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    if falhas:
        print(f"  {len(falhas)} FALHA(S):")
        for f in falhas:
            print(f"    - {f}")
    else:
        print("  PASSOU.")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
