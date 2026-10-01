# -*- coding: utf-8 -*-
"""
O teto do Instagram aguenta a operação real de seis pessoas?

POR QUE ESTE TESTE EXISTE (31/08/2026)

O auditor levantou os números da operação, e eles mudaram o que se sabia:

  - são SEIS pessoas, não cinco
  - cada uma tem a PRÓPRIA conta do Instagram
  - as carteiras são desiguais: 10, 9, 8, 8, 8 e 2 influenciadores, 45 no total
  - cada pessoa baixa em média 2 stories por dia de cada influenciador seu
  - os influenciadores postam mais ou menos em dias alternados, um dia sim e um
    dia não, e é isso que faz o volume real (48 arquivos por dia medidos no
    Drive deles em agosto) bater com a conta teórica (cerca de 45)

Este teste NÃO chama o Instagram e NÃO sobe teto nenhum. Ele simula o consumo
contra o contador de verdade do programa, com o estado guardado numa pasta
temporária. Isso é de propósito: subir o teto para experimentar desfaz a única
evidência de que o programa é disciplinado, e essa regra não se quebra nem para
testar.

O QUE ELE PROVA, E O ITEM 4 É O QUE MOTIVOU ESCREVÊ-LO

  1. o contador é por CONTA, e contas diferentes não se misturam
  2. o teto de 20 virou recomendação (17/09/2026): passar dele não trava mais,
     só avisa
  3. o consumo diário de cada carteira, para a decisão de teto sair de número
     medido e não de estimativa
  4. a regra "uma conta por dia por máquina" IMPEDE seis contas na mesma
     máquina. Ela existe por motivo medido (em 27/08 duas contas saíram do mesmo
     computador e uma foi barrada), e é justamente por isso que o desenho de
     servidor único com seis contas não fecha

    py testes\teste_teto_com_seis_contas.py
"""
import json
import os
import sys
import tempfile

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


# A operação real, informada pelo auditor em 31/08/2026. Os nomes das pessoas
# ficam fora: para o teto só a quantidade importa.
CARTEIRAS = [10, 9, 8, 8, 8, 2]
STORIES_POR_INFLUENCIADOR_POR_DIA = 2

# MEDIDO EM 31/08/2026 às 19h05, e corrige a premissa que este teste usava.
#
# A primeira versão usava 2, que era o número repetido no PROMPT_CONTINUACAO
# desde o começo, e nunca havia sido medido. Medição limpa, com UM link isolado
# (sem pausa e sem outro download no meio, para não confundir): o contador da
# conta @candyboxconfeitaria foi de 15 para 16 depois de um download de story
# bem-sucedido, com arquivo no Drive e linha criada na Monitoramento.
#
# ALCANCE DA MEDIÇÃO, porque generalizar aqui seria repetir o erro: vale para
# story COM o número no link, que é o caso comum. Story SEM o número custou 2 no
# mesmo dia e não baixou nada, porque gastou a consulta pelo @. Reel e post não
# foram medidos.
CHAMADAS_POR_DOWNLOAD = 1

# Um dia sim, um dia não: em média metade da carteira posta em cada dia.
FRACAO_QUE_POSTA_POR_DIA = 0.5


def preparar(fluxo, pasta):
    """Aponta o estado da conta para uma pasta temporária, para o teste não
    tocar no contador de verdade da máquina."""
    fluxo.ARQUIVO_ESTADO_CONTA = os.path.join(pasta, "estado_conta_instagram.json")
    # DESLIGA O CONTADOR COMPARTILHADO (24/09/2026): sem isto,
    # _contar_uso_instagram/situacao_da_conta falariam de verdade com a
    # planilha de fechamentos desta máquina, que este teste nunca isolou
    # porque o mecanismo não existia quando ele foi escrito.
    fluxo._planilha_fechamentos_id = lambda: None
    return fluxo


def zerar(fluxo):
    if os.path.exists(fluxo.ARQUIVO_ESTADO_CONTA):
        os.remove(fluxo.ARQUIVO_ESTADO_CONTA)


