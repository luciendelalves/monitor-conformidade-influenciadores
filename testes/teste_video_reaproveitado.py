# -*- coding: utf-8 -*-
"""
Prova que vídeo reaproveitado gera linha e aviso, em vez de ser engolido.

POR QUE ESTE TESTE EXISTE (31/08/2026)

O auditor informou que reaproveitar vídeo é vedado em CONTRATO: o influenciador
não pode republicar uma peça antiga como se fosse nova. Ao conferir o código,
apareceu que o programa fazia o contrário do necessário.

O que acontecia quando o mesmo vídeo era baixado de novo:

    achava pela impressão digital do arquivo
    avisava "já está na pasta, não subi de novo"
    RETORNAVA ALI, sem criar a linha na Monitoramento

Consequência: o segundo post não ganhava linha, nunca era auditado, o
reaproveitamento não ficava registrado, e a fila marcava "BAIXADO E
ORGANIZADO", que lê como sucesso. O programa engolia em silêncio exatamente o
achado que deveria levantar.

A DETECÇÃO nunca foi o problema, e é bom deixar isso claro para quem vier: ela
já funcionava, por conteúdo, comparando a impressão digital que o próprio Drive
calcula. O que estava errado era a REAÇÃO.

Não fala com o Drive nem com planilha: as duas pontas são dubladas.

    py testes\teste_video_reaproveitado.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fluxo_downloads as fluxo

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    print("--- 1. o codigo nao retorna mais antes de criar a linha ---")
    import inspect
    fonte = inspect.getsource(fluxo.enviar_para_drive)
    trecho = fonte.split("if repetido:")[1].split("id_pasta_ciclo")[0]
    conferir("registrar_na_monitoramento" in trecho,
             "o caminho do vídeo repetido chama registrar_na_monitoramento",
             "sem isso o segundo post fica sem linha e nunca é auditado")
    # A MARCA VIROU "PEÇA REAPROVEITADA" EM 02/09/2026, quando story de foto
    # deixou de ser recusado no download. A comparação sempre foi byte a byte,
    # então ela já alcançava imagem; era o texto que dizia vídeo. Aqui a
    # conferência passou a olhar o radical, para não travar na palavra exata.
    conferir("REAPROVEITAD" in trecho,
             "e avisa com a palavra REAPROVEITADA, não com 'não subi de novo'",
             trecho[:80])
    conferir("VÍDEO REAPROVEITADO" not in trecho,
             "sem chamar de vídeo o que pode ser foto")
    conferir("contrato" in trecho.lower(),
             "dizendo que é vedado em contrato, que é o motivo de importar")

    print()
    print("--- 2. a busca e por CONTEUDO, e nao por nome ---")
    fonte_busca = inspect.getsource(fluxo.procurar_arquivo_repetido)
    conferir("_impressao_digital" in fonte_busca,
             "compara a impressão digital do arquivo")
    conferir("md5Checksum" in fonte_busca,
             "contra a que o próprio Drive calcula")
    conferir("mesmo_nome or mesmo_conteudo" in fonte_busca,
             "e basta uma das duas vias bater")
    print("         (importa porque o mesmo vídeo salvo com outro nome, ou com")
    print("          numeração de tela diferente, continua sendo o mesmo vídeo)")

    print()
    print("--- 3. a impressao digital reconhece o mesmo arquivo ---")
    import tempfile
    pasta = tempfile.mkdtemp()
    a = os.path.join(pasta, "a.mp4")
    b = os.path.join(pasta, "b_outro_nome.mp4")
    c = os.path.join(pasta, "c_diferente.mp4")
    conteudo = os.urandom(200000)
    for caminho, dados in ((a, conteudo), (b, conteudo), (c, os.urandom(200000))):
        with open(caminho, "wb") as f:
            f.write(dados)

    da, db, dc = (fluxo._impressao_digital(x) for x in (a, b, c))
    conferir(da == db, "mesmo conteúdo com nome diferente dá a mesma digital")
    conferir(da != dc, "conteúdo diferente dá digital diferente")

    print()
    print("--- 4. qual e a janela de busca, em cada layout ---")
    # Isto é o limite conhecido, e fica no teste para ninguém supor que a busca
    # alcança mais do que alcança.
    import datetime
    data = datetime.date(2026, 8, 26)
    layout_antes = fluxo.LAYOUT_PASTAS
    try:
        fluxo.LAYOUT_PASTAS = fluxo.LAYOUT_TESTE
        caminho_teste = fluxo.caminho_ate_influenciador("alguem", data, "EDS")
        fluxo.LAYOUT_PASTAS = fluxo.LAYOUT_MARKETING
        caminho_mkt = fluxo.caminho_ate_influenciador("alguem", data, "EDS")
    finally:
        fluxo.LAYOUT_PASTAS = layout_antes

    print(f"         layout de teste    : {caminho_teste}")
    print(f"         layout do Marketing: {caminho_mkt}")
    # MUDOU EM 01/09/2026, E ESTREITOU A BUSCA NO LAYOUT DE TESTE.
    #
    # Antes o layout de teste devolvia só ["@handle"], então a busca de vídeo
    # reaproveitado cobria a pasta inteira do influenciador, sem limite de mês.
    # Agora os dois layouts montam bet / ano / mês / @handle, então a janela do
    # teste passou a ser a mesma do Marketing: UM mês e UMA bet.
    #
    # Isso é perda de alcance no layout de teste, e está aqui escrito para não
    # passar por melhoria. Foi aceito porque o alcance que importa é o do
    # Marketing, que é onde a auditoria acontece, e ter o teste com alcance
    # MAIOR que a produção esconderia justamente este limite: peça reaproveitada
    # de um mês para o outro não é detectada em nenhum dos dois.
    conferir(caminho_teste == caminho_mkt,
             "os dois layouts têm a mesma janela, e o de teste deixou de ser "
             "mais largo que a produção",
             f"{caminho_teste} != {caminho_mkt}")
    conferir(len(caminho_teste) == 4,
             "e a janela é bet / ano / mês / @influenciador nos dois",
             str(caminho_teste))
    conferir(len(caminho_mkt) == 4 and caminho_mkt[2].endswith("Agosto"),
             "no do Marketing ela fica presa a UM mês e UMA marca",
             str(caminho_mkt))
    print("         (o auditor aceitou a janela de um mês como piso; alargar")
    print("          para o ano inteiro é melhoria registrada, não feita)")


if __name__ == "__main__":
    print("=" * 74)
    print("  Vídeo reaproveitado: gera linha e aviso, não silêncio")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
