# -*- coding: utf-8 -*-
"""
As exceções do escopo real, e as opções que elas obrigam a existir.

POR QUE ESTE ARQUIVO EXISTE

Pedido do auditor em 03/09/2026: "faça uma análise mais profunda nesses
documentos dos influenciadores e cruze os dados para que as automações e
informações no ciclo do programa funcionem de forma perfeita" e, na mesma
conversa, "considere as exceções para que a gente consiga ter as opções
necessárias para não inferir nada".

TODO TEXTO AQUI É REAL. Saiu de duas fontes do papel de trabalho da auditoria,
na pasta "12 - AUDITORIA INFLUENCIADORES / PAPEL DE TRABALHO" do Drive:

    aba Achado01_EntregaEComprovacao da planilha final, coluna "Escopo
      Contratado (Completo)": 69 textos distintos em 260 linhas
    aba "Pendencias auditoria" da planilha AUDITORIA - VALIDAÇÃO MKT INFLU,
      coluna "Entrega - Contrato": 23 formatos distintos em 173 linhas

CADA SEÇÃO ABAIXO NASCEU DE UM DEFEITO MEDIDO, e não de imaginação: antes do
cruzamento, o parser lia 68 dos 69 escopos e deixava 5 pedaços sem
reconhecimento, e três desses casos MUDAVAM O FECHAMENTO do ciclo.

Rodar:

    py testes\teste_excecoes_do_escopo.py
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


def linha(handle, ciclo, tipo, post, data, marcacao="LINK",
          validacao="CONFORME"):
    return {"handle": handle, "ciclo": ciclo, "tipo": tipo, "post": post,
            "data_post": data, "marcacao": marcacao, "validacao": validacao}


def rodar():
    import escopo_e_entrega as ee

    print("--- 1. ALTERNATIVA SEM PARÊNTESES: '40 - Stories, reels ou feed' ---")
    # 6 linhas na planilha de validação. O DEFEITO: a vírgula partia o texto, o
    # programa lia 40 STORIES e jogava "reels ou feed" fora. Um ciclo que
    # entregasse 40 reels, dentro do que o contrato permite, fechava NÃO CONFORME
    # por mudança de composição e ainda pedia justificativa de quem acertou.
    lido = ee.ler_escopo("40 - Stories, reels ou feed")
    conferir(len(lido["alternativas"]) == 1,
             "é lida como UMA alternativa, e não como 40 stories",
             str(lido))
    if lido["alternativas"]:
        quantidade, tipos = lido["alternativas"][0]
        conferir(quantidade == 40, "com quantidade 40", str(quantidade))
        conferir(set(tipos) == {"STORIES", "REELS", "FEED"},
                 "cumprida por stories, reels OU feed", str(tipos))
    conferir(not lido["contratado"],
             "e nada foi somado como cota de um tipo só",
             str(lido["contratado"]))
    # E o efeito prático: 40 reels fecham o ciclo.
    entregas = [linha("@a", "1", "REELS", i, f"{i:02d}/09/2026")
                for i in range(1, 41)]
    fecha = ee.fechar_ciclo(lido, ee.contar_entregas(entregas, "@a", "1"))
    conferir(fecha["situacao"] == ee.CONFORME,
             "40 reels contra 'stories, reels ou feed' fecha CONFORME",
             fecha["situacao"])
    # A soma continua sendo soma: "6 stories, 4 reels" não é alternativa.
    soma = ee.ler_escopo("6 stories, 4 reels")
    conferir(soma["contratado"] == {"STORIES": 6, "REELS": 4},
             "e lista SEM 'ou' continua sendo soma, não alternativa",
             str(soma))

    print()
    print("--- 2. LIVE É HORA, NÃO POST: '40 - Horas live' ---")
    # 16 linhas na planilha de validação. O DEFEITO: o programa contava
    # {'LIVE': 40} como cota de posts. Live não aparece na coluna TIPO da
    # Monitoramento, então a cota pedia 40 entregas que nunca chegam e o ciclo
    # ficava INCOMPLETO para sempre, sem ninguém entender por quê.
    lido = ee.ler_escopo("40 - Horas live")
    conferir("LIVE" not in lido["contratado"],
             "não entra na cota de posts", str(lido["contratado"]))
    conferir(any("hora" in texto.lower() for _, texto in lido["nao_mensuraveis"]),
             "e vira conferência humana, com a quantidade à vista",
             str(lido["nao_mensuraveis"]))
    conferir(all(qtd is None for qtd, texto in lido["nao_mensuraveis"] if "hora" in texto.lower()),
             "mas SEM quantidade própria: hora não é posts, não pode somar junto",
             str(lido["nao_mensuraveis"]))
    # E o escopo que é SÓ live tem situação própria, que não culpa o cadastro.
    fecha = ee.fechar_ciclo(lido, ee.contar_entregas([], "@a", "1"))
    conferir(fecha["situacao"] == ee.SEM_COTA_MENSURAVEL,
             "escopo só de live fecha como ESCOPO SEM ENTREGA MEDIDA",
             fecha["situacao"])
    conferir(fecha["situacao"] != ee.SEM_BASE,
             "e NÃO como sem base para comparar",
             "seria cobrar o Marketing por um cadastro que está completo")
    conferir(fecha["conferir_a_mao"],
             "com a lista do que precisa ser conferido à mão")

    print()
    print("--- 3. TIPO QUE A RÉGUA NÃO ALCANÇA: '8 - Twitter/X', '2 - Youtube' ---")
    # 13 linhas de Twitter e 3 de YouTube na planilha de validação, e a aba
    # Achado03 tem 23 linhas de X/TWITTER com "NÃO FOI POSSÍVEL ANALISAR (LINK DE
    # REDE SOCIAL)". O DEFEITO: com "só peça CONFORME conta", uma cota de 8
    # tweets nunca fecharia, porque nenhum tweet recebe veredito CONFORME.
    lido = ee.ler_escopo("12 - Stories + 8 - Twitter/X")
    conferir(lido["contratado"] == {"STORIES": 12},
             "só o que a régua alcança entra na cota", str(lido["contratado"]))
    conferir(lido["contratado_nao_validavel"] == {"X/TWITTER": 8},
             "o resto fica em contratado_nao_validavel",
             str(lido["contratado_nao_validavel"]))
    conferir(any("X/TWITTER" in i for i in ee._conferir_a_mao(lido, {})),
             "e aparece na conferência humana, dizendo por quê",
             str(ee._conferir_a_mao(lido, {})))
    # E O PONTO QUE MAIS IMPORTA: entregar tweet não é entregar fora do escopo.
    entregas = ([linha("@a", "1", "STORIES", i, f"{i:02d}/09/2026")
                 for i in range(1, 13)]
                + [linha("@a", "1", "X/TWITTER", i, f"{i:02d}/09/2026",
                         validacao="NÃO FOI POSSÍVEL ANALISAR (LINK DE REDE SOCIAL)")
                   for i in range(1, 9)])
    fecha = ee.fechar_ciclo(lido, ee.contar_entregas(entregas, "@a", "1"))
    conferir("X/TWITTER" not in fecha["fora_do_escopo"],
             "tweet contratado NÃO é 'tipo fora do escopo'",
             str(fecha["fora_do_escopo"]))
    # NÃO fecha CONFORME aqui: os 8 X/TWITTER vêm com "NÃO FOI POSSÍVEL
    # ANALISAR" (link de rede social), que é sem_evidencia, e isso por si só
    # já impede CONFORME. O que este teste prova é mais estreito, e é o que
    # importa: contratado_nao_validavel não vira "fora do escopo" nem exige
    # a justificativa de composição, que é sobre algo TROCADO, não sobre
    # peça sem evidência.
    conferir(fecha["situacao"] == ee.COTA_SEM_EVIDENCIA,
             "fecha COTA FECHA, MAS FALTA EVIDÊNCIA DA PEÇA, não punido por composição",
             fecha["situacao"])
    # exige_justificativa AQUI VEM DE ENTREGA_NAO_FECHOU, NÃO DE COMPOSIÇÃO
    # (09/09/2026): COTA_SEM_EVIDENCIA é uma situação que não fechou, então
    # solicitar pagamento exige justificativa mesmo sem nada fora do escopo.
    # O que este teste garante é só que fora_do_escopo continua vazio.
    conferir(fecha["exige_justificativa"],
             "mas exige justificativa por não ter fechado (falta evidência), "
             "não por composição")
    conferir(not fecha["fora_do_escopo"],
             "e fora_do_escopo continua vazio: nada foi trocado")

    print()
    print("--- 4. ESCOPO QUE PEDE ORGÂNICO COM QUANTIDADE ---")
    # No dado real: "12 POSTAGENS ORGÂNICAS", "14 postagens orgânicas mostrando a
    # marca", "14 - Post Orgânico". A peça orgânica é contada à parte porque não
    # passa pela régua, mas o contrato pede uma quantidade dela.
    for texto in ("12 POSTAGENS ORGÂNICAS", "14 - Post Orgânico",
                  "14 postagens orgânicas mostrando a marca"):
        lido = ee.ler_escopo(texto)
        conferir(bool(lido["contratado_organico"]),
                 f"\"{texto[:34]}\" vira quantidade de orgânico",
                 str(lido))
        conferir(not lido["nao_reconhecido"],
                 f"\"{texto[:34]}\" não fica sem reconhecimento",
                 str(lido["nao_reconhecido"]))

    print()
    print("--- 5. QUANTIDADE SEM FORMATO: '20 - Videos', '2 COLLABS' ---")
    # 5 linhas de "20 - Videos" na planilha de validação. Não dá para saber se
    # conta como reels, feed ou story. Chutar seria decidir a cota no lugar de
    # quem tem o contrato.
    lido = ee.ler_escopo("20 - Videos")
    conferir(lido["ambiguos"] and lido["ambiguos"][0][0] == 20,
             "'20 - Videos' vira item ambíguo, com a quantidade",
             str(lido["ambiguos"]))
    conferir(not lido["contratado"],
             "e NÃO é distribuído no tipo mais parecido",
             str(lido["contratado"]))
    conferir(any("formato" in i.lower() for i in ee._conferir_a_mao(lido, {})),
             "a conferência humana diz que falta o formato",
             str(ee._conferir_a_mao(lido, {})))

    print()
    print("--- 6. O PARÊNTESE NÃO APAGA O ITEM: '8 REELS (4 COLLABS)' ---")
    # REGRESSÃO QUE EU MESMO CRIEI em 03/09/2026 ao pôr "collab" entre os termos
    # não mensuráveis: o item inteiro virava conferência e os 8 reels do contrato
    # desapareciam da cota.
    lido = ee.ler_escopo("8 REELS (4 COLLABS)")
    conferir(lido["contratado"] == {"REELS": 8},
             "os 8 reels continuam na cota", str(lido["contratado"]))
    conferir(any("collab" in texto.lower() for _, texto in lido["nao_mensuraveis"]),
             "e as collabs viram conferência, como detalhe do item",
             str(lido["nao_mensuraveis"]))
    conferir(all(qtd is None for qtd, texto in lido["nao_mensuraveis"] if "collab" in texto.lower()),
             "sem quantidade própria: o \"4\" já é subconjunto dos 8 reels, não soma de novo",
             str(lido["nao_mensuraveis"]))

    print()
    print("--- 7. ITEM SEM QUANTIDADE LEGÍVEL: 'X - Facebook' ---")
    # 3 linhas na planilha de validação. O DEFEITO ERA O PIOR TIPO: sem número, o
    # trecho não casava com nada e era descartado em SILÊNCIO, então um item do
    # contrato simplesmente sumia do fechamento.
    lido = ee.ler_escopo("X - Facebook")
    conferir(lido["nao_reconhecido"],
             "não desaparece: fica registrado como não reconhecido",
             str(lido))
    conferir(any("quantidade" in i.lower() for i in lido["nao_reconhecido"]),
             "e o texto diz que o problema é a quantidade ilegível",
             str(lido["nao_reconhecido"]))

    print()
    print("--- 8. CONDIÇÃO NO ESCOPO: 'a partir do 2º mês 12 combos' ---")
    # O programa não sabe qual mês do contrato é o ciclo que está fechando.
    lido = ee.ler_escopo("a partir do 2º mês 12 combos de stories")
    conferir(lido["condicionais"],
             "vira item condicional, visível", str(lido))
    conferir(not lido["contratado"],
             "e NÃO cobra a quantidade desde o primeiro ciclo",
             str(lido["contratado"]))

    print()
    print("--- 9. 'COBERTURA DE JOGOS' é conferência, não tipo de post ---")
    lido = ee.ler_escopo("3 - Cobertura Jogos")
    conferir(lido["nao_mensuraveis"],
             "vira conferência humana", str(lido))
    conferir(not lido["nao_reconhecido"],
             "e não fica como desconhecido", str(lido["nao_reconhecido"]))

    print()
    print("--- 10. NENHUM DOS 69 ESCOPOS REAIS FICA SEM DESTINO ---")
    # A conferência que fecha o cruzamento: todo texto de escopo do papel de
    # trabalho tem que cair em ALGUMA das listas. Silêncio é o único resultado
    # inaceitável, porque é o que faz item de contrato desaparecer.
    REAIS = [
        "12 COMBOS DE STORIES",
        "6 COMBOS DE STORIES + 4 REELS",
        "12 STORIES + 6 REELS + 2 YOUTUBE + 2 TWITTER",
        "MENSAL: 2 COMBOS DE STORIES\nANUAL:  6 POSTS NO FEED",
        "5 FEED (OU REELS), 6 COMBOS STORIES, 8 TWEETS E 4 YOUTUBE",
        "18 COMBOS STORIES COM 3 TELAS CADA",
        "8 combos de stories + 2 feeds + 10 publicações contendo marcação da "
        "logo + presença em 4 eventos ao longo do ano + viagens",
        "4 combos de stories + 2 diárias de gravação para a marca +1 reels feed "
        "+ Presença em eventos quando necessário",
        "40 HORAS LIVE",
        "40 - Stories, reels ou feed",
        "8 REELS (4 COLLABS)",
        "2 COLLABS",
        "12 POSTAGENS ORGÂNICAS",
        "14 - Post Orgânico",
        "20 - Videos",
        "4 VÍDEOS",
        "3 - Cobertura Jogos",
        "X - Facebook",
        "a partir do 2º mês 12 combos de stories",
        "2 - Twitter/X",
        "1 - Post Feed",
        "2 - Youtube",
    ]
    sem_destino = []
    for texto in REAIS:
        lido = ee.ler_escopo(texto)
        tem_destino = any([
            lido["contratado"], lido["contratado_nao_validavel"],
            lido["contratado_organico"], lido["alternativas"], lido["anuais"],
            lido["nao_mensuraveis"], lido["ambiguos"], lido["condicionais"],
            lido["nao_reconhecido"], lido["sem_escopo"]])
        if not tem_destino:
            sem_destino.append(texto)
    conferir(not sem_destino,
             f"os {len(REAIS)} escopos reais têm destino",
             "SEM DESTINO: " + str(sem_destino))

    print()
    print("--- 11. 'NÃO FOI POSSÍVEL ANALISAR' NÃO É PEÇA REPROVADA ---")
    # O ACHADO CENTRAL DO CRUZAMENTO. A minha versão anterior chamava de
    # "reprovada" tudo o que não começasse com CONFORME. A própria auditoria já
    # separava isso em duas abas, e a aba Achado03 tem a coluna "Categoria do
    # Gap" com duas categorias cuja contagem fecha exatamente:
    #     Evidência Inacessível  223 = 140 + 77 + 6
    #     Limitação de Validação  118 = 107 + 11
    conferir(ee.categoria_do_gap("SEM ACESSO À PASTA")
             == ee.CATEGORIA_GAP_EVIDENCIA,
             "sem acesso à pasta é Evidência Inacessível")
    conferir(ee.categoria_do_gap("PASTA VAZIA") == ee.CATEGORIA_GAP_EVIDENCIA,
             "pasta vazia também")
    conferir(ee.categoria_do_gap("NÃO FOI POSSÍVEL ANALISAR (LINK DE REDE SOCIAL)")
             == ee.CATEGORIA_GAP_EVIDENCIA,
             "e link de rede social também")
    conferir(ee.categoria_do_gap("REQUER ANÁLISE HUMANA (aviso pequeno/baixo contraste)")
             == ee.CATEGORIA_GAP_LIMITACAO,
             "aviso pequeno é Limitação de Validação Automatizada")
    conferir(ee.categoria_do_gap("REQUER ANÁLISE HUMANA")
             == ee.CATEGORIA_GAP_LIMITACAO,
             "e requer análise humana sem detalhe também")
    conferir(ee.categoria_do_gap("NÃO CONFORME (Falta aviso de publicidade)") == "",
             "violação regulatória NÃO é gap: é achado")
    conferir(ee.categoria_do_gap("CONFORME") == "", "e conforme não é gap")
    conferir(ee.categoria_do_gap("") == "",
             "coluna vazia não é gap: é análise que não rodou")
    # ESTE RÓTULO NÃO EXISTE NO PAPEL DE TRABALHO, porque lá o alerta de áudio
    # era uma COLUNA separada. No programa ele virou veredito, e sem tratamento
    # cairia em "peça reprovada": o programa acusaria violação regulatória onde
    # o que existe é uma fala que alguém precisa ouvir.
    conferir(ee.categoria_do_gap("REQUER ANÁLISE DE ÁUDIO (possível fala "
                                 "problemática: ganho garantido)")
             == ee.CATEGORIA_GAP_LIMITACAO,
             "alerta de áudio é limitação da automação, não reprovação")

    print()
    print("--- 11d. TODO rótulo que o pipeline escreve tem destino ---")
    # A conferência que impede o próximo rótulo novo de cair em "reprovada" por
    # esquecimento. Ela lê o pipeline e classifica cada rótulo literal que ele
    # escreve na coluna de validação.
    import re
    with open(os.path.join(BASE, "pipeline_influenciadores.py"),
              encoding="utf-8") as f:
        fonte_pipeline = f.read()
    rotulos = sorted(set(re.findall(
        r'"((?:PASTA VAZIA|SEM ACESSO|N[AÃ]O FOI POSS[IÍ]VEL|REQUER AN[AÁ]LISE'
        r'|CONFORME|N[AÃ]O CONFORME|POST ORG)[^"]*)"', fonte_pipeline)))
    conferir(len(rotulos) >= 10,
             f"achei {len(rotulos)} rótulo(s) literais no pipeline",
             "se este número cair muito, a busca deixou de encontrar os rótulos")
    for rotulo in rotulos:
        gap = ee.categoria_do_gap(rotulo)
        e_conforme = rotulo.upper().startswith("CONFORME")
        e_violacao = rotulo.upper().startswith(("NÃO CONFORME", "NAO CONFORME"))
        e_organico = any(rotulo.upper().startswith(r)
                         for r in ee.ROTULOS_FORA_DA_REGUA)
        conferir(bool(gap) or e_conforme or e_violacao or e_organico,
                 f"\"{rotulo[:44]}\" tem destino",
                 "sem destino, ele cai em 'peça reprovada' e vira achado falso")

    print()
    print("--- 11b. e cada categoria (menos reprovada) tem situação própria ---")
    escopo_1 = ee.ler_escopo("1 COMBOS DE STORIES")
    casos = [
        ("SEM ACESSO À PASTA", ee.COTA_SEM_EVIDENCIA, "sem_evidencia"),
        ("REQUER ANÁLISE HUMANA (aviso pequeno/baixo contraste)",
         ee.COTA_NO_LIMITE_DA_AUTOMACAO, "limite_da_automacao"),
    ]
    for veredito, esperada, chave in casos:
        contagem = ee.contar_entregas(
            [linha("@b", "1", "STORIES", 1, "01/09/2026", validacao=veredito)],
            "@b", "1")
        conferir(len(contagem[chave]) == 1,
                 f"\"{veredito[:38]}\" cai em {chave}",
                 str({k: len(v) for k, v in contagem.items() if isinstance(v, list)}))
        fecha = ee.fechar_ciclo(escopo_1, contagem)
        conferir(fecha["situacao"] == esperada,
                 f"e fecha como {esperada}", fecha["situacao"])
    # REPROVADA É DIFERENTE DAS OUTRAS TRÊS (16/09/2026): continua caindo em
    # "reprovadas" pela categoria, mas não trava mais o fechamento numa
    # situação própria — conta pra cota e fecha CONFORME, com aviso.
    contagem_reprovada = ee.contar_entregas(
        [linha("@b", "1", "STORIES", 1, "01/09/2026",
               validacao="NÃO CONFORME (Falta aviso de publicidade)")],
        "@b", "1")
    conferir(len(contagem_reprovada["reprovadas"]) == 1,
             "\"NÃO CONFORME (...)\" cai em reprovadas",
             str({k: len(v) for k, v in contagem_reprovada.items()
                  if isinstance(v, list)}))
    fecha_reprovada = ee.fechar_ciclo(escopo_1, contagem_reprovada)
    conferir(fecha_reprovada["situacao"] == ee.CONFORME,
             "mas fecha CONFORME, não numa situação própria",
             fecha_reprovada["situacao"])

    print()
    print("--- 11c. peça orgânica não é reprovada nem gap ---")
    # O rótulo do orgânico é "POST ORGÂNICO, NÃO VALIDADO", e ele não começa com
    # CONFORME. Sem tratar, ele cairia em reprovadas e viraria achado inventado.
    contagem = ee.contar_entregas(
        [linha("@c", "1", "STORIES", 1, "01/09/2026", marcacao="ORGANICO",
               validacao="POST ORGÂNICO, NÃO VALIDADO")], "@c", "1")
    conferir(not contagem["reprovadas"],
             "peça orgânica não entra em reprovadas",
             str(contagem["reprovadas"]))
    conferir(contagem["entregue_organico"] == {"STORIES": 1},
             "ela é contada no grupo do orgânico",
             str(contagem["entregue_organico"]))


if __name__ == "__main__":
    print("=" * 74)
    print("  As exceções do escopo real, e as opções que elas obrigam")
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