def rodar():
    import fluxo_downloads as fluxo

    pasta = tempfile.mkdtemp(prefix="teto_seis_contas_")
    preparar(fluxo, pasta)
    conta_original = fluxo.USUARIO_DOS_COOKIES
    teto = fluxo.limite_diario_vigente()

    print(f"       teto em uso: {teto} chamadas por dia por conta")
    print(f"       estado do teste em pasta temporária, o contador real não é tocado")
    print()

    try:
        print("--- 1. o contador é por conta, e contas diferentes não se misturam ---")
        zerar(fluxo)
        fluxo.USUARIO_DOS_COOKIES = "conta_pessoa_1"
        for _ in range(5):
            fluxo._contar_uso_instagram()
        pode1, _motivo1, usados1, restantes1 = fluxo.situacao_da_conta()
        conferir(usados1 == 5, "a primeira conta contou 5", str(usados1))
        conferir(restantes1 == teto - 5, "e o restante bate", str(restantes1))

        # Outra conta, MESMO arquivo de estado: o contador dela tem que ser
        # próprio. Se fosse compartilhado, o teto valeria para a soma e a
        # segunda pessoa herdaria o consumo da primeira.
        fluxo.USUARIO_DOS_COOKIES = "conta_pessoa_2"
        estado = json.load(open(fluxo.ARQUIVO_ESTADO_CONTA, encoding="utf-8-sig"))
        conferir("conta_pessoa_1" in estado,
                 "o estado guarda a conta pelo nome dela")
        conferir(estado["conta_pessoa_1"]["usados"] == 5,
                 "e o consumo da primeira continua registrado nela",
                 str(estado.get("conta_pessoa_1")))

        print()
        print("--- 2. no teto, a conta continua sendo usada (virou recomendação) ---")
        # REVISADO EM 17/09/2026: decisão do auditor, depois de eu levantar o
        # risco pra metodologia de subida medida. O teto diário parou de
        # travar; virou só um aviso ("teto recomendado"). As outras duas
        # travas desta função (uma conta por dia, pausa após bloqueio real)
        # não mudaram, ver o item 4 abaixo.
        zerar(fluxo)
        fluxo.USUARIO_DOS_COOKIES = "conta_no_limite"
        for _ in range(teto):
            fluxo._contar_uso_instagram()
        pode, motivo, usados, restantes = fluxo.situacao_da_conta()
        conferir(pode, f"com {teto} usados, a conta continua podendo ser usada")
        conferir(restantes == 0, "o restante mostrado é zero", str(restantes))
        conferir("teto recomendado" in motivo.lower(),
                 "a mensagem diz que é o teto recomendado, não uma trava", motivo[:90])
        conferir("continua funcionando" in motivo.lower(),
                 "e deixa claro que não parou nada", motivo[:90])

        print()
        print("--- 3. o consumo de cada carteira, contra o teto ---")
        # Aqui o teste não julga: ele CALCULA e mostra. Quem decide o teto é o
        # auditor, e a decisão precisa do número na frente.
        total_downloads = 0
        estouraram = 0
        for carteira in CARTEIRAS:
            postam = carteira * FRACAO_QUE_POSTA_POR_DIA
            downloads = postam * STORIES_POR_INFLUENCIADOR_POR_DIA
            chamadas = downloads * CHAMADAS_POR_DOWNLOAD
            total_downloads += downloads
            cabe = chamadas <= teto
            if not cabe:
                estouraram += 1
            marca = "cabe" if cabe else "ESTOURA"
            no_limite = " (exatamente no limite)" if chamadas == teto else ""
            print(f"       carteira de {carteira:>2}: "
                  f"{postam:>4.1f} postam, {downloads:>4.1f} downloads, "
                  f"{chamadas:>4.1f} chamadas  ->  {marca}{no_limite}")

        conferir(estouraram == 0,
                 f"nenhuma das {len(CARTEIRAS)} carteiras estoura o teto de {teto} "
                 f"em dia normal",
                 f"{estouraram} estouraram")

        maior = max(CARTEIRAS) * FRACAO_QUE_POSTA_POR_DIA * \
            STORIES_POR_INFLUENCIADOR_POR_DIA * CHAMADAS_POR_DOWNLOAD
        conferir(maior <= teto / 2,
                 f"a maior carteira usa no máximo metade do teto em dia normal "
                 f"({maior:.0f} de {teto})",
                 "com a medição de 1 chamada por download, a folga é bem maior "
                 "do que se supunha")

        # O dia atípico: TODOS os influenciadores da maior carteira postam.
        # Este era o caso que, com a premissa antiga de 2 chamadas, fazia a
        # maior carteira parar no meio do dia. Com o número medido, ele cabe.
        pior = max(CARTEIRAS) * STORIES_POR_INFLUENCIADOR_POR_DIA * CHAMADAS_POR_DOWNLOAD
        print(f"       dia atípico, todos os {max(CARTEIRAS)} da maior carteira postando: "
              f"{pior:.0f} chamadas, {pior / teto:.1f}x o teto")
        conferir(pior <= teto,
                 f"e até o dia em que TODOS postam cabe no teto "
                 f"({pior:.0f} de {teto})",
                 "com a premissa antiga de 2 chamadas isso era o dobro do teto")

        print(f"       total da operação: {total_downloads:.0f} downloads por dia")
        # Bate com a medição independente feita no Drive do Marketing.
        conferir(40 <= total_downloads <= 55,
                 f"o total ({total_downloads:.0f}) bate com os 48 arquivos por dia "
                 f"medidos no Drive deles em agosto",
                 "duas contas independentes chegando perto dá confiança nas duas")

        print()
        print("--- 4. seis contas na MESMA máquina: a regra não deixa ---")
        # ESTE É O ACHADO QUE MOTIVOU O TESTE. A regra existe por motivo medido
        # (27/08: duas contas do mesmo computador, uma barrada), e é ela que
        # torna o servidor único incompatível com seis contas.
        zerar(fluxo)
        fluxo.USUARIO_DOS_COOKIES = "conta_pessoa_1"
        fluxo._contar_uso_instagram()
        dona = fluxo.conta_do_dia_nesta_maquina()
        conferir(dona == "conta_pessoa_1",
                 "a primeira conta que usa prende a máquina no dia", str(dona))

        fluxo.USUARIO_DOS_COOKIES = "conta_pessoa_2"
        pode2, motivo2, _u, _r = fluxo.situacao_da_conta()
        conferir(not pode2,
                 "a segunda conta é BARRADA na mesma máquina, no mesmo dia")
        conferir("uma conta por dia por máquina" in motivo2,
                 "e a mensagem diz a regra", motivo2[:110])
        conferir("endereço de rede" in motivo2,
                 "e diz o motivo, que é o padrão que leva ao bloqueio",
                 motivo2[:110])

        # E as outras quatro, para deixar claro que não é caso isolado.
        barradas = 0
        for n in range(3, 7):
            fluxo.USUARIO_DOS_COOKIES = f"conta_pessoa_{n}"
            pode_n, _m, _u, _r = fluxo.situacao_da_conta()
            if not pode_n:
                barradas += 1
        conferir(barradas == 4,
                 "as outras quatro contas também ficam barradas no mesmo dia",
                 f"{barradas} de 4")
        print("       CONSEQUÊNCIA: num servidor único, a primeira pessoa que baixar")
        print("       impede as outras cinco até o dia virar. Não é defeito da regra:")
        print("       é o desenho de servidor único com seis contas que não fecha.")

        print()
        print("--- 5. voltar para a conta do dia continua liberado ---")
        # A regra não pode virar prisão: quem já é a dona do dia segue podendo.
        fluxo.USUARIO_DOS_COOKIES = "conta_pessoa_1"
        pode1b, motivo1b, _u, _r = fluxo.situacao_da_conta()
        conferir(pode1b, "a conta dona do dia continua podendo usar", motivo1b[:80])

        print()
        print("--- 6. trocar de conta SEM baixar não prende a máquina ---")
        zerar(fluxo)
        fluxo.USUARIO_DOS_COOKIES = "conta_que_so_olhou"
        fluxo.situacao_da_conta()   # só consultou, não usou
        conferir(fluxo.conta_do_dia_nesta_maquina() is None,
                 "consultar a situação não prende a máquina",
                 "prender por consulta bloquearia a máquina sem uso nenhum")

    finally:
        fluxo.USUARIO_DOS_COOKIES = conta_original


if __name__ == "__main__":
    print("=" * 74)
    print("  O teto do Instagram contra a operação real de seis pessoas")
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
