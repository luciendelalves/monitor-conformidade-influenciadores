# -*- coding: utf-8 -*-
"""
Entrega fora da plataforma (diária de gravação, evento) pode ser confirmada
e contar no total do ciclo, com justificativa obrigatória só quando ainda
sobra algo a explicar.

POR QUE ESTE TESTE EXISTE (17/09/2026)

Pedido do auditor: "para escopos que possuem entregas FORA da plataforma,
como diária de divulgação... precisa ter um campo para conferir manualmente
e lá a pessoa vai poder marcar um CHECK de que essas mídias foram entregues
e com justificativa obrigatória." Resposta escolhida, entre as duas
oferecidas: conta no total quando o item tem número (em posts); item sem
número (ex: "presença em eventos quando necessário") continua só
documentado, por não ter quantidade nenhuma pra somar.

A JUSTIFICATIVA MUDOU NO MESMO DIA. A primeira versão exigia sempre que o
CHECK era usado. Testando ao vivo (caso @saporitorenata: 12 stories + 5
reels batendo exato, só a diária faltando confirmar), isso confundia: a
tabela mostrava tudo ✅ e mesmo assim pedia justificativa, sem dizer por
quê. Regra final: se confirmar a entrega fora da plataforma é só o que
faltava pro ciclo fechar por inteiro (nada mensurável abaixo do contratado,
nada fora do escopo), não há substituição nenhuma para explicar, e a
justificativa não é mais exigida, só o motivo automático registrando a
confirmação. Se, mesmo assim, o ciclo continuar INCOMPLETO, a justificativa
volta a ser obrigatória (ver o cenário 3b).

Este teste não fala com o Google: escopo_e_entrega.py é módulo puro.

Rodar:

    py testes\\teste_declaracao_entrega_fora_da_plataforma.py
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

    print("--- 1. item COM número entra no total contratado ---")
    # "2 diárias de gravação" tem número em posts: soma no contratado, mesmo
    # sem nenhuma declaração ainda (letra morta seria o mesmo bug do
    # YouTube/Twitter de 16/09/2026, só que para fora da plataforma).
    lido = ee.ler_escopo("4 COMBOS DE STORIES + 2 DIARIAS DE GRAVACAO")
    entregas = [linha("@a", "1", "STORIES", i, f"{i:02d}/09/2026") for i in range(1, 5)]
    fecha = ee.fechar_ciclo(lido, ee.contar_entregas(entregas, "@a", "1"))
    conferir(fecha["total_contratado"] == 6,
             "as 2 diárias entram no total contratado (4 stories + 2)",
             fecha["total_contratado"])
    conferir(fecha["situacao"] == ee.INCOMPLETO,
             "sem ninguém confirmar as diárias, o ciclo fica incompleto (4 de 6)",
             fecha["situacao"])

    print()
    print("--- 2. confirmando com o CHECK, fecha o ciclo, SEM pedir justificativa ---")
    # REVISTO 17/09/2026, mesmo dia: a primeira versão deste teste exigia
    # justificativa sempre que o check era usado. Testando ao vivo (caso
    # @saporitorenata: stories e reels batendo exato, só a diária faltando
    # confirmar), ficou claro que isso confundia sem motivo: o ciclo fecha
    # por inteiro, nada mensurável ficou pra trás, não há nada de anômalo
    # para explicar. Ver o comentário de `exige_justificativa` em
    # fechar_ciclo.
    _, texto_diaria = next(qtd_texto for qtd_texto in lido["nao_mensuraveis"]
                           if "diaria" in qtd_texto[1].lower())
    fecha2 = ee.fechar_ciclo(
        lido, ee.contar_entregas(entregas, "@a", "1"),
        declaracoes_nao_mensuravel={texto_diaria: 2})
    conferir(fecha2["situacao"] == ee.CONFORME_COM_OBSERVACAO,
             "com as 2 diárias confirmadas, fecha por conferência humana",
             fecha2["situacao"])
    conferir(fecha2["total_entregue"] == 4 and fecha2["total_contratado"] == 6,
             "o total medido continua 4; quem fechou a conta foi a declaração",
             (fecha2["total_entregue"], fecha2["total_contratado"]))
    conferir(not fecha2["exige_justificativa"],
             "e a justificativa NÃO é obrigatória: o ciclo fechou por inteiro, "
             "sem nenhum tipo mensurável faltando",
             fecha2)
    conferir(any("fora da plataforma" in m and "2" in m for m in fecha2["motivos"]),
             "mas o motivo automático continua registrando o que foi confirmado",
             str(fecha2["motivos"]))

    print()
    print("--- 3. o CONTRATADO não infla com declaração exagerada ---")
    # O TETO CAIU PRO EXCEDENTE COBRIR OUTRA FALTA (23/09/2026, ver o teste
    # próprio disso: teste_compensacao_identificada.py). O que NÃO mudou, e é
    # o que esta seção prova, é o total_contratado: ele vem do escopo escrito
    # no cadastro, e declarar 999 não faz o contrato virar maior. O excedente
    # (999 - 2 = 997) até existe como sobra disponível, mas este cenário não
    # tem falta nenhuma pra ele cobrir (stories bateu 4 de 4 no que sobrou
    # depois da diária), então ele fica parado, sem efeito e sem pedir nada.
    fecha3 = ee.fechar_ciclo(
        lido, ee.contar_entregas(entregas, "@a", "1"),
        declaracoes_nao_mensuravel={texto_diaria: 999})
    conferir(fecha3["total_contratado"] == 6,
             "o contratado continua 6, não 4 + 999",
             fecha3["total_contratado"])
    conferir(fecha3["situacao"] == ee.CONFORME_COM_OBSERVACAO,
             "fecha certo mesmo com declaração exagerada",
             fecha3["situacao"])
    conferir(not fecha3["exige_justificativa"],
             "e não pede justificativa: o excedente existe, mas não foi usado "
             "pra cobrir falta nenhuma", fecha3)

    print()
    print("--- 3b. declaração parcial, ainda incompleto: some o detalhe por tipo ---")
    # PEDIDO DO AUDITOR (17/09/2026): o "ATENÇÃO: TIPO entregou X de Y, Z a
    # menos" só aparece pra ciclo incompleto DE VERDADE, sem nenhuma
    # declaração de fora da plataforma envolvida. Aqui a declaração existe
    # (mesmo não sendo suficiente pra fechar), então esse detalhe por tipo
    # não deve aparecer: quem confere já vê a declaração no motivo próprio
    # dela, dobrar a explicação confundiria mais que ajudaria.
    entregas_poucas = [linha("@a", "1", "STORIES", i, f"{i:02d}/09/2026")
                       for i in range(1, 3)]  # só 2 de 4 stories
    fecha3b = ee.fechar_ciclo(
        lido, ee.contar_entregas(entregas_poucas, "@a", "1"),
        declaracoes_nao_mensuravel={texto_diaria: 2})
    conferir(fecha3b["situacao"] == ee.INCOMPLETO,
             "2 stories + 2 diárias declaradas ainda não fecham os 6 contratados",
             fecha3b["situacao"])
    conferir(fecha3b["exige_justificativa"],
             "aqui a justificativa VOLTA a ser obrigatória: mesmo com o "
             "check marcado, ainda falta entrega de verdade",
             fecha3b)
    conferir(not any("entregou" in m and "STORIES" in m.upper() for m in fecha3b["motivos"]),
             "sem o detalhe por tipo, porque já existe declaração envolvida",
             str(fecha3b["motivos"]))
    conferir(any("Conferido à mão" in m or "fora da plataforma confirmada" in m
                for m in fecha3b["motivos"]),
             "a declaração aparece com o motivo próprio dela",
             str(fecha3b["motivos"]))

    print()
    print("--- 4. item SEM número nunca entra no total, com ou sem check ---")
    # "Presença em eventos quando necessário" não tem quantidade no texto:
    # não há o que declarar, fica só documentado (mesmo comportamento de
    # antes de 17/09/2026).
    lido_evento = ee.ler_escopo(
        "4 combos de stories + 2 diárias de gravação para a marca "
        "+1 reels feed + Presença em eventos quando necessário")
    fecha4 = ee.fechar_ciclo(
        lido_evento, ee.contar_entregas([], "@b", "1"),
        declaracoes_nao_mensuravel={"Presença em eventos quando necessário": 50})
    conferir(fecha4["total_contratado"] == 4 + 2 + 1,
             "eventos nunca soma: só stories (4) + diárias (2) + reels (1)",
             fecha4["total_contratado"])

    print()
    print("--- 5. live em horas continua fora, mesmo com CHECK ---")
    lido_live = ee.ler_escopo("10 COMBOS DE STORIES + 40 HORAS LIVE")
    _, texto_live = next(qtd_texto for qtd_texto in lido_live["nao_mensuraveis"]
                         if "hora" in qtd_texto[1].lower())
    fecha5 = ee.fechar_ciclo(
        lido_live, ee.contar_entregas([], "@c", "1"),
        declaracoes_nao_mensuravel={texto_live: 40})
    conferir(fecha5["total_contratado"] == 10,
             "live em horas não soma, mesmo declarado: a unidade não é posts",
             fecha5["total_contratado"])

    print()
    print("--- 6. exemplo ilustrativo, no mesmo formato do caso @saporitorenata ---")
    # PEDIDO DO AUDITOR (24/09/2026): outro caso trabalhado, agora com
    # "cobertura" em vez de "diária", pra mostrar que a mesma régua vale pra
    # todo o vocabulário de TERMOS_NAO_MENSURAVEIS, não só a diária de
    # gravação. HANDLE FICTÍCIO, criado só para este teste: não é
    # influenciador real, ao contrário do caso @saporitorenata (aquele
    # aconteceu de verdade e está registrado acima).
    #
    # O ESCOPO: "6 combos de stories + 1 cobertura de evento da marca". A
    # cobertura de evento é o mesmo tipo de peça que a diária: o download não
    # tem como ver alguém fisicamente presente num evento, só quem fechou o
    # ciclo confirma.
    lido_cobertura = ee.ler_escopo("6 COMBOS DE STORIES + 1 COBERTURA DE EVENTO DA MARCA")
    conferir(lido_cobertura["nao_mensuraveis"] == [(1, "1 COBERTURA DE EVENTO DA MARCA")],
             "o escopo reconhece a cobertura como fora da plataforma, com quantidade 1",
             lido_cobertura["nao_mensuraveis"])
    _, texto_cobertura = lido_cobertura["nao_mensuraveis"][0]

    # Os 6 stories batem exatos com o contratado, igual @saporitorenata batia
    # em stories e reels. Só falta a cobertura, que o download nunca vê.
    entregas_cobertura = [linha("@exemplo_teste_cobertura", "1", "STORIES", i, f"{i:02d}/09/2026")
                          for i in range(1, 7)]
    contadas_cobertura = ee.contar_entregas(entregas_cobertura, "@exemplo_teste_cobertura", "1")

    fecha6_sem_confirmar = ee.fechar_ciclo(lido_cobertura, contadas_cobertura)
    conferir(fecha6_sem_confirmar["situacao"] == ee.INCOMPLETO,
             "sem confirmar a cobertura, falta 1 dos 7 contratados (6 stories + 1 cobertura)",
             fecha6_sem_confirmar["situacao"])

    fecha6 = ee.fechar_ciclo(
        lido_cobertura, contadas_cobertura,
        declaracoes_nao_mensuravel={texto_cobertura: 1})
    conferir(fecha6["total_contratado"] == 7,
             "o contratado soma 6 stories + 1 cobertura", fecha6["total_contratado"])
    conferir(fecha6["situacao"] == ee.CONFORME_COM_OBSERVACAO,
             "confirmando a cobertura, o ciclo fecha por inteiro", fecha6["situacao"])
    conferir(not fecha6["exige_justificativa"],
             "sem justificativa: confirmar a cobertura foi só o que faltava",
             fecha6)
    conferir(any("fora da plataforma" in m and "1" in m for m in fecha6["motivos"]),
             "o motivo automático registra a cobertura confirmada",
             str(fecha6["motivos"]))


if __name__ == "__main__":
    print("=" * 74)
    print("  Entrega fora da plataforma: check + justificativa obrigatória")
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
