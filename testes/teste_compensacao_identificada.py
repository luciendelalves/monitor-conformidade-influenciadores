# -*- coding: utf-8 -*-
"""
O programa diz QUEM cobriu QUEM, e não só que "parece" ter sido compensado.

POR QUE ESTE TESTE EXISTE (23/09/2026)

Até esta data o fechamento comparava dois totais e escrevia "entregas parecem
compensadas". Quem lia a tela tinha que descobrir sozinho, na tabela, o que
tinha coberto o quê. O auditor pediu o cálculo de verdade: "se for compensada,
o programa identificar o que foi compensado em relação ao escopo, e não apenas
confiar nos números de que parece que algo foi compensado".

E PEDIU OS DOIS LADOS: as entregas que passam pela plataforma e as que não
passam, estas últimas confirmadas na caixa de marcar (diária de gravação, por
exemplo).

AS TRÊS REGRAS QUE MUDARAM JUNTO, no mesmo pedido:

1. ciclo compensado ou batendo exato NÃO pede mais Observação escrita à mão.
   Ela volta a ser obrigatória só quando a entrega é divergente E MENOR.
2. no lugar dela, o programa escreve sozinho a coluna NOTA do histórico
   ("Ciclo completo", "Ciclo completo, compensado (...)"), para o registro
   continuar existindo sem depender de alguém digitar.
3. o aviso de divergência com o Calendário saiu da tela do Financeiro: o
   Calendário é organizacional das analistas, e seis linhas de "sem linha no
   Calendário" num ciclo normal eram ruído, não achado.

O QUE ESTE TESTE GUARDA, e é o que custa caro se voltar: a atribuição
("os 2 reels cobriram os 2 stories") é uma DIVISÃO, não um fato do dado. Ela
precisa ser sempre a mesma para o mesmo fechamento, senão um registro de
auditoria muda de texto sozinho entre duas leituras.

Não fala com planilha nenhuma.

    py testes\\teste_compensacao_identificada.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import escopo_e_entrega as ee

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def fechar(texto_escopo, entregue, organico=None, declaracoes=None,
           declaracoes_nm=None):
    contagem = {"entregue": dict(entregue), "entregue_organico": dict(organico or {}),
                "reprovadas": [], "sem_veredito": [], "sem_evidencia": [],
                "limite_da_automacao": [], "posts": []}
    return ee.fechar_ciclo(ee.ler_escopo(texto_escopo), contagem,
                           declaracoes=declaracoes,
                           declaracoes_nao_mensuravel=declaracoes_nm)


def rodar():
    print("--- 1. a divisão em si, sem depender do resto do motor ---")
    r = ee.explicar_compensacao([{"o_que": "STORIES", "quanto": 2}],
                                [{"o_que": "REELS", "quanto": 2}])
    conferir(len(r) == 1 and r[0]["coberto"] == 2, "uma falta, uma sobra, cobertura total", str(r))
    conferir(r[0]["por"] == [{"o_que": "REELS", "quanto": 2, "origem": "", "rotulo": ""}],
             "e diz de onde veio a cobertura", str(r[0]["por"]))

    r = ee.explicar_compensacao([{"o_que": "STORIES", "quanto": 5}],
                                [{"o_que": "REELS", "quanto": 2}])
    conferir(r[0]["coberto"] == 2 and r[0]["quanto"] == 5,
             "sobra menor que a falta cobre só em parte, e isso fica visível",
             str(r))

    # A falta é maior que a maior sobra, senão a segunda sobra nem é tocada.
    r = ee.explicar_compensacao([{"o_que": "STORIES", "quanto": 6}],
                                [{"o_que": "REELS", "quanto": 1},
                                 {"o_que": "FEED", "quanto": 5}])
    conferir([p["o_que"] for p in r[0]["por"]] == ["FEED", "REELS"],
             "com duas sobras, a maior entra primeiro, sempre na mesma ordem",
             str(r[0]["por"]))
    de_novo = ee.explicar_compensacao([{"o_que": "STORIES", "quanto": 6}],
                                      [{"o_que": "REELS", "quanto": 1},
                                       {"o_que": "FEED", "quanto": 5}])
    conferir(de_novo == r,
             "e o mesmo fechamento sai escrito igual na segunda vez",
             "texto de registro de auditoria não pode mudar sozinho")

    conferir(ee.explicar_compensacao([], [{"o_que": "REELS", "quanto": 9}]) == [],
             "sobra sem falta nenhuma não inventa compensação")

    print()
    print("--- 2. o caso que o auditor mostrou na tela ---")
    # 6 COMBOS DE STORIES + 4 REELS; entregou 4 stories e 6 reels.
    f = fechar("6 COMBOS DE STORIES + 4 REELS", {"STORIES": 4, "REELS": 6})
    conferir(f["situacao"] == ee.CONFORME, "o ciclo fecha", f["situacao"])
    conferir(any("2 STORIES coberto(s) por 2 REELS" in m for m in f["motivos"]),
             "e o motivo diz o que cobriu o quê, com número",
             str(f["motivos"]))
    conferir(not any("parecem compensadas" in m for m in f["motivos"]),
             "a frase antiga, que não dizia o quê, saiu")
    conferir(f["exige_justificativa"] is False,
             "compensado não pede mais Observação escrita à mão")
    conferir(f["nota_automatica"].startswith("Ciclo completo (entrega compensada:")
             and "2 STORIES" in f["nota_automatica"],
             "e a NOTA do histórico sai escrita pelo programa, na redação pedida",
             f["nota_automatica"])

    print()
    print("--- 3. bateu exato: sem Observação, mas com registro ---")
    f = fechar("6 COMBOS DE STORIES + 4 REELS", {"STORIES": 6, "REELS": 4})
    conferir(f["exige_justificativa"] is False, "não pede Observação")
    # A REDAÇÃO É A DO AUDITOR, palavra por palavra (23/09/2026).
    conferir(f["nota_automatica"] == "Ciclo completo.",
             "e mesmo assim entra no histórico dizendo o que houve",
             f["nota_automatica"])
    conferir(f["compensacao"] == [], "sem compensação nenhuma para explicar")

    print()
    print("--- 4. divergente E MENOR: aí sim pede Observação ---")
    f = fechar("6 COMBOS DE STORIES + 4 REELS", {"STORIES": 4, "REELS": 4})
    conferir(f["situacao"] == ee.INCOMPLETO, "o ciclo não fecha", f["situacao"])
    conferir(f["exige_justificativa"] is True,
             "e a Observação volta a ser obrigatória")
    conferir(f["nota_automatica"] == "",
             "sem nota automática: aqui o texto tem que ser de gente",
             f["nota_automatica"])
    conferir(any("2 a menos" in m for m in f["motivos"]),
             "e o motivo diz quanto faltou", str(f["motivos"]))

    print()
    print("--- 5. os dois lados: o que passa pela plataforma e o que não passa ---")
    # A diária NÃO foi confirmada, e sobrou story: a falta de fora da
    # plataforma é coberta igual a qualquer outra.
    f = fechar("4 COMBOS DE STORIES + 1 DIARIA DE GRAVACAO", {"STORIES": 6})
    conferir(any("DIARIA" in m and "coberto" in m for m in f["motivos"]),
             "item de fora da plataforma não confirmado entra como falta coberta",
             str(f["motivos"]))
    conferir(not any("1 1 DIARIA" in m for m in f["motivos"]),
             "e o número não sai repetido, porque o texto do contrato já o traz",
             str(f["motivos"]))

    # Confirmada na caixa de marcar: ela cobre a própria linha e some da conta.
    f = fechar("4 COMBOS DE STORIES + 1 DIARIA DE GRAVACAO", {"STORIES": 4},
               declaracoes_nm={"1 DIARIA DE GRAVACAO": 1})
    conferir(f["compensacao"] == [],
             "confirmada, ela não aparece como falta nem como sobra",
             str(f["compensacao"]))
    conferir(f["exige_justificativa"] is False, "e o ciclo não pede Observação")

    print()
    print("--- 5b. o EXCEDENTE de fora da plataforma pode cobrir outro tipo ---")
    # PEDIDO DO AUDITOR NO MESMO DIA: "se a compensação for de alguma entrega
    # externa, estamos preparados para isso?". Não estava: o teto travava a
    # declaração na própria linha do contrato, e não sobrava nunca. Agora
    # sobra, com uma condição que não existe nas outras compensações: exige
    # Observação, porque aqui a única evidência é a palavra de quem declarou.
    f = fechar("6 COMBOS DE STORIES + 1 DIARIA DE GRAVACAO", {"STORIES": 4},
               declaracoes_nm={"1 DIARIA DE GRAVACAO": 3})
    conferir(f["situacao"] == ee.CONFORME_COM_OBSERVACAO,
             "o excedente (2) cobre os 2 stories que faltavam", f["situacao"])
    conferir(f["exige_justificativa"] is True,
             "e AQUI a Observação é obrigatória, diferente das outras compensações",
             "sem arquivo pra conferir depois, só a palavra de quem declarou")
    conferir(any("STORIES" in m and "DIARIA" in m and "coberto" in m for m in f["motivos"]),
             "o motivo diz que o excedente da diária cobriu os stories",
             str(f["motivos"]))

    # Declarar excedente que NÃO é usado não pede nada: só exceder não basta.
    f = fechar("6 COMBOS DE STORIES + 1 DIARIA DE GRAVACAO", {"STORIES": 6},
               declaracoes_nm={"1 DIARIA DE GRAVACAO": 3})
    conferir(f["exige_justificativa"] is False,
             "excedente declarado mas não usado não pede Observação",
             "o ciclo já fechava sem precisar dele")

    # Sem exceder, continua como antes de hoje: cobre só a própria linha.
    f = fechar("6 COMBOS DE STORIES + 1 DIARIA DE GRAVACAO", {"STORIES": 4},
               declaracoes_nm={"1 DIARIA DE GRAVACAO": 1})
    conferir(f["situacao"] == ee.INCOMPLETO,
             "dentro do contratado (sem exceder), continua sem cobrir story",
             f["situacao"])

    print()
    print("--- 6. peça orgânica também compensa, e o texto diz que foi ela ---")
    f = fechar("6 COMBOS DE STORIES", {"STORIES": 4}, organico={"STORIES": 2})
    conferir(any("orgânico" in m for m in f["motivos"]),
             "a origem orgânica aparece no motivo", str(f["motivos"]))

    print()
    print("--- 7. tipo FORA DO ESCOPO: registrado, mas sem Observação à mão ---")
    # ESTA EXCEÇÃO CAIU NO MESMO DIA (23/09/2026). Ela tinha sido mantida na
    # primeira versão, com a ressalva de que entregar formato nunca contratado
    # é pergunta sobre COMPOSIÇÃO e não sobre volume. O auditor foi consultado
    # com essa ressalva na mão e mandou tirar também.
    #
    # O QUE NÃO PODE SE PERDER, e é o que este teste guarda: a composição
    # trocada continua REGISTRADA, agora pelo programa, citando o tipo pelo
    # nome. Sem essa segunda conferência, tirar a justificativa teria apagado
    # o rastro da flexibilização, que é o oposto do que a ferramenta existe
    # para fazer.
    f = fechar("6 COMBOS DE STORIES", {"STORIES": 4, "TIKTOK": 2})
    conferir(f["situacao"] == ee.CONFORME, "o total fecha", f["situacao"])
    conferir(f["exige_justificativa"] is False,
             "não pede mais Observação escrita à mão")
    conferir("fora do escopo" in f["nota_automatica"]
             and "TIKTOK" in f["nota_automatica"],
             "mas a nota automática registra a composição trocada, com o tipo",
             f["nota_automatica"])
    conferir(any("não está no escopo" in m and "TIKTOK" in m for m in f["motivos"]),
             "e o motivo na tela continua dizendo isso também",
             str(f["motivos"]))

    print()
    print("--- 7b. a Observação tem DUAS condições, e as duas têm motivo ---")
    # Depois das duas quedas de 23/09 (tipo abaixo do combinado e tipo fora do
    # escopo), sobrava só "o ciclo não fechou". NO MESMO DIA entrou uma
    # segunda condição, ver a seção 5b: excedente de entrega fora da
    # plataforma cobrindo falta de outro tipo, porque ali a única evidência é
    # a palavra de quem declarou, sem arquivo pra conferir depois. Se alguém
    # acrescentar uma TERCEIRA condição sem o auditor pedir, é este teste que
    # reprova.
    fonte = open(os.path.join(BASE, "escopo_e_entrega.py"), encoding="utf-8").read()
    conferir('"exige_justificativa": (situacao in ENTREGA_NAO_FECHOU\n'
             '                                or _veio_de_declaracao_externa),' in fonte,
             "a condição é a situação do ciclo OU o excedente declarado ter sido usado",
             "compensado por tipo medido ou por composição trocada continuam sem pedir nada")

    print()
    print("--- 8. sem escopo legível, as chaves novas existem e vêm vazias ---")
    f = fechar("", {"STORIES": 3})
    conferir(f["compensacao"] == [] and f["nota_automatica"] == "",
             "senão quem lê o fechamento quebraria justo quando falta cadastro",
             f"{f['compensacao']} / {f['nota_automatica']}")

    print()
    print("--- 9. o aviso de divergência com o Calendário saiu da tela ---")
    tela = open(os.path.join(BASE, "pages", "3_Financeiro.py"), encoding="utf-8").read()
    codigo = [l for l in tela.splitlines()
              if l.strip() and not l.strip().startswith("#")]
    conferir(not any("_divergencias" in l for l in codigo),
             "a lista de divergências saiu do código da tela")
    conferir(not any("baixado aqui divergem" in l for l in codigo),
             "e o aviso em destaque também")
    conferir(any("Cronograma pro WhatsApp" in l for l in codigo),
             "mas o cronograma pro WhatsApp continua, que foi o pedido")
    conferir(any("nota_automatica" in l for l in codigo),
             "e a tela usa a nota automática ao registrar no histórico")

    print()
    print("--- 12. entrega fora da plataforma virou campo de quantidade ---")
    # PEDIDO DO AUDITOR (23/09/2026): "se a compensação for de alguma entrega
    # externa, estamos preparados para isso?". O check só confirmava a
    # própria linha; sem um número pra digitar, nunca haveria excedente pra
    # sobrar. Ver a seção 5b em escopo_e_entrega.
    conferir(any("nm_qtd_" in l for l in codigo),
             "o campo é de número (nm_qtd_), não mais de marcar (nm_check_)")
    conferir(not any("nm_check_" in l for l in codigo),
             "a chave do checkbox antigo saiu por completo")
    conferir(any('"confirmado" if digitado else' in l for l in codigo),
             "e a leitura decide pelo número digitado, não por um booleano")

    print()
    print("--- 10. a caixa de Observação some da tela quando o ciclo fechou ---")
    # ACHADO PELO AUDITOR NA TELA (23/09/2026), no caso da diária confirmada:
    # tudo verde, ciclo apto a pagamento, e a caixa de texto continuava lá,
    # grande e vazia, escrito "(opcional)". Caixa em branco no meio da tela
    # pede para ser preenchida mesmo dizendo que não precisa.
    #
    # FICOU ATRÁS DE UM EXPANSOR, e não apagada: quem quiser registrar algo
    # sobre um ciclo que fechou continua podendo. O registro em si não depende
    # mais dela (ver a nota automática, seções acima).
    conferir(any('if _nota_obrigatoria:' in l for l in codigo),
             "a tela separa os dois casos antes de desenhar o campo")
    conferir(not any("Escrever uma observação" in l for l in codigo),
             "o expansor da tentativa anterior também saiu",
             "o auditor pediu campo NENHUM quando o ciclo fecha")
    conferir(not any('"Observação (opcional)"' in l for l in codigo),
             "e o rótulo antigo, que deixava a caixa sempre à vista, também")
    conferir(any("Vai ser registrado assim" in l for l in codigo),
             "no lugar do campo, a tela MOSTRA o que vai ser gravado")
    conferir(any('nota_automatica' in l and 'Ciclo completo' in l for l in codigo),
             "e o texto vem do motor, não é remontado na tela",
             "tela e registro dizendo coisas diferentes quebra o histórico")

    print()
    print("--- 11. a explicação da compensação APARECE, e não em vermelho ---")
    # DEFEITO DE ALGUMAS HORAS, em 23/09/2026: a caixa que mostra os motivos
    # estava dentro de `if exige_justificativa`. Quando a justificativa deixou
    # de ser exigida em ciclo compensado, a explicação de quem cobriu quem
    # passou a ser calculada e nunca desenhada. O auditor viu na tela e
    # perguntou se a compensação ainda estava sendo implementada; estava
    # pronta, era a caixa que não aparecia.
    #
    # E A COR IMPORTA: ciclo apto a pagamento pintado de vermelho diz o
    # contrário do que o fechamento concluiu.
    trecho = tela.split("_motivos = [m for m in")[1][:900]
    conferir("if fechamento[\"exige_justificativa\"]:" not in
             tela.split("_motivos = [m for m in")[0][-400:],
             "a lista de motivos não está mais atrás da justificativa",
             "senão ciclo compensado calcula a explicação e não mostra")
    conferir("st.error(_texto_motivos)" in trecho and "st.info(_texto_motivos)" in trecho,
             "vermelho quando não fechou, azul quando fechou por compensação",
             trecho[:200])


if __name__ == "__main__":
    print("=" * 74)
    print("  Compensação identificada, e a Observação só quando falta de verdade")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
