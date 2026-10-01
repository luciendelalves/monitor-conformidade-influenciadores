# -*- coding: utf-8 -*-
r"""
Prova o cruzamento do ESCOPO contratado com o que foi ENTREGUE, por ciclo.

TODOS OS TEXTOS DE ESCOPO AQUI SÃO REAIS, lidos no cadastro do Marketing em
03/09/2026 (76 ativos, 69 com escopo preenchido, 59 textos distintos). Não são
exemplos inventados: cada um deles é um contrato de verdade, e cada um trouxe um
caso que o motor tem que tratar.

O MOLDE vem da aba `Achado01_EntregaEComprovacao` da planilha de achados da
própria auditoria, que já fazia esse cruzamento à mão em 260 linhas.

AS DUAS DEFINIÇÕES QUE O AUDITOR DEU, e que este teste guarda:

  1. "1 combo = 1 post do dia". Confirmado depois no dado histórico do próprio
     Marketing (Ciclos MKT.xlsx): a numeração de POST deles é uma por data.
  2. "a ideia é seguir o escopo, e se mudarem a entrega, o ciclo vai fechar como
     NÃO CONFORME e vai ter que ter uma justificativa embaixo". REVISADO em
     09/09/2026: o "NÃO CONFORME" próprio saiu (colidia com o veredito
     regulatório por peça), mas a exigência de justificativa quando a
     composição muda continua, agora independente da situação do ciclo. Ver
     a seção 9 e o comentário de exige_justificativa em escopo_e_entrega.py.

    py testes\teste_escopo_e_entrega.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

falhas = []

# ESCOPOS REAIS, do cadastro, em 03/09/2026.
E_SIMPLES = "12 COMBOS DE STORIES"                      # @adrianamunizofc
E_DOIS_TIPOS = "6 COMBOS DE STORIES + 4 REELS"          # @babamarcoss
E_TRES_TIPOS = "12 STORIES + 6 REELS + 2 YOUTUBE + 2 TWITTER"   # @centraldotimao
E_PERIODICIDADE = "MENSAL: 2 COMBOS DE STORIES\nANUAL:  6 POSTS NO FEED"  # @leosantana
E_ALTERNATIVA = "5 FEED (OU REELS), 6 COMBOS STORIES, 8 TWEETS E 4 YOUTUBE"  # @bruno.formiga
E_NAO_MENSURAVEL = ("4 combos de stories + 2 diárias de gravação para a marca "
                    "+1 reels feed + Presença em eventos quando necessário")  # @juremafox
E_ORGANICO_NO_ESCOPO = ("8 combos de stories + 2 feeds + 10 publicações contendo "
                        "marcação da logo + presença em 4 eventos ao longo do ano "
                        "+ viagens")  # @recifeordinario
E_SEM_ESCOPO = "Não informado"                          # @carlinhos
E_INDEFINIDO = "Indefinido"                             # @linkocto


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def linha(handle, ciclo, tipo, post, data, marcacao="LINK",
          validacao="CONFORME"):
    # O veredito entra por padrão como CONFORME porque, desde 31/08/2026, só
    # peça CONFORME conta para a cota. Sem ele, os testes de 6 a 12, que são
    # sobre a CONTA do escopo, fechariam todos em "falta análise de peça" e não
    # exercitariam mais o que foram escritos para exercitar. Quem quer testar o
    # veredito passa o valor na mão, como faz a seção 13.
    return {"handle": handle, "ciclo": ciclo, "tipo": tipo, "post": post,
            "data_post": data, "marcacao": marcacao, "validacao": validacao}


def rodar():
    import escopo_e_entrega as ee

    print("--- 1. escopo simples, o caso de 32 dos 69 contratos ---")
    lido = ee.ler_escopo(E_SIMPLES)
    conferir(lido["contratado"] == {"STORIES": 12},
             "12 COMBOS DE STORIES vira 12 de STORIES", str(lido["contratado"]))

    print()
    print("--- 2. mais de um tipo no mesmo escopo ---")
    conferir(ee.ler_escopo(E_DOIS_TIPOS)["contratado"] == {"STORIES": 6, "REELS": 4},
             "stories e reels", str(ee.ler_escopo(E_DOIS_TIPOS)["contratado"]))
    lido_tres = ee.ler_escopo(E_TRES_TIPOS)
    tres = lido_tres["contratado"]
    conferir(tres.get("STORIES") == 12 and tres.get("REELS") == 6,
             "stories e reels entram na cota", str(tres))
    # MUDOU EM 03/09/2026, pelo cruzamento com o papel de trabalho. YouTube e
    # Twitter saíram da cota e foram para contratado_nao_validavel. O motivo está
    # em TIPOS_NAO_VALIDAVEIS: a régua da portaria não alcança esses tipos, e
    # como só peça CONFORME conta, a cota deles NUNCA fecharia. A aba Achado03
    # mede isso: 23 linhas de X/TWITTER com "NÃO FOI POSSÍVEL ANALISAR".
    nao_validavel = lido_tres["contratado_nao_validavel"]
    conferir(nao_validavel.get("YOUTUBE") == 2
             and nao_validavel.get("X/TWITTER") == 2,
             "youtube e twitter ficam separados, porque a régua não os alcança",
             str(nao_validavel))
    conferir("YOUTUBE" not in tres and "X/TWITTER" not in tres,
             "e por isso NÃO entram na cota, que nunca fecharia",
             "só peça CONFORME conta, e esses tipos não recebem veredito")

    print()
    print("--- 3. periodicidade misturada: o ANUAL fica FORA do ciclo ---")
    # @leosantana: "MENSAL: 2 COMBOS DE STORIES / ANUAL: 6 POSTS NO FEED".
    # Somar o anual na cota do ciclo cobraria seis feeds por mês de quem deve
    # seis por ano.
    lido = ee.ler_escopo(E_PERIODICIDADE)
    conferir(lido["contratado"] == {"STORIES": 2},
             "só o mensal entra na cota do ciclo", str(lido["contratado"]))
    conferir(any("FEED" in a.upper() for a in lido["anuais"]),
             "e o item anual aparece à parte, para conferência",
             str(lido["anuais"]))

    print()
    print("--- 4. entrega alternativa: 5 FEED (OU REELS) ---")
    lido = ee.ler_escopo(E_ALTERNATIVA)
    conferir(lido["alternativas"] and lido["alternativas"][0][0] == 5,
             "a quantidade da alternativa é 5", str(lido["alternativas"]))
    conferir(lido["alternativas"] and set(lido["alternativas"][0][1]) == {"FEED", "REELS"},
             "e ela é cumprida por FEED ou REELS", str(lido["alternativas"]))
    conferir(lido["contratado"].get("STORIES") == 6,
             "e o resto do escopo continua sendo lido", str(lido["contratado"]))

    print()
    print("--- 5. o que download NÃO mede não é ignorado ---")
    # É a diferença entre o fechamento ser honesto e ser confiante demais: um
    # ciclo com "presença em eventos" no escopo não pode fechar CONFORME olhando
    # só os posts.
    lido = ee.ler_escopo(E_NAO_MENSURAVEL)
    conferir(lido["contratado"].get("STORIES") == 4, "conta os 4 combos",
             str(lido["contratado"]))
    conferir(lido["contratado"].get("REELS") == 1, "e o reels", str(lido["contratado"]))
    # TUPLA (quantidade, texto) DESDE 17/09/2026, e não mais texto puro: dá
    # pra distinguir o item que TEM número em posts (diária) do que não tem
    # (presença em eventos, sem quantidade nenhuma no texto).
    conferir(any("diária" in texto.lower() for _, texto in lido["nao_mensuraveis"]),
             "as diárias de gravação viram conferência humana",
             str(lido["nao_mensuraveis"]))
    conferir(any(qtd == 2 and "diária" in texto.lower()
                for qtd, texto in lido["nao_mensuraveis"]),
             "e a diária guarda a quantidade (2), pra poder ser confirmada e contada",
             str(lido["nao_mensuraveis"]))
    conferir(any("evento" in texto.lower() for _, texto in lido["nao_mensuraveis"]),
             "e a presença em eventos também",
             str(lido["nao_mensuraveis"]))
    conferir(any(qtd is None and "evento" in texto.lower()
                for qtd, texto in lido["nao_mensuraveis"]),
             "mas eventos não tem quantidade (o texto não tem número nenhum)",
             str(lido["nao_mensuraveis"]))

    print()
    print("--- 6. o fechamento do ciclo ---")
    entregas = [linha("@x", "5", "STORIES", 1, "01/09/2026"),
                linha("@x", "5", "STORIES", 2, "03/09/2026"),
                linha("@x", "5", "STORIES", 2, "03/09/2026"),   # 2ª tela, mesmo post
                linha("@x", "5", "REELS", 1, "04/09/2026")]
    contagem = ee.contar_entregas(entregas, "@x", "5")
    conferir(contagem["entregue"] == {"STORIES": 2, "REELS": 1},
             "conta POST, e não linha: a segunda tela do mesmo post não soma",
             str(contagem["entregue"]))

    fecha = ee.fechar_ciclo(ee.ler_escopo("2 COMBOS DE STORIES + 1 REELS"), contagem)
    conferir(fecha["situacao"] == ee.CONFORME,
             "escopo cumprido fecha CONFORME", fecha["situacao"])
    conferir(not fecha["exige_justificativa"],
             "e não exige justificativa")

    print()
    print("--- 7. falta quantidade: INCOMPLETO, e isso já exige justificativa ---")
    # MUDOU EM 09/09/2026: antes, INCOMPLETO sozinho não exigia justificativa
    # ("o ciclo ainda pode ser cumprido"). Com o fim da tela virando "Solicitar
    # pagamento?", exige_justificativa passou a significar "posso solicitar
    # sem escrever nada?", e a resposta pra um ciclo que não fechou é não,
    # mesmo que ele ainda possa fechar depois. Ver ENTREGA_NAO_FECHOU.
    fecha = ee.fechar_ciclo(ee.ler_escopo("6 COMBOS DE STORIES + 1 REELS"), contagem)
    conferir(fecha["situacao"] == ee.INCOMPLETO, "fecha INCOMPLETO", fecha["situacao"])
    conferir(fecha["faltando"] == {"STORIES": 4}, "dizendo o que falta",
             str(fecha["faltando"]))
    conferir(fecha["exige_justificativa"],
             "e já exige justificativa para solicitar pagamento mesmo assim")

    print()
    print("--- 8. ENTREGAR MAIS DO MESMO TIPO não é desvio ---")
    # Na planilha de achados, 13 combos contra 12 contratados fechou ✅.
    fecha = ee.fechar_ciclo(ee.ler_escopo("1 COMBOS DE STORIES + 1 REELS"), contagem)
    conferir(fecha["situacao"] == ee.CONFORME,
             "2 stories entregues contra 1 contratado continua CONFORME",
             fecha["situacao"])

    print()
    print("--- 9. MUDANÇA DE COMPOSIÇÃO exige justificativa, e é INDEPENDENTE ---")
    # REVISADO em 09/09/2026, alinhado ao RA Nº 16/2026 (Achado 1): a cota
    # cumprida x não cumprida é um critério binário; composição diferente do
    # contratado é registrada e exige justificativa, mas não decide mais a
    # situação do ciclo sozinha. Dois cenários provam a independência.
    #
    # 9a REVISADO EM 16/09/2026, com a régua de quantidade virando TOTAL do
    # ciclo ("qualquer coisa compensa qualquer coisa"): FEED contratado sem
    # entrega, mas REELS veio fora do escopo cobrindo o total (2 stories + 1
    # feed contratados = 3; 2 stories + 1 reels entregues = 3 também). Isso
    # não fecha mais INCOMPLETO por quantidade: fecha CONFORME, e A
    # JUSTIFICATIVA CONTINUA EXIGIDA MESMO ASSIM, só que agora só pela
    # composição (fora_do_escopo), não mais pela falta.
    fecha = ee.fechar_ciclo(ee.ler_escopo("2 COMBOS DE STORIES + 1 FEED"), contagem)
    conferir(fecha["situacao"] == ee.CONFORME,
             "REELS fora do escopo cobre o FEED que faltou no total: fecha CONFORME",
             fecha["situacao"])
    # REVISADO DE NOVO EM 23/09/2026: a composição trocada deixou de EXIGIR
    # texto escrito à mão, e passou a ser registrada pelo programa. O pedido
    # do auditor limitou a Observação obrigatória ao caso "divergente e
    # menor", e depois ele confirmou, com a ressalva na mão, que isso alcança
    # também o tipo fora do escopo. O que não podia acontecer era o rastro
    # sumir junto: por isso a conferência abaixo, do que fica registrado.
    conferir(not fecha["exige_justificativa"],
             "a composição sozinha não exige mais texto escrito à mão",
             str(fecha))
    conferir(fecha["fora_do_escopo"] == {"REELS": 1},
             "dizendo o que veio fora do escopo", str(fecha["fora_do_escopo"]))
    conferir("REELS" in fecha["nota_automatica"],
             "e o programa registra a troca sozinho, citando o tipo",
             fecha["nota_automatica"])

    # 9b: composição muda mas a COTA FECHA (nada faltando). Este é o caso que
    # a régua antiga não conseguia expressar: fechava NÃO CONFORME mesmo sem
    # faltar nada, só por ter vindo algo a mais. Agora fecha CONFORME (apto a
    # pagamento) e MESMO ASSIM pede a justificativa da composição.
    fecha_composicao_pura = ee.fechar_ciclo(ee.ler_escopo("1 REELS"), contagem)
    conferir(fecha_composicao_pura["situacao"] == ee.CONFORME,
             "nada faltando: fecha CONFORME mesmo com STORIES fora do escopo",
             fecha_composicao_pura["situacao"])
    # MESMA REVISÃO DE 23/09/2026 da conferência acima: o ciclo fecha, o
    # registro da troca é escrito pelo programa, e a Observação à mão fica
    # reservada ao ciclo que não fechou.
    conferir(not fecha_composicao_pura["exige_justificativa"],
             "e não exige mais texto à mão pela composição sozinha",
             str(fecha_composicao_pura))
    conferir("fora do escopo" in fecha_composicao_pura["nota_automatica"],
             "com a troca registrada automaticamente no lugar",
             fecha_composicao_pura["nota_automatica"])
    conferir(fecha_composicao_pura["fora_do_escopo"] == {"STORIES": 2},
             "dizendo o que veio fora do escopo", str(fecha_composicao_pura["fora_do_escopo"]))

    print()
    print("--- 10. escopo não preenchido não fecha nada ---")
    for texto in (E_SEM_ESCOPO, E_INDEFINIDO):
        fecha = ee.fechar_ciclo(ee.ler_escopo(texto), contagem)
        conferir(fecha["situacao"] == ee.SEM_BASE,
                 f"{texto!r} fecha como SEM BASE PARA COMPARAR",
                 fecha["situacao"])
        conferir(not fecha["exige_justificativa"],
                 "e não pede justificativa de quem não tem o que justificar")
        conferir(any("não está preenchido" in m for m in fecha["motivos"]),
                 "dizendo que o problema é o cadastro, não a entrega")

    print()
    print("--- 11. peça ORGÂNICA é entrega SEPARADA ---")
    # Decisão do auditor: orgânico e link "são tipos de entrega diferentes
    # mesmo". E o escopo do @recifeordinario pede "10 publicações contendo
    # marcação da logo", que é entrega orgânica: então ela não pode ser
    # descartada, tem que aparecer.
    com_organico = entregas + [
        linha("@x", "5", "STORIES", 9, "09/09/2026", marcacao="ORGANICO")]
    contagem2 = ee.contar_entregas(com_organico, "@x", "5")
    conferir(contagem2["entregue"] == {"STORIES": 2, "REELS": 1},
             "o orgânico NÃO entra na contagem de link",
             str(contagem2["entregue"]))
    conferir(contagem2["entregue_organico"] == {"STORIES": 1},
             "ele é contado à parte", str(contagem2["entregue_organico"]))
    fecha = ee.fechar_ciclo(ee.ler_escopo("2 COMBOS DE STORIES + 1 REELS"), contagem2)
    conferir(any("ORGÂNICO" in i for i in fecha["conferir_a_mao"]),
             "e aparece na lista de conferência humana",
             str(fecha["conferir_a_mao"]))
    # O escopo que PEDE orgânico deixa isso visível.
    lido = ee.ler_escopo(E_ORGANICO_NO_ESCOPO)
    conferir(any("marcação da logo" in texto.lower() for _, texto in lido["nao_mensuraveis"]),
             "escopo que pede publicação com a logo entra na conferência",
             str(lido["nao_mensuraveis"]))

    print()
    print("--- 12. o ciclo separa, e o influenciador também ---")
    misturado = entregas + [linha("@x", "6", "STORIES", 1, "20/09/2026"),
                            linha("@outro", "5", "STORIES", 1, "01/09/2026")]
    conferir(ee.contar_entregas(misturado, "@x", "5")["entregue"]
             == {"STORIES": 2, "REELS": 1},
             "outro ciclo e outro influenciador não entram na conta",
             str(ee.contar_entregas(misturado, "@x", "5")["entregue"]))
    conferir(ee.contar_entregas(misturado, "@x", "Ciclo 5")["entregue"]
             == {"STORIES": 2, "REELS": 1},
             "e \"Ciclo 5\" é o mesmo que \"5\"")

    print()
    print("--- 12b. INCOMPLETO também diz o que veio FORA DO ESCOPO ---")
    # Achado ao rodar no dado real em 03/09/2026: o @jubrasil ciclo 2 tinha
    # entregado 2 de 20 stories E um reels fora do escopo. O ciclo fechava NÃO
    # CONFORME (hoje seria INCOMPLETO, ver seção 9) e o motivo falava só do
    # reels, então o aviso para o Financeiro sairia sem dizer que faltavam 18
    # stories. A correção original continua valendo: os dois motivos aparecem
    # juntos, independentemente de qual decide a situação.
    #
    # REVISADO EM 16/09/2026: a falta de quantidade virou TOTAL do ciclo, sem
    # citar tipo (só 1 stories + 1 reels + 1 feed = 3, contra 21 contratados,
    # falta 18 no total), e a queda de STORIES especificamente ganhou o
    # próprio motivo de atenção, independente do total.
    fecha = ee.fechar_ciclo(ee.ler_escopo("20 COMBOS DE STORIES + 1 FEED"),
                            ee.contar_entregas(
                                [linha("@j", "2", "STORIES", 1, "01/09/2026"),
                                 linha("@j", "2", "REELS", 1, "02/09/2026"),
                                 linha("@j", "2", "FEED", 1, "03/09/2026")],
                                "@j", "2"))
    conferir(fecha["situacao"] == ee.INCOMPLETO,
             "falta quantidade no total do ciclo: fecha INCOMPLETO",
             fecha["situacao"])
    conferir(fecha["exige_justificativa"],
             "e o REELS fora do escopo ainda exige a justificativa da composição")
    conferir(any("REELS" in m for m in fecha["motivos"]),
             "dizendo do tipo fora do escopo")
    conferir(any("Falta quantidade no total" in m for m in fecha["motivos"]),
             "dizendo que falta no total do ciclo", str(fecha["motivos"]))
    # "STORIES" E NÃO "Stories" DESDE 23/09/2026: a frase especial que existia
    # só para Stories foi absorvida pela mensagem única de tipos abaixo do
    # combinado, que escreve o nome do tipo como ele vem do dado. A queda
    # continua avisada e continua com número; o que saiu foi o texto separado.
    conferir(any("ATENÇÃO" in m and "STORIES" in m for m in fecha["motivos"]),
             "E avisando a queda em STORIES, com número", str(fecha["motivos"]))

    print()
    print("--- 12c. contrato que declara o TAMANHO do combo ---")
    # Real, do cadastro: "18 COMBOS STORIES COM 3 TELAS CADA + DIÁRIAS DE
    # GRAVAÇÃO". O programa conta por post, como o auditor definiu, e AVISA,
    # porque um combo publicado em dois dias apareceria como dois posts.
    lido = ee.ler_escopo("18 COMBOS STORIES COM 3 TELAS CADA + DIÁRIAS DE GRAVAÇÃO")
    conferir(lido["telas_por_combo"] == 3,
             "lê que o combo tem 3 telas", str(lido["telas_por_combo"]))
    conferir(lido["contratado"].get("STORIES") == 18,
             "e a quantidade continua sendo 18 combos", str(lido["contratado"]))
    fecha = ee.fechar_ciclo(lido, contagem)
    conferir(any("combo de 3 telas" in i for i in fecha["conferir_a_mao"]),
             "e o fechamento avisa, em vez de ignorar em silêncio",
             str(fecha["conferir_a_mao"]))
    conferir(ee.ler_escopo("12 COMBOS DE STORIES")["telas_por_combo"] is None,
             "contrato que não declara tamanho não inventa um")

    print()
    print("--- 13. PEÇA REPROVADA CONTINUA IDENTIFICADA, MAS JÁ NÃO TRAVA ---")
    # Até 16/09/2026 só peça CONFORME contava para a cota (decisão de
    # 31/08/2026). Revisto a pedido do auditor: "sempre haverá algum não
    # conforme que pode passar, ele só vai ser avisado para as próximas não
    # repetir". `entregue_conforme` continua existindo, separado de
    # `entregue`, só para dizer QUANTO passou limpo na régua, sem gate.
    duas_sendo_uma_reprovada = [
        linha("@k", "1", "STORIES", 1, "01/09/2026", validacao="CONFORME"),
        linha("@k", "1", "STORIES", 2, "02/09/2026",
              validacao="NÃO CONFORME (Falta aviso de publicidade)")]
    c = ee.contar_entregas(duas_sendo_uma_reprovada, "@k", "1")
    conferir(c["entregue"] == {"STORIES": 2},
             "o total entregue conta as duas", str(c["entregue"]))
    conferir(c["entregue_conforme"] == {"STORIES": 1},
             "e o total conforme continua separado, informativo",
             str(c["entregue_conforme"]))
    conferir(len(c["reprovadas"]) == 1, "e a reprovada fica identificada")

    print()
    print("--- 13b. PEÇA REPROVADA CONTA COMO ENTREGA, E VIRA AVISO ---")
    # REVISADO EM 16/09/2026: existia uma situação própria ("COTA FECHA, MAS
    # TEM PEÇA REPROVADA") que travava o ciclo em algo diferente de CONFORME.
    # Ela saiu: agora a peça reprovada conta pra cota igual a qualquer outra,
    # e vira só um aviso nos motivos, não mais um bloqueio.
    fecha = ee.fechar_ciclo(ee.ler_escopo("1 COMBOS DE STORIES"), c)
    conferir(fecha["situacao"] == ee.CONFORME,
             "fecha CONFORME mesmo com a peça reprovada dentro",
             fecha["situacao"])
    conferir(any("ATENÇÃO" in m and "não passaram na régua" in m
                 for m in fecha["motivos"]),
             "e o motivo avisa da peça reprovada, sem travar o fechamento",
             str(fecha["motivos"]))
    conferir(not fecha["exige_justificativa"],
             "peça reprovada sozinha não exige mais justificativa pra pagar",
             fecha)
    # E o caso de faltar análise é diferente de reprovar: a coluna de validação
    # vazia é como a linha nasce na planilha, antes de o lote rodar.
    sem_analise = [linha("@k", "1", "STORIES", 1, "01/09/2026", validacao="")]
    c2 = ee.contar_entregas(sem_analise, "@k", "1")
    fecha2 = ee.fechar_ciclo(ee.ler_escopo("1 COMBOS DE STORIES"), c2)
    conferir(fecha2["situacao"] == ee.COTA_ESPERANDO_ANALISE,
             "peça sem veredito tem situação própria também", fecha2["situacao"])
    # Com tudo conforme, fecha conforme.
    tudo_ok = [linha("@k", "1", "STORIES", 1, "01/09/2026")
               | {"validacao": "CONFORME"}]
    fecha3 = ee.fechar_ciclo(ee.ler_escopo("1 COMBOS DE STORIES"),
                             ee.contar_entregas(tudo_ok, "@k", "1"))
    conferir(fecha3["situacao"] == ee.CONFORME,
             "e com todas conformes fecha CONFORME", fecha3["situacao"])

    print()
    print("--- 14. exige_justificativa passou a cobrir TODA situação que não fechou ---")
    # ATÉ 09/09/2026 esta pergunta era outra: PAGAR sem a entrega ter fechado,
    # resolvida por uma função própria (pagamento_exige_justificativa) ligada
    # a um rádio "Este ciclo já foi pago?". O auditor redesenhou o fim da
    # tela para "Solicitar pagamento?": "o pagamento vem depois do ciclo
    # fechado... essa mensagem é para pagamento do ciclo". A régua migrou
    # pra dentro do próprio fechar_ciclo, então fecha["exige_justificativa"]
    # já responde "posso solicitar sem escrever nada?" na hora.
    #
    # REUSA fecha2/fecha3 da seção 13b (sem veredito e tudo conforme), que já
    # construíram cada situação de verdade. `fecha` (peça reprovada) já foi
    # conferido na própria seção 13b: não exige mais justificativa.
    conferir(fecha2["exige_justificativa"],
             "COTA_ESPERANDO_ANALISE (sem veredito) exige justificativa pra "
             "solicitar pagamento", fecha2)
    conferir(not fecha3["exige_justificativa"],
             "e CONFORME de verdade (nada fora do padrão) não exige nada")

    print()
    print("--- 15. TODA situação tem nome que cabe na tela ---")
    # DEFEITO VISTO PELO AUDITOR NA TELA em 03/09/2026: a situação estava num
    # indicador do Streamlit, que tem a largura da coluna, e aparecia como
    # "SEM BA..." e "NÃO C...". Ele lia o fechamento sem saber do que se tratava.
    # Estas conferências existem para que a sétima situação, criada amanhã, não
    # possa nascer sem nome curto e sem explicação.
    # OITO DESDE 16/09/2026: entrou CONFORME_COM_OBSERVACAO (o ciclo que só
    # fecha porque alguém declarou na tela que uma entrega que o programa não
    # mede existe) e saiu COTA_COM_PECA_REPROVADA (peça reprovada deixou de
    # travar o fechamento, virou só aviso). O número aqui é de propósito: é
    # ele que obriga a situação nova a passar pelas conferências de nome
    # curto, explicação e gravidade, logo abaixo.
    conferir(len(ee.SITUACOES_DE_CICLO) == 8,
             "as oito situações estão declaradas numa lista só",
             str(ee.SITUACOES_DE_CICLO))
    for situacao in ee.SITUACOES_DE_CICLO:
        ap = ee.apresentacao(situacao)
        conferir(situacao in ee.APRESENTACAO,
                 f"{situacao}: tem apresentação declarada")
        conferir(0 < len(ap["curto"]) <= 40,
                 f"{situacao}: o nome curto cabe ({len(ap['curto'])} caracteres)",
                 ap["curto"])
        conferir(len(ap["explicacao"]) > 30,
                 f"{situacao}: explica em uma frase o que aquilo significa",
                 ap["explicacao"])
        conferir(ap["gravidade"] in ("ok", "achado", "espera"),
                 f"{situacao}: a gravidade diz para onde o caso vai",
                 ap["gravidade"])
    # NENHUMA SITUAÇÃO É MAIS "achado" (16/09/2026). Era só
    # COTA_COM_PECA_REPROVADA, a última que ia direto para o auditor em vez
    # de seguir para o financeiro; com ela removida, todo ciclo que fecha em
    # quantidade segue "ok" ou "espera" (ainda sendo medido).
    conferir({s for s in ee.SITUACOES_DE_CICLO
              if ee.apresentacao(s)["gravidade"] == "achado"}
             == set(),
             "nenhuma situação de ciclo é mais achado")
    conferir(ee.apresentacao(ee.CONFORME)["gravidade"] == "ok",
             "e só o CONFORME segue para o financeiro")
    # Situação desconhecida não deixa a tela em branco justamente na hora ruim.
    conferir(ee.apresentacao("BANANA")["curto"] == "BANANA",
             "situação desconhecida devolve o próprio texto, e não vazio")

    print()
    print("--- 15b. a situação NÃO volta para o indicador estreito ---")
    pagina = os.path.join(BASE, "pages", "3_Financeiro.py")
    with open(pagina, encoding="utf-8") as f:
        fonte = f.read()
    codigo = "\n".join(l for l in fonte.splitlines()
                       if not l.strip().startswith("#"))
    conferir('metric("Situação' not in codigo
             and "metric('Situação" not in codigo,
             "a página não põe a situação num st.metric",
             "é o defeito que cortava o nome; a faixa de largura inteira cabe")
    conferir("ee.apresentacao(" in codigo,
             "e usa a apresentação vinda do motor, sem reescrever os nomes")

    print()
    print("--- 16. o registro não tem mais coluna de achado de pagamento ---")
    # ATÉ 09/09/2026, "pagar sem a entrega fechada" tinha nome de achado
    # próprio (ACHADO_PAGO_SEM_ENTREGA) e coluna própria no registro, pedida
    # pelo auditor em 03/09/2026 para poder ser contado depois. Isso saiu
    # junto com o rádio "já foi pago?": não existe mais uma declaração de
    # pagamento pra cruzar com a entrega, porque a tela só solicita DEPOIS de
    # o ciclo (ou a justificativa) já estar certo. O que sobrevive do
    # espírito original é a JUSTIFICATIVA em si, ainda obrigatória e ainda
    # gravada, só que numa coluna só (justificativa), sem o achado à parte.
    for nome in ("achado_de_pagamento", "ACHADO_PAGO_SEM_ENTREGA"):
        conferir(not hasattr(ee, nome), f"escopo_e_entrega não tem mais {nome}")
    # A ÂNCORA É O TRECHO DE CAMPOS_FECHAMENTO, NÃO O ARQUIVO INTEIRO: a
    # palavra "achado" também aparece, à toa, no dicionário de gravidade da
    # faixa do topo ({"achado": st.error, ...}), que não tem relação nenhuma
    # com a coluna removida.
    trecho_campos = codigo.split("CAMPOS_FECHAMENTO = (")[1].split(")")[0]
    conferir('"achado"' not in trecho_campos,
             "o registro do fechamento não grava mais a coluna achado",
             trecho_campos)
    conferir('"justificativa": justificativa' in codigo,
             "a justificativa continua sendo gravada, sem precisar de "
             "segunda coluna")

    print()
    print("--- 16b. a coluna nova não desalinha o registro antigo ---")
    # Se a lista de campos cresce e o programa só faz append, os valores novos
    # entram sob os títulos antigos e o registro passa a mentir em silêncio.
    import csv as _csv
    import tempfile
    antigos_titulos = ["quando", "quem", "influenciador", "pagamento"]
    with tempfile.TemporaryDirectory() as pasta:
        caminho = os.path.join(pasta, "fechamentos_ciclo.csv")
        with open(caminho, "w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=antigos_titulos)
            w.writeheader()
            w.writerow({"quando": "2026-09-02 10:00:00", "quem": "alguem",
                        "influenciador": "@antigo", "pagamento": "PAGO"})
        # Reproduz o que a página faz, sem abrir o Streamlit.
        campos = ("quando", "quem", "influenciador", "pagamento", "achado")
        with open(caminho, encoding="utf-8", newline="") as f:
            antigos = list(_csv.DictReader(f))
        titulos = tuple(antigos[0].keys()) if antigos else ()
        if titulos and titulos != campos:
            with open(caminho, "w", newline="", encoding="utf-8") as f:
                w = _csv.DictWriter(f, fieldnames=campos)
                w.writeheader()
                for antigo in antigos:
                    w.writerow({c: antigo.get(c, "") or "" for c in campos})
        with open(caminho, encoding="utf-8", newline="") as f:
            depois = list(_csv.DictReader(f))
        conferir(tuple(depois[0].keys()) == campos,
                 "o arquivo antigo é reescrito com os títulos novos",
                 str(tuple(depois[0].keys())))
        conferir(depois[0]["influenciador"] == "@antigo"
                 and depois[0]["pagamento"] == "PAGO",
                 "sem perder o que já estava gravado")
        conferir(depois[0]["achado"] == "",
                 "e a coluna nova fica vazia no registro antigo, não chutada")


if __name__ == "__main__":
    print("=" * 74)
    print("  Escopo contratado contra entrega, por ciclo")
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
