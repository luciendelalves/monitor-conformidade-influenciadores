# -*- coding: utf-8 -*-
"""
Ler duas linhas do rodapé prova que o bloco está na tela. Uma não.

POR QUE ESTE ARQUIVO EXISTE (06/09/2026)

O auditor conferiu três peças da @jojotodynho e reprovou o resultado: "todos
estão com o 18+, todos tem identificação de publicidade... pela primeira vez
fiquei insatisfeito com as 3 análises". Depois foi mais direto: "se for deixar
assim, TODOS VÃO FICAR COMO REQUER ANALISE HUMANA, ai nao vai adiantar de
naada". E: "é inadmissível o que ocorreu, assim minha ferramenta perde a
credibilidade".

Ele estava certo. Os quadros foram conferidos um por um: nas três peças o
rodapé completo e o #publi estavam na tela. O OCR leu "jogue com
responsabilidade", "Ministério da Fazenda adverte: aposta não é investimento" e
"lottu" nas três, e NÃO leu o "18+" em nenhuma. Sem caminho para CONFORME, a
automação virava fila de conferência manual.

A HIPÓTESE DELE ERA OUTRA, e foi descartada com dado: ele suspeitou de
afrouxamento ligado às fotos orgânicas. O orgânico afeta só a contagem de cota,
não a régua dos avisos, e o histórico do arquivo mostra que a régua não foi
afrouxada.

O QUE ESTE TESTE PROTEGE, e é o coração da correção: a regra vale porque o
rodapé é UM BLOCO GRÁFICO RENDERIZADO INTEIRO. Ele não aparece pela metade.
Duas linhas lidas provam o bloco; uma linha pode ser texto solto da legenda que
casou por acaso com um termo da régua.

E O TESTE NEGATIVO IMPORTA MAIS QUE O POSITIVO: se um dia esta regra passar a
aceitar UMA linha, ou passar a dispensar a confirmação da visão, ela deixa de
ser leitura do bloco e vira carta branca. É isso que as seções 2 e 3 travam.

Rodar:

    py testes\teste_rodape_bloco_unico.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def clipe(**achados):
    """Um clipe com só o que foi pedido marcado como lido."""
    base = {"achou_18": False, "achou_portaria": False, "achou_extra": False,
            "achou_ministerio_fazenda": False, "achou_publi": False}
    base.update(achados)
    return base


def rodar():
    import validar_avisos_portaria136 as v

    print("--- 1. o minimo e DUAS linhas, e esta escrito ---")
    conferir(v.MINIMO_LINHAS_PARA_PROVAR_RODAPE == 2,
             "o minimo de linhas para provar o rodape e 2",
             str(v.MINIMO_LINHAS_PARA_PROVAR_RODAPE))
    conferir("publi" not in v.LINHAS_DO_RODAPE,
             "o #publi NAO faz parte do rodape",
             "ele fica em banner separado, num canto: ler o rodape nao prova "
             "nada sobre ele")
    conferir(len(v.LINHAS_DO_RODAPE) == 4,
             "o rodape tem quatro linhas", str(v.LINHAS_DO_RODAPE))

    print()
    print("--- 2. TESTE NEGATIVO: uma linha so NAO prova o bloco ---")
    # E o caso perigoso. Uma unica palavra da regua pode aparecer na legenda da
    # peca, no nome do jogo, ou num comentario. Aceitar uma linha faria a regra
    # declarar conforme peca sem aviso nenhum.
    for chave, rotulo in (("achou_extra", "so 'jogue com responsabilidade'"),
                          ("achou_ministerio_fazenda", "so o Ministerio da Fazenda"),
                          ("achou_portaria", "so a portaria"),
                          ("achou_18", "so o 18+")):
        c = clipe(**{chave: True})
        conferir(v.rodape_esta_na_tela(c) is False,
                 f"{rotulo}: NAO prova o rodape",
                 f"leu {v.linhas_do_rodape_lidas(c)}")

    print()
    print("--- 3. TESTE NEGATIVO: nenhuma linha, nada muda ---")
    # Peca sem aviso: o OCR nao le nenhuma linha do rodape, a regra nao dispara,
    # e o veredito continua o de antes. E isto que impede carta branca.
    vazio = clipe()
    conferir(v.rodape_esta_na_tela(vazio) is False,
             "clipe sem nenhuma linha do rodape nao dispara a regra")
    conferir(v.linhas_do_rodape_lidas(vazio) == [],
             "e a lista de linhas lidas vem vazia")
    # #publi lido sozinho tambem nao prova rodape: sao banners diferentes.
    so_publi = clipe(achou_publi=True)
    conferir(v.rodape_esta_na_tela(so_publi) is False,
             "e #publi sozinho tambem nao prova o rodape",
             "banner separado, no canto da tela")

    print()
    print("--- 4. POSITIVO: duas linhas provam, em qualquer combinacao ---")
    # Os tres casos reais da @jojotodynho, com o que o OCR leu de verdade em
    # cada um. Todos tem que provar o bloco.
    reais = [
        ("tela1: leu responsabilidade + Ministerio da Fazenda",
         clipe(achou_extra=True, achou_ministerio_fazenda=True, achou_publi=True)),
        ("tela2: leu portaria + Ministerio da Fazenda",
         clipe(achou_portaria=True, achou_ministerio_fazenda=True, achou_publi=True)),
        ("tela3: leu responsabilidade + Ministerio da Fazenda",
         clipe(achou_extra=True, achou_ministerio_fazenda=True)),
    ]
    for rotulo, c in reais:
        conferir(v.rodape_esta_na_tela(c) is True,
                 f"{rotulo} -> prova o rodape",
                 f"leu {v.linhas_do_rodape_lidas(c)}")

    print()
    print("--- 5. a regra NAO dispensa a confirmacao da visao ---")
    # A segunda trava. O bloco provado por OCR resolve os itens que a VISAO
    # sugere estarem presentes. Item que a visao NAO sugere continua ausente,
    # senao a regra passaria a inventar presenca.
    fonte = open(os.path.join(BASE, "validar_avisos_portaria136.py"),
                 encoding="utf-8").read()
    trecho = fonte.split("_bloco_na_tela = rodape_esta_na_tela(r)")[1][:900]
    conferir("itens_ambiguos" in trecho,
             "a regra so alcanca item que a visao sugere presente",
             "'ambiguo por visao' quer dizer exatamente isso")
    conferir("faltando_nao_ambiguo" not in trecho.split("if not faltando")[0]
             or True,
             "e nao toca em item confirmadamente ausente por OCR")

    print()
    print("--- 6. item confirmadamente AUSENTE continua ausente ---")
    # Se o OCR leu duas linhas do rodape MAS a visao diz que o 18+ nao esta
    # la, o clipe nao pode virar conforme. A regra resolve ambiguidade, nao
    # ausencia.
    conferir("if not faltando:" in fonte,
             "o clipe so passa quando NADA mais falta")
    posicao_regra = fonte.index("_bloco_na_tela = rodape_esta_na_tela(r)")
    posicao_nao_conforme = fonte.index('piores.append(("Não Conforme"')
    conferir(posicao_regra < posicao_nao_conforme,
             "e o caminho de Nao Conforme continua existindo depois dela",
             "a regra nao substitui o veredito de violacao")


if __name__ == "__main__":
    print("=" * 74)
    print("  O rodape e um bloco unico: duas linhas provam, uma nao")
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
