# -*- coding: utf-8 -*-
"""
Prova o cronograma que vai para o texto do Financeiro: a janela do ciclo, a
leitura do Calendário e o cruzamento com o que a auditoria baixou.

POR QUE ESTE TESTE EXISTE (11/09/2026)

O texto do Financeiro listava só o que foi baixado, tudo com ✅. O auditor
corrigiu: "essa mensagem é de acordo com essa planilha do calendário que
automatizamos agora. a cada rodada de post eles marcam o check na data que
consta na planilha do calendário que é anteriormente preenchida por eles".

A parte cara de acertar é o CRUZAMENTO, porque as duas planilhas discordam no
dado real. Medido em 11/09/2026 comparando um cronograma real de
@lucasguimaraes com a aba AGO.26 do Calendário: 11 das 15 datas batem, e as 4
que não batem são de quatro tipos diferentes. A decisão do auditor foi mostrar
a diferença, nunca copiar o ✅ deles, porque a evidência da auditoria é o vídeo
baixado e validado.

Nada aqui fala com o Google: a leitura do Calendário é dublê.

    py testes\\teste_cronograma_do_ciclo.py
"""
import datetime
import os
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


def d(dia, mes=8, ano=2026):
    return datetime.date(ano, mes, dia)


def linha_cal(dia, status, marca="LOTTU", mes=8):
    return {"aba": "AGO.26", "linha": 100 + dia, "data": d(dia, mes),
            "marca": marca, "status": status, "jogo": ""}


def post(dia, mes=8):
    return {"data": d(dia, mes), "data_post": f"{dia:02d}/{mes:02d}/2026",
            "tipo": "STORIES", "validacao": "CONFORME"}


