# -*- coding: utf-8 -*-
"""
Quantidade fecha pelo TOTAL do ciclo: qualquer tipo compensa qualquer tipo.
Mas se algum tipo específico ficou abaixo do combinado, isso pede
justificativa, mesmo com o total fechando.

POR QUE ESTE ARQUIVO EXISTE (16/09/2026, ampliado 17/09/2026)

Pedido do auditor, testando a tela do Financeiro, em três rodadas:

  1. "às vezes falta 1 combo de stories mas tem um post de feed/reels a
     mais, então dá pra calcular que quando tem 1 a menos e outro a mais,
     tá conforme, mas se tiver faltando, apenas se estiver faltando, aí
     sinaliza" (sugeria um grupo Feed/Reels, com Stories de fora)
  2. "o usuário tinha 10 reels e 10 stories no escopo do contrato, mas ele
     entregou 9 reels e 11 stories, entende? então isso está ok" (aqui é
     STORIES cobrindo REELS, o oposto do que a régua de grupo permitiria)
  3. resolvido com "qualquer coisa pode compensar qualquer coisa", mas
     "as entregas principais são stories, por isso temos que ter atenção a
     isso" -- daí a régua ficar sobre o TOTAL, com um aviso à parte quando
     STORIES especificamente cai, mesmo com o total fechando.

REVISADO EM 17/09/2026: a régua de atenção, que nasceu só para Stories,
generalizou para QUALQUER tipo, com o exemplo do próprio auditor: "10 lives
e 10 stories contratados, entrega 15 stories e 5 lives... compensou...
CICLO COMPLETO PORÉM com justificativa da alteração obrigatória". Resumo da
regra final: tudo igual ao escopo = CONFORME sem nada; total fecha mas com
substituição entre tipos = CONFORME com justificativa OBRIGATÓRIA; total não
fecha, mesmo somando tudo = INCOMPLETO com justificativa obrigatória. Os
cenários 1 e 2 abaixo, que antes eram "compensação livre, sem aviso", agora
também exigem justificativa: só ficaram sem aviso enquanto a régua olhava
só Stories.

Este teste não fala com o Google: escopo_e_entrega.py é módulo puro. Ver
teste_excecoes_do_escopo.py para o mesmo padrão de teste sobre escopo real.

Rodar:

    py testes\\teste_feed_reels_se_cobrem.py
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


def linha(handle, ciclo, tipo, post, data, marcacao="LINK", validacao="CONFORME"):
    return {"handle": handle, "ciclo": ciclo, "tipo": tipo, "post": post,
            "data_post": data, "marcacao": marcacao, "validacao": validacao}


def rodar():
    import escopo_e_entrega as ee

    print("--- 1. falta FEED, sobra REELS (os dois contratados): fecha CONFORME ---")
    # Os dois tipos precisam estar no escopo escrito, senão a sobra de REELS
    # também dispara "tipo entregue que não está no escopo", que é um achado
    # à parte (composição), não o que este cenário quer isolar (quantidade).
    lido = ee.ler_escopo("3 feed, 5 reels, 5 stories")
    entregas = (
        [linha("@a", "1", "FEED", i, f"{i:02d}/09/2026") for i in range(1, 2)]      # 1 de 3 feed
        + [linha("@a", "1", "REELS", i, f"{i:02d}/09/2026") for i in range(1, 8)]   # 7 de 5 reels, 2 de sobra
        + [linha("@a", "1", "STORIES", i, f"{i:02d}/09/2026") for i in range(1, 6)])  # 5 de 5 stories
    fecha = ee.fechar_ciclo(lido, ee.contar_entregas(entregas, "@a", "1"))
    conferir(fecha["situacao"] == ee.CONFORME,
             "1 feed + 7 reels + 5 stories = 13, contra 13 contratados, fecha CONFORME",
             fecha["situacao"])
    # A REGRA VIROU DE NOVO EM 23/09/2026, e agora no sentido contrário.
    #
    # Em 17/09 este teste passou a exigir justificativa aqui: FEED ficou 2
    # abaixo do combinado (1 de 3), e a régua generalizada (antes só de
    # Stories) pedia explicação de qualquer tipo nessa situação, mesmo com o
    # total fechando.
    #
    # O auditor reviu em 23/09, vendo a tela: "caso tenha sido compensada ou a
    # entrega bateu exatamente com o que está no escopo, essa parte da
    # Observação não precisa aparecer, quero que ela apareça apenas se a
    # entrega for divergente e MENOR". Aqui a entrega não é menor: o total
    # fecha, e o que caiu em FEED sobrou em REELS.
    #
    # O REGISTRO NÃO SE PERDEU NA TROCA, e é o que torna isto aceitável do
    # lado da auditoria: a NOTA do histórico passou a ser escrita pelo
    # programa, dizendo o que cobriu o quê (nota_automatica). Antes o registro
    # dependia de alguém digitar; agora ele existe sempre.
    conferir(not fecha["exige_justificativa"],
             "FEED ficou abaixo, mas REELS cobriu e o total fechou: não pede "
             "mais justificativa escrita à mão",
             str(fecha))
    conferir(any("FEED" in m and "coberto" in m for m in fecha["motivos"]),
             "e o motivo diz o que cobriu o FEED, com número",
             str(fecha["motivos"]))
    conferir("FEED" in fecha["nota_automatica"],
             "com o registro indo para a NOTA do histórico, escrito pelo programa",
             fecha["nota_automatica"])

    print()
    print("--- 2. o exemplo do auditor: 10 reels + 10 stories, entregou 9 + 11 ---")
    lido2 = ee.ler_escopo("10 reels, 10 stories")
    entregas2 = (
        [linha("@b", "1", "REELS", i, f"{i:02d}/09/2026") for i in range(1, 10)]     # 9 reels
        + [linha("@b", "1", "STORIES", i, f"{i:02d}/09/2026") for i in range(1, 12)])  # 11 stories
    fecha2 = ee.fechar_ciclo(lido2, ee.contar_entregas(entregas2, "@b", "1"))
    conferir(fecha2["situacao"] == ee.CONFORME,
             "9 reels + 11 stories = 20, contra 20 contratados, fecha CONFORME",
             fecha2["situacao"])
    # MESMA REVISÃO DE 23/09/2026 (ver a seção 1): REELS ficou 1 abaixo, e
    # Stories cobriu. É a frase literal do auditor sobre este exemplo, de
    # 16/09: "isso está ok".
    conferir(not fecha2["exige_justificativa"],
             "REELS caiu 1, Stories cobriu, total fecha: sem justificativa à mão",
             str(fecha2))
    conferir(any("1 REELS coberto(s) por 1 STORIES" in m for m in fecha2["motivos"]),
             "e o motivo diz exatamente quem cobriu quem",
             str(fecha2["motivos"]))

    print()
    print("--- 3. STORIES caindo, com o total fechando: compensação, não achado ---")
    lido3 = ee.ler_escopo("10 reels, 10 stories")
    entregas3 = (
        [linha("@c", "1", "REELS", i, f"{i:02d}/09/2026") for i in range(1, 12)]     # 11 reels de sobra
        + [linha("@c", "1", "STORIES", i, f"{i:02d}/09/2026") for i in range(1, 10)])  # só 9 de 10 stories
    fecha3 = ee.fechar_ciclo(lido3, ee.contar_entregas(entregas3, "@c", "1"))
    conferir(fecha3["situacao"] == ee.CONFORME,
             "11 reels + 9 stories = 20, contra 20 contratados: o total ainda fecha",
             fecha3["situacao"])
    # STORIES TINHA RÉGUA PRÓPRIA DESDE 16/09/2026 ("as entregas principais
    # são stories, por isso temos que ter atenção a isso"), e ela também caiu
    # em 23/09, pelo mesmo pedido das seções acima: com o total fechando, a
    # queda de um tipo é compensação, e compensação agora é registrada
    # automaticamente em vez de exigir texto de gente. O tipo que caiu
    # continua aparecendo, com número, tanto no motivo quanto na tabela.
    conferir(not fecha3["exige_justificativa"],
             "stories caiu 1, reels cobriu, total fecha: sem justificativa à mão",
             str(fecha3))
    conferir(any("1 STORIES coberto(s) por 1 REELS" in m for m in fecha3["motivos"]),
             "e o motivo diz que foi reels quem cobriu stories",
             str(fecha3["motivos"]))
    conferir("STORIES" in fecha3["nota_automatica"],
             "com a queda em stories registrada na NOTA, escrita pelo programa",
             fecha3["nota_automatica"])

    print()
    print("--- 3b. ORGÂNICO entra na soma, dos dois lados ---")
    # MEDIDO EM 16/09/2026, e foi o auditor quem viu: 16 stories contratados,
    # com 10 stories + 6 LIVES entregues, fechava CONFORME; os mesmos 10
    # stories + 6 ORGÂNICOS fechavam INCOMPLETO, porque a peça orgânica corria
    # num trilho paralelo desde 03/09/2026. "Eles fazem substituições de
    # acordo com a repercussão da entrega", e orgânico é uma delas.
    lido_org = ee.ler_escopo("16 COMBOS DE STORIES")
    entregas_org = (
        [linha("@e", "1", "STORIES", i, f"{i:02d}/09/2026") for i in range(1, 11)]
        + [linha("@e", "1", "STORIES", i, f"{i:02d}/08/2026", marcacao="ORGANICO")
           for i in range(1, 7)])
    fecha_org = ee.fechar_ciclo(lido_org, ee.contar_entregas(entregas_org, "@e", "1"))
    conferir(fecha_org["situacao"] == ee.CONFORME,
             "10 stories + 6 orgânicos cobrem 16 stories contratados",
             fecha_org["situacao"])

    # E O OUTRO LADO, que é o que impede cota de graça: orgânico ESCRITO no
    # contrato também soma no contratado. Sem isto, quem tivesse "12 postagens
    # orgânicas" no escopo ganharia 12 entregas sem entregar nada.
    lido_org2 = ee.ler_escopo("16 COMBOS DE STORIES + 12 POSTAGENS ORGANICAS")
    entregas_so_stories = [linha("@f", "1", "STORIES", i, f"{i:02d}/09/2026")
                           for i in range(1, 17)]
    fecha_org2 = ee.fechar_ciclo(lido_org2,
                                 ee.contar_entregas(entregas_so_stories, "@f", "1"))
    conferir(fecha_org2["situacao"] == ee.INCOMPLETO,
             "orgânico contratado e não entregue continua faltando",
             f"{fecha_org2['situacao']} {fecha_org2['total_entregue']}/"
             f"{fecha_org2['total_contratado']}")
    conferir(fecha_org2["total_contratado"] == 28,
             "com o orgânico contratado somando no total (16 + 12)",
             str(fecha_org2["total_contratado"]))

    print()
    print("--- 4. falta de verdade no total: continua INCOMPLETO ---")
    lido4 = ee.ler_escopo("5 feed")
    entregas4 = [linha("@d", "1", "FEED", i, f"{i:02d}/09/2026") for i in range(1, 3)]  # 2 de 5
    fecha4 = ee.fechar_ciclo(lido4, ee.contar_entregas(entregas4, "@d", "1"))
    conferir(fecha4["situacao"] == ee.INCOMPLETO,
             "2 de 5 feed, nada para compensar: continua incompleto",
             fecha4["situacao"])
    conferir(fecha4["exige_justificativa"], "e continua exigindo justificativa")


if __name__ == "__main__":
    print("=" * 74)
    print("  Quantidade pelo total do ciclo; Stories com atenção própria")
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