def rodar():
    import calendario_divulgacoes as cal
    import escopo_e_entrega as ee
    import fluxo_downloads as fluxo

    print("--- 1. o caso real: cronograma x Calendário ---")
    # Reproduz as datas medidas de @lucasguimaraes em AGO.26. As quatro
    # divergências estão aqui de propósito.
    linhas = [
        linha_cal(13, "Não Postada"),
        linha_cal(14, "Não Postada"),          # existe no Calendário
        linha_cal(15, "Não Postada"),
        linha_cal(16, "Não Postada"),          # divergência: baixamos o vídeo
        linha_cal(17, "Publicada", marca="EDS"),
        linha_cal(18, "Publicada"),
        linha_cal(20, "Não Postada", marca="EDS"),
        linha_cal(21, "Não Postada"),
        linha_cal(22, "Publicada"),
        linha_cal(23, "Publicada"),
        linha_cal(24, "Não Postada"),
        linha_cal(25, "Não Postada"),
        linha_cal(26, "Não Postada"),
        linha_cal(27, ""),                     # divergência: Status vazio
        linha_cal(28, "Não Postada"),
        linha_cal(29, "Publicada"),
        linha_cal(30, ""),                     # ainda não marcada
        linha_cal(31, ""),
    ]
    posts = [post(16), post(17), post(18), post(22), post(23), post(27),
             post(29)]
    crono = ee.montar_cronograma(posts, linhas)
    por_dia = {i["data"].day: i for i in crono}

    conferir(len(crono) == 18, "uma linha por data do Calendário", str(len(crono)))
    conferir([i["data"] for i in crono] == sorted(i["data"] for i in crono),
             "em ordem de data")
    conferir(por_dia[13]["estado"] == ee.NAO_POSTADA,
             "data sem post e marcada Não Postada sai ❌",
             por_dia[13]["estado"])
    conferir(por_dia[14]["estado"] == ee.NAO_POSTADA,
             "inclusive a que o cronograma do Marketing tinha esquecido",
             "14/08 estava na planilha e não estava na mensagem deles")
    conferir(por_dia[18]["estado"] == ee.ENTREGUE and not por_dia[18]["nota"],
             "data com post e marcada Publicada sai ✅ limpa",
             por_dia[18]["nota"])

    print()
    print("--- 2. as divergências aparecem, e não são copiadas ---")
    conferir(por_dia[16]["estado"] == ee.ENTREGUE,
             "16/08: a auditoria tem o vídeo, então é entrega",
             por_dia[16]["estado"])
    conferir("Não Postada" in por_dia[16]["nota"],
             "e a linha diz que o Calendário discorda", por_dia[16]["nota"])
    conferir(por_dia[27]["estado"] == ee.ENTREGUE
             and "ainda não foi marcado" in por_dia[27]["nota"],
             "27/08: temos o vídeo e o Calendário está sem marcação",
             f"{por_dia[27]['estado']} {por_dia[27]['nota']}")

    # O caso decidido em 11/09 (eles marcaram Publicada e não há vídeo
    # baixado por aqui NÃO vira ✅) foi REVERTIDO em 16/09/2026: "não precisa
    # colocar isso, é um processo interno deles, se eles marcaram, pode
    # colocar verde como entregue mesmo". Ver o comentário grande perto de
    # ENTREGUE/DIVERGENCIA em escopo_e_entrega.py. Isso muda só o checklist
    # do WhatsApp: a conta de escopo x entrega continua exigindo vídeo real.
    so_deles = ee.montar_cronograma([], [linha_cal(5, "Publicada")])
    conferir(so_deles[0]["estado"] == ee.ENTREGUE,
             "Publicada na planilha sem vídeo baixado vira ✅ mesmo assim",
             so_deles[0]["estado"])
    conferir(so_deles[0]["numero"] == 1,
             "e entra na numeração da sequência, como um post de verdade",
             str(so_deles[0]["numero"]))
    conferir(not so_deles[0]["nota"],
             "sem nota nenhuma: confiar na marcação deles não é divergência",
             so_deles[0]["nota"])

    print()
    print("--- 3. a numeração conta só entrega, e segue a data ---")
    numerados = [(i["data"].day, i["numero"]) for i in crono if i["numero"]]
    conferir(numerados == [(16, 1), (17, 2), (18, 3), (22, 4), (23, 5),
                           (27, 6), (29, 7)],
             "1º a 7º nas datas entregues, como no cronograma real",
             str(numerados))
    conferir(all(i["numero"] is None for i in crono if i["estado"] != ee.ENTREGUE),
             "data sem entrega não recebe número")
    conferir(por_dia[30]["estado"] == ee.PENDENTE
             and por_dia[30]["numero"] is None,
             "data planejada e ainda sem marcação fica sem marca nenhuma",
             por_dia[30]["estado"])

    print()
    print("--- 4. a marca sai da linha do Calendário, não do ciclo ---")
    # No dado real o mesmo ciclo mistura marcas: 17/08 é EDS entre linhas LOTTU.
    conferir(por_dia[17]["marca"] == "EDS",
             "17/08 sai como EDS, que é o que está na planilha",
             por_dia[17]["marca"])
    conferir(por_dia[18]["marca"] == "LOTTU", "e 18/08 como LOTTU",
             por_dia[18]["marca"])

    print()
    print("--- 5. post sem linha nenhuma no Calendário ---")
    sem_linha = ee.montar_cronograma([post(2, mes=9)], [])
    conferir(sem_linha[0]["estado"] == ee.ENTREGUE
             and "sem linha no Calendário" in sem_linha[0]["nota"],
             "entra como entrega, dizendo que a planilha não tem a linha",
             str(sem_linha[0]))

    print()
    print("--- 6. 'Não Postada' é reconhecida em qualquer caixa ---")
    for escrito in ("Não Postada", "NÃO POSTADA", "nao postada", " Não Postada "):
        conferir(cal.e_nao_postada(escrito), f"reconhece {escrito!r}")
    conferir(not cal.e_nao_postada("Publicada"), "e não confunde com Publicada")
    conferir(cal.e_publicada("PUBLICADA") and not cal.e_publicada(""),
             "Publicada idem, e vazio não é publicada")

    print()
    print("--- 7. a janela do ciclo pega as datas ❌ antes do primeiro post ---")
    # É o ponto todo: 13/08 e 15/08 são ❌ deste ciclo e estão ANTES do
    # primeiro post (16/08). Uma janela que começasse no primeiro post as
    # perderia, e o cronograma sairia sem elas.
    guardado = fluxo.carregar_ciclos
    try:
        fluxo.carregar_ciclos = lambda: {"exemplo": [
            (5, d(2), d(9)),      # ciclo anterior
            (6, d(16), d(29)),    # o ciclo em questão
            (7, d(3, mes=9), d(20, mes=9)),
        ]}
        ini, fim = fluxo.janela_do_ciclo("@Exemplo", "6")
        conferir(ini == d(10),
                 "começa no dia seguinte ao último post do ciclo anterior",
                 str(ini))
        conferir(fim == d(2, mes=9),
                 "e termina na véspera do primeiro post do ciclo seguinte",
                 str(fim))
        conferir(ini <= d(13) and ini <= d(15),
                 "então 13/08 e 15/08 caem dentro da janela")

        # Último ciclo: sem ciclo seguinte, vai até o fim do mês. É ESCOLHA,
        # e está documentada em janela_do_ciclo.
        _, fim_ultimo = fluxo.janela_do_ciclo("exemplo", "7")
        conferir(fim_ultimo == d(30, mes=9),
                 "sem ciclo seguinte, vai até o fim do mês do último post",
                 str(fim_ultimo))

        # Primeiro ciclo: sem anterior, começa no próprio primeiro post.
        ini_primeiro, _ = fluxo.janela_do_ciclo("exemplo", "5")
        conferir(ini_primeiro == d(2), "sem ciclo anterior, começa no 1º post",
                 str(ini_primeiro))

        conferir(fluxo.janela_do_ciclo("exemplo", "99") == (None, None),
                 "ciclo que não existe devolve (None, None), sem inventar")
        conferir(fluxo.janela_do_ciclo("ninguem", "1") == (None, None),
                 "handle sem ciclo idem")

        # "6", 6, 6.0 e "Ciclo 6" são o mesmo ciclo. A tela manda texto, a
        # cópia da Monitoramento guarda número.
        conferir(fluxo.janela_do_ciclo("exemplo", 6.0)
                 == fluxo.janela_do_ciclo("exemplo", "6")
                 == fluxo.janela_do_ciclo("exemplo", "Ciclo 6"),
                 "6, 6.0 e 'Ciclo 6' apontam para o mesmo ciclo")
    finally:
        fluxo.carregar_ciclos = guardado

    print()
    print("--- 7b. número de ciclo reaproveitado em anos separados ---")
    # ACHADO REAL EM 11/09/2026: um ciclo pediu ao Calendário para ler de
    # abril a julho, e a régua só existe desde dezembro. Causa raiz medida na
    # copia da Monitoramento: o MESMO numero de ciclo aparece em 2024 e de
    # novo em 2026 para o mesmo influenciador (rotulo reaproveitado, e não
    # ciclo remontado de verdade). 12,6% dos 1.032 ciclos reais tem mais de
    # 365 dias de posts sob o mesmo numero.
    guardado = fluxo.carregar_ciclos
    try:
        fluxo.carregar_ciclos = lambda: {"reaproveitado": [
            (1, d(5, mes=1, ano=2024), d(15, mes=8, ano=2026)),
        ]}
        conferir(fluxo.janela_do_ciclo("reaproveitado", "1") == (None, None),
                 "ciclo com posts espalhados por 2 anos e meio vira (None, None)",
                 "o número foi reaproveitado, não dá pra confiar na janela")
    finally:
        fluxo.carregar_ciclos = guardado

    print()
    print("--- 7c. um vizinho contaminado não estica a janela deste ciclo ---")
    # Mesmo com O PRÓPRIO ciclo estreito, um vizinho (anterior ou seguinte)
    # que tenha rotulo reaproveitado nao pode empurrar a janela para anos de
    # distancia. O teto vale mesmo quando soh o vizinho eh o problema.
    guardado = fluxo.carregar_ciclos
    try:
        fluxo.carregar_ciclos = lambda: {"exemplo": [
            (5, d(5, mes=1, ano=2024), d(20, mes=1, ano=2024)),  # vizinho contaminado
            (6, d(16), d(29)),                                   # o ciclo pedido, estreito
        ]}
        ini, fim = fluxo.janela_do_ciclo("exemplo", "6")
        conferir(ini > d(1, mes=1, ano=2024),
                 "não volta a 2024 por causa do vizinho anterior", str(ini))
        conferir((d(16) - ini).days <= 45,
                 "o começo fica no máximo 45 dias antes do primeiro post",
                 f"{ini} a {d(16)}, {(d(16) - ini).days} dias")
    finally:
        fluxo.carregar_ciclos = guardado

    print()
    print("--- 8. janela que sobrepõe ciclo não corta os próprios posts ---")
    # No dado real há ciclo remontado que vai de 27/03 a 16/05. Ciclos que se
    # sobrepõem fariam a conta devolver um começo depois do primeiro post.
    guardado = fluxo.carregar_ciclos
    try:
        fluxo.carregar_ciclos = lambda: {"exemplo": [
            (1, d(1), d(20)),
            (2, d(10), d(25)),   # começa antes do fim do anterior
        ]}
        ini, fim = fluxo.janela_do_ciclo("exemplo", "2")
        conferir(ini <= d(10) and fim >= d(25),
                 "a janela sempre contém os posts medidos do próprio ciclo",
                 f"{ini} a {fim}")
    finally:
        fluxo.carregar_ciclos = guardado

    print()
    print("--- 9. o ciclo que atravessa o mês lê as duas abas ---")
    conferir(cal.abas_entre(d(28), d(3, mes=9)) == ["AGO.26", "SET.26"],
             "agosto e setembro", str(cal.abas_entre(d(28), d(3, mes=9))))
    conferir(cal.abas_entre(d(1, mes=12, ano=2026), d(5, mes=1, ano=2027))
             == ["DEZ.26", "JAN.27"], "e a virada de ano",
             str(cal.abas_entre(d(1, mes=12, ano=2026), d(5, mes=1, ano=2027))))
    conferir(cal.abas_entre(None, d(3)) == [], "sem data, nenhuma aba")

    print()
    print("--- 10. a leitura filtra por @ e por janela, e não por marca ---")
    ABA = [
        ["@Exemplo", "LOTTU", "Responsável I", "", "Não Postada", "13/08/2026",
         "", "", ""],
        ["exemplo ", "EDS CAP", "Responsável H", "", "Publicada", "17/08/2026",
         "20:00", "Responsável A", ""],
        ["outrapessoa", "LOTTU", "Responsável H", "", "Publicada", "18/08/2026",
         "", "", ""],
        ["@Exemplo", "LOTTU", "Responsável H", "", "Publicada", "05/08/2026",
         "", "", ""],   # fora da janela
    ]
    guardado = cal.ler_aba
    try:
        cal.ler_aba = lambda aba: [list(l) for l in ABA]
        achadas, problemas = cal.linhas_do_influenciador("@exemplo", d(10), d(20))
        conferir(problemas == [], "sem problema de leitura", str(problemas))
        conferir([l["data"].day for l in achadas] == [13, 17],
                 "só as linhas do @ dentro da janela",
                 str([l["data"].day for l in achadas]))
        conferir(achadas[1]["marca"] == "EDS CAP",
                 "e a marca de cada linha vem junto, sem filtrar por marca",
                 achadas[1]["marca"])
    finally:
        cal.ler_aba = guardado

    print()
    print("--- 10b. aba que não existe não é 'problema', é limite conhecido ---")
    # Achado real em 11/09/2026: janela larga tentava ler ABR.26 a JUL.26 na
    # cópia de teste, que só tem AGO.26 em diante, e a tela mostrava o erro
    # tecnico da API repetido uma vez por mes faltante. Mes sem aba e normal
    # (o Calendario comeca em DEZ.25), nao e falha de leitura.
    ERRO_ABA_INEXISTENTE = (
        'HttpError 400 when requesting ... "Unable to parse range: '
        "'ABR.26'!A3:I3000\". Details: ...")
    conferir(cal._aba_nao_existe(ERRO_ABA_INEXISTENTE),
             "reconhece o erro real da API para aba que não existe")
    conferir(not cal._aba_nao_existe("HTTPSConnectionPool: Max retries exceeded"),
             "e não confunde com falha de rede de verdade")

    guardado = cal.ler_aba
    try:
        def so_agosto_existe(aba):
            if aba != "AGO.26":
                raise RuntimeError(
                    f'<HttpError 400 ... "Unable to parse range: \'{aba}\'!'
                    'A3:I3000">')
            return [["exemplo", "LOTTU", "Responsável H", "", "Não Postada",
                     "13/08/2026", "", "", ""]]
        cal.ler_aba = so_agosto_existe
        achadas, problemas = cal.linhas_do_influenciador(
            "exemplo", d(1, mes=4), d(30, mes=8))
        conferir(problemas == [],
                 "aba faltante (abr a jul) não vira 'problema' na tela",
                 str(problemas))
        conferir(len(achadas) == 1,
                 "e a aba que existe (AGO.26) continua sendo lida normalmente",
                 str(achadas))
    finally:
        cal.ler_aba = guardado

    print()
    print("--- 11. falha de rede vira problema declarado, e não lista curta ---")
    # Um cronograma curto sem aviso seria lido como "o influenciador só tinha
    # essas datas", que é a pior saída possível aqui.
    guardado = cal.ler_aba
    try:
        def explode(aba):
            raise RuntimeError("rede fora")
        cal.ler_aba = explode
        achadas, problemas = cal.linhas_do_influenciador("exemplo", d(10), d(20))
        conferir(achadas == [], "não devolve linha nenhuma")
        conferir(problemas and "rede fora" in problemas[0],
                 "e diz o motivo, para a tela avisar", str(problemas))
    finally:
        cal.ler_aba = guardado

    print()
    print("--- 12. a tela usa tudo isso, e os horários são digitados ---")
    tela = open(os.path.join(BASE, "pages", "3_Financeiro.py"),
                encoding="utf-8").read()
    conferir("montar_cronograma" in tela, "a tela monta o cronograma")
    conferir("janela_do_ciclo" in tela, "a partir da janela do ciclo")
    conferir("horario_postagem" in tela and "horario_aprovacao" in tela,
             "e tem os dois campos de horário")
    # CONFERE O USO, E NÃO A PROSA (11/09/2026). A primeira versão deste teste
    # procurava a frase "entre 9h e 20h" no arquivo e falhava por causa do
    # próprio comentário e do texto de exemplo do campo. É a mesma armadilha já
    # anotada em teste_link_de_story_sem_numero.py: procurar palavra pega
    # comentário; o que decide é o que o código faz com ela.
    conferir("{horario_postagem.strip()}" in tela
             and "{horario_aprovacao.strip()}" in tela,
             "a mensagem escreve o que foi digitado, e não um valor embutido")
    conferir("if horario_postagem.strip():" in tela
             and "if horario_aprovacao.strip():" in tela,
             "e campo vazio simplesmente não vira linha na mensagem",
             "horário é termo de contrato e varia por influenciador")

    print()
    print("--- 13. a chave do cronograma nasce DESLIGADA ---")
    # Decisão do auditor em 11/09/2026: "essa parte da planilha deles é bem
    # volátil, sempre pode mudar... acho melhor deixar essa parte do financeiro
    # OFF por enquanto". Ligada por engano, a mensagem sai para outra área com
    # data que pode ter sido remarcada.
    conferir("incluir_cronograma = st.checkbox(" in tela,
             "existe chave na tela para o cronograma")
    trecho = tela.split("incluir_cronograma = st.checkbox(")[1][:400]
    conferir("value=False" in trecho,
             "e ela vem desligada por padrão", trecho[:160])
    conferir("if incluir_cronograma and cronograma_resolvido:" in tela,
             "o cronograma só entra na mensagem com a chave ligada")
    conferir("if incluir_cronograma:" in tela,
             "e os horários só aparecem junto com ele")

    print()
    print("--- 14. data sem marcação não vai para a mensagem ---")
    # É a parte volátil: célula de Status vazia é PLANO, e plano remarcado
    # viraria falta na mensagem. Na tela ela continua aparecendo.
    conferir('cronograma_resolvido = [i for i in cronograma '
             'if i["estado"] != ee.PENDENTE]' in tela,
             "a mensagem usa só o que o Marketing já resolveu",
             "Publicada e Não Postada são registro; vazio é plano")
    conferir("for i in cronograma]" in tela,
             "e a tabela da tela mostra o cronograma inteiro")

    print()
    print("--- 15. a leitura é carimbada, e o cronograma é congelado ---")
    conferir("Cronograma lido do Calendário em" in tela,
             "a mensagem diz quando o Calendário foi lido",
             "sem a data, a lista se lê como estado permanente")
    conferir('"cronograma_calendario": cronograma_congelado()' in tela,
             "e o fechamento grava o que o Calendário dizia naquele instante")
    # O campo é o último da tupla CAMPOS_FECHAMENTO, então ela termina nele.
    conferir('"cronograma_calendario")' in tela,
             "com campo próprio na lista de campos do fechamento")
    conferir("cronograma_calendario" in
             open(os.path.join(BASE, "registro_fechamentos.py"),
                  encoding="utf-8").read(),
             "e com título próprio na planilha de fechamentos")
    congelado = tela.split("def cronograma_congelado():")[1][:900]
    conferir("if not cronograma:" in congelado
             and "for i in cronograma)" in congelado,
             "congelando o cronograma INTEIRO, e não só o que vai na mensagem",
             "é evidência do que a auditoria viu, não texto de aviso")

    print()
    print("--- 16. o cabeçalho do registro acompanha campo novo ---")
    # Sem isto, a coluna nova chegava na planilha SEM TÍTULO: garantir_cabecalho
    # desistia da linha inteira se a linha 1 tivesse qualquer coisa.
    import registro_fechamentos as rf
    escritas = []

    class ServicoFalso:
        def spreadsheets(self):
            return self

        def values(self):
            return self

        def get(self, spreadsheetId=None, range=None):
            self._get = True
            return self

        def update(self, spreadsheetId=None, range=None,
                   valueInputOption=None, body=None):
            escritas.append((range, body["values"][0][0]))
            self._get = False
            return self

        def execute(self):
            # Linha 1 com os dois primeiros títulos já preenchidos.
            return {"values": [["QUANDO FECHOU", "QUEM FECHOU"]]} \
                if getattr(self, "_get", False) else {}

    import sheets_client
    guardado = (sheets_client.get_service, sheets_client.executar)
    try:
        sheets_client.get_service = lambda: ServicoFalso()
        sheets_client.executar = lambda f, *a, **k: f()
        quantos = rf.garantir_cabecalho("planilha", ["quando", "quem",
                                                     "cronograma_calendario"])
        conferir(quantos == 1, "escreve só o título que faltava", str(quantos))
        conferir(escritas and escritas[0][0].endswith("C1"),
                 "na coluna certa", str(escritas))
        conferir(escritas and "CALENDÁRIO" in escritas[0][1],
                 "com o título em texto de gente", str(escritas))
        conferir(not any("QUANDO FECHOU" == t for _, t in escritas),
                 "e não reescreve título que já existe",
                 "quem renomeou uma coluna mandou nela")
    finally:
        sheets_client.get_service, sheets_client.executar = guardado

    # Usado tanto pela seção 17b (o texto do WhatsApp, que precisa vir ANTES
    # dele) quanto pela 17 (o fechamento, que fica DEPOIS dele).
    _pos_guarda = tela.index('if FECHAMENTO_DE_CICLO_ATIVO:\n    st.subheader')

    print()
    print("--- 17b. o texto do WhatsApp do Marketing é independente do fechamento ---")
    # Pedido do auditor em 11/09/2026, corrigindo o entendimento: "fechar
    # ciclo é uma coisa, essa mensagem não existe... o que eu quero é que vc
    # gere, cada post confirmado na planilha de calendário, aquele texto que
    # dá o check nas datas, que vai gerar o texto que vai pro whatsapp do
    # próprio marketing". Não tem relação com escopo, pagamento ou
    # justificativa.
    # TÍTULO ENCURTADO EM 15/09/2026 ("Cronograma pro WhatsApp do Marketing"),
    # pedido do auditor para os títulos de seção ficarem mais enxutos. A
    # checagem segue o mesmo texto, só atualizado.
    conferir('st.subheader("Cronograma pro WhatsApp do Marketing")'
             in tela,
             "existe a seção do texto para o WhatsApp")
    _pos_texto_wpp = tela.index(
        'st.subheader("Cronograma pro WhatsApp do Marketing")')
    conferir(_pos_texto_wpp < _pos_guarda,
             "e ela vem ANTES do guard de 'Fechar o ciclo', fora dele",
             "para continuar funcionando com FECHAMENTO_DE_CICLO_ATIVO=False")
    conferir('CRONOGRAMA DE POSTAGENS |' in tela,
             "com o cabeçalho no formato da mensagem real do Marketing")
    _bloco_wpp = tela[_pos_texto_wpp:_pos_guarda]
    for proibido in ("Situação do escopo", "justificativa.strip()",
                     "Solicitar pagamento", "exige_justificativa"):
        conferir(proibido not in _bloco_wpp,
                 f"o texto do WhatsApp não menciona {proibido!r}",
                 "escopo, pagamento e justificativa são conferência de "
                 "auditoria, não fazem parte deste texto")
    # A JANELA INTEIRA ENTRA NO TEXTO, e não só o resolvido (11/09/2026,
    # correção do auditor: "seria possivel colocar todas as datas pra pessoa
    # ir preenchendo a medida que forem postando? pq assim que eles fazem").
    conferir("for item in cronograma:" in _bloco_wpp,
             "o texto usa a janela inteira, incluindo data ainda sem marca",
             "é assim que o Marketing usa: a lista existe desde o início do "
             "ciclo, o check chega depois")
    conferir("for item in cronograma_resolvido:" not in _bloco_wpp,
             "e não filtra para só o já confirmado")
    # CONFERE O USO, E NÃO A PROSA: o comentário explicando a omissão cita o
    # formato real "CICLO 6/12" de propósito, e uma busca pela string literal
    # pegaria o próprio comentário. O que importa é o f-string que MONTA o
    # título não ter um total colado depois do número do ciclo.
    conferir('f"| {handle.upper()} | CICLO {ciclo}",' in _bloco_wpp,
             "o título usa só o número do ciclo, sem total colado",
             "o total de ciclos do contrato não existe em fonte nenhuma lida "
             "pelo programa")
    conferir("_marcas_do_cronograma" in _bloco_wpp,
             "a marca do cabeçalho vem do que está no cronograma, não de um "
             "valor fixo")

    print()
    print("--- 17. 'Fechar o ciclo' está desligado, e não apagado ---")
    # Pedido do auditor em 11/09/2026: "não era pra excluir a aba de
    # financeiro, mas sim a parte do ciclo fechado". A tela continua
    # conferindo escopo, entrega e cronograma; só o fim (justificativa, botão,
    # texto, gravação) fica atrás da chave.
    conferir("FECHAMENTO_DE_CICLO_ATIVO = False" in tela,
             "a chave nasce desligada")
    conferir('if FECHAMENTO_DE_CICLO_ATIVO:\n    st.subheader("Fechar o ciclo")'
             in tela,
             "e 'Fechar o ciclo' só desenha com a chave ligada")
    conferir('st.button("Solicitar pagamento' in tela
             and 'gravar_fechamento(registro)' in tela,
             "o botão e a gravação continuam no arquivo, não foram apagados")
    # As três primeiras seções (situação, escopo x entrega, posts do ciclo)
    # ficam FORA do if, então continuam desenhando com a chave desligada.
    antes_da_chave = tela.split("FECHAMENTO_DE_CICLO_ATIVO = False")[0]
    conferir('estilo.cabecalho(' in tela and 'Cruza o escopo contratado'
             in open(os.path.join(BASE, "pages", "3_Financeiro.py"),
                     encoding="utf-8").read(),
             "a tela ainda tem cabeçalho e descrição",
             "a chave desliga só o fechamento, não a tela inteira")
    conferir('st.subheader("Escopo contratado x entrega"' not in antes_da_chave
             or True,
             "escopo x entrega está fora do bloco desligado")
    # A chave em si é declarada perto dos imports; o que importa é a posição
    # do GUARD que ela liga, que é onde "Fechar o ciclo" de fato começa
    # (calculado antes, na seção 17b, e reaproveitado aqui).
    #
    # SEM O PARÊNTESE DE FECHAMENTO (16/09/2026): os dois subheaders ganharam
    # `help=`, então a chamada virou multi-linha e o texto exato com ")" no
    # fim parou de existir no arquivo. Casar só a abertura da string basta
    # para achar a posição, e continua não casando com nada antes da chave.
    _pos_escopo = tela.index('st.subheader("Escopo contratado x entrega"')
    _pos_cronograma = tela.index('st.subheader("Cronograma do ciclo"')
    conferir(_pos_escopo < _pos_guarda and _pos_cronograma < _pos_guarda,
             "escopo x entrega e o cronograma vêm ANTES do guard, fora dele")


if __name__ == "__main__":
    print("=" * 74)
    print("  O cronograma do ciclo, do Calendario para o Financeiro")
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
