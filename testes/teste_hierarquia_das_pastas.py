# -*- coding: utf-8 -*-
"""
Prova a hierarquia nova das pastas, e que o ciclo saiu do Drive.

A ESTRUTURA, informada pelo auditor em 01/09/2026 e conferida no Drive deles:

    bet / ano / mês / @influenciador / DD/MM / {orgânico|link} / <tipo>
    arquivo: "@influenciador - tela N"

A MARCAÇÃO SUBIU PARA CIMA DO TIPO EM 03/09/2026, e eram outras três antes: a
primeira versão daquele dia tinha "publi" como categoria própria, e o auditor
corrigiu no mesmo dia ("Publi e Link são a mesma coisa, pq a publi contem o LINK
com a marca"). Ver o comentário de PASTA_ORGANICO em fluxo_downloads.

OS NOMES DE PASTA DE TIPO SÃO MEDIDOS, NÃO ESCOLHIDOS

Varredura só de leitura no Drive do Marketing em 01/09/2026, restrita aos
influenciadores com STATUS ATIVO na Dados_influ (50 com pasta em 2026), contando
os nomes de pasta dentro da pasta do dia:

    283x "vídeo bruto"   273x "story"     93x "stories"   43x "bruto"
     25x "brutas"         24x "brutos"    14x "Story"     13x "Vídeo bruto"
     11x "ENTREGAS"       10x "DADOS"     10x "orgânico"   6x "link"
      4x "STORY"           3x "Stories"    2x "REELS"      2x "Bruto"

Então o padrão deles é "story", minúsculo e no SINGULAR, e a variação plural vale
93 pastas, ou seja um quarto do material: a lista de sinônimos é necessária, não
precaução. "link" e "orgânico" existem, minúsculos, mas nesta varredura ficam AO
LADO da pasta de story. Em 03/09/2026 o auditor definiu que as marcações ficam
ACIMA dela, e a varredura daquele dia, em 60 influenciadores, não achou nível
nenhum ABAIXO do tipo.

O QUE MUDOU, E O QUE ISSO DESFEZ

Antes o caminho terminava na pasta do influenciador (layout do Marketing) ou numa
pasta por CICLO (layout de teste). Agora existe pasta do dia e pasta de tipo, e
a PASTA DE CICLO DEIXOU DE EXISTIR NOS DOIS.

O ciclo não desapareceu: ele passa a viver só na coluna CICLO da Monitoramento,
que é onde sempre foi usado de verdade. Data é fato do vídeo e vira pasta; ciclo
é interpretação de contrato e vira campo de planilha. Guardar interpretação como
pasta era o que fazia o mesmo dia poder pertencer a dois ciclos.

QUEM CRIA O QUÊ, e é a parte que protege o Drive deles:

    bet, ano, mês                       só ENCONTRA, nunca cria
    @influenciador                      cria com a trava do cadastro
    DD/MM, marcação e tipo              cria quando faltar

O critério é quem escolhe o nome. Nos quatro de cima existe um nome que alguém
batizou, e o programa não tem como distinguir "nome um pouco diferente" de "pasta
nova", então criar ali produz pasta órfã sem ninguém saber. No nível do MÊS isso
não é hipótese: das 18 pastas de mês de 2026, três não batem letra por letra
("01. Janeiro " com espaço no fim, "08. AGOSTO" em maiúsculas), medido em
30/08/2026.

Nos três de baixo não há escolha de nome: a data vem do vídeo, o tipo vem do
endereço do post e a marcação é uma de três. E sem criar esses três, alguém teria
que criar cerca de 46 pastas por dia à mão antes de o programa poder gravar.

Nada aqui fala com o Google: as listagens são dublês.

    py testes\teste_hierarquia_das_pastas.py
"""
import datetime
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


class DriveFalso:
    """Uma árvore de pastas de mentira, para ver o que o programa procura e o
    que ele cria."""

    def __init__(self, existentes=()):
        # {(id_pai, nome): id} — as pastas que já existem
        self.pastas = {}
        self.criadas = []
        self.proximo = 100
        for caminho in existentes:
            pai = "raiz"
            for nome in caminho:
                chave = (pai, nome)
                if chave not in self.pastas:
                    self.proximo += 1
                    self.pastas[chave] = f"id{self.proximo}"
                pai = self.pastas[chave]

    def listar(self, id_pai):
        return [{"name": nome, "id": ident}
                for (pai, nome), ident in self.pastas.items() if pai == id_pai]

    def criar(self, nome, id_pai):
        self.proximo += 1
        ident = f"id{self.proximo}"
        self.pastas[(id_pai, nome)] = ident
        self.criadas.append(nome)
        return ident


DATA = datetime.date(2026, 9, 1)


def rodar():
    import fluxo_downloads as fluxo

    print("--- 1. o caminho tem os seis níveis, na ordem certa ---")
    layout_antes = fluxo.LAYOUT_PASTAS
    try:
        fluxo.LAYOUT_PASTAS = fluxo.LAYOUT_MARKETING
        ate_influ = fluxo.caminho_ate_influenciador("novoinflu", DATA, "LOTTU")
        dentro = fluxo.pastas_dentro_do_influenciador("Ciclo 7", DATA, "STORIES")
        caminho = ate_influ + dentro
    finally:
        fluxo.LAYOUT_PASTAS = layout_antes

    # QUANTOS NÍVEIS DE DENTRO DO INFLUENCIADOR PODEM SER CRIADOS, contados da
    # própria árvore e não escritos à mão.
    #
    # Aqui eram 2 e 3, fixos, e a inversão de 03/09/2026 quebrou o teste: com a
    # marcação, os níveis de dentro passaram de dois (data, tipo) para três
    # (data, marcação, tipo), e com 2 o programa não podia criar nem a pasta do
    # dia. É o mesmo defeito que a seção 4b guarda, e ele apareceu aqui primeiro.
    #
    # NÃO É a conta da produção, e a diferença importa. Lá o limite é maior e
    # inclui o mês e o influenciador, porque quem barra o influenciador é a trava
    # do cadastro (`autorizar`), que estas seções não usam. Aqui o limite é
    # justamente o que faz o influenciador que falta INTERROMPER, que é o que as
    # seções 4b, 5 e 6 existem para provar. Usar a conta da produção fez as três
    # deixarem de interromper, e elas passaram a não provar nada.
    CRIAVEIS_DE_DENTRO = len(dentro)

    print(f"       {' / '.join(caminho)}")
    # A MARCAÇÃO ENTROU NO CAMINHO EM 03/09/2026, ACIMA DO TIPO.
    #
    # Antes o caminho terminava em "01/09 / story", e a pasta "orgânico", quando
    # havia, ficava DENTRO de story. O auditor pediu a inversão e definiu três
    # marcações, e depois duas: orgânico e link. Sem passar marcação nenhuma, o
    # caminho cai em "link", que é o padrão e é o que preserva o comportamento
    # antigo: quem não marcava nada caía no tipo direto.
    conferir(caminho == ["03. LOTTU", "2026", "09. Setembro", "@novoinflu",
                         "01/09", "link", "story"],
             "bet, ano, mês, @influenciador, data, marcação e tipo", str(caminho))
    conferir(caminho[-1] == "story",
             "e o TIPO continua sendo o último nível antes do arquivo",
             "é assim na pasta deles: a medição de 02/09 não achou nível nenhum "
             "abaixo do tipo em 60 influenciadores")

    print()
    print("--- 2. o CICLO não aparece no caminho ---")
    # O ponto central da mudança. O rótulo do ciclo é passado para a função e
    # simplesmente não entra na árvore.
    conferir(not any("ciclo" in str(p).lower() for p in caminho),
             "nenhum nível do caminho é ciclo, mesmo passando 'Ciclo 7'",
             str(caminho))

    print()
    print("--- 3. o TIPO do post escolhe a pasta, e os nomes são os medidos ---")
    conferir(fluxo.pasta_do_tipo("STORIES") == "story",
             "STORIES vira \"story\", minúsculo e no singular, como no Drive deles",
             fluxo.pasta_do_tipo("STORIES"))
    conferir(fluxo.pasta_do_tipo("REELS") == "reels", "REELS vira \"reels\"")
    conferir(fluxo.pasta_do_tipo("FEED") == "feed", "FEED vira \"feed\"")
    # Tipo desconhecido cai em story de propósito: das 124 pastas de tipo
    # medidas no Drive deles, todas as 124 eram de story, e parar o envio depois
    # de a chamada ao Instagram já ter sido gasta seria pior que acertar o caso
    # dominante.
    conferir(fluxo.pasta_do_tipo(None) == "story",
             "tipo que não veio cai em story, em vez de derrubar o envio")
    conferir(fluxo.pasta_do_tipo("TIKTOK") == "story",
             "e tipo que não tem pasta também")

    print()
    print("--- 3b. a MARCAÇÃO é uma pasta ACIMA da do tipo ---")
    # A ORDEM INVERTEU EM 03/09/2026, e vale registrar as duas versões do pedido.
    #
    # Em 01/09 ele pediu: "caso a pessoa opte por escolher como orgânico, ele vai
    # para uma pasta dentro de storie, reels ou feed". Era dentro.
    #
    # Em 03/09, depois de definir as três marcações por grau de publicidade, ele
    # pediu o contrário: "e aí dentro dessas é que vai o tipo de mídia, se é
    # reels/feed/stories". E a medição de 02/09 sustenta: na pasta deles não há
    # nível nenhum abaixo do tipo, em 60 influenciadores lidos.
    padrao = fluxo.pastas_dentro_do_influenciador("Ciclo 7", DATA, "REELS")
    conferir(padrao == ["01/09", "link", "reels"],
             "sem escolher nada, cai em link", str(padrao))
    for chave, pasta in (("organico", "orgânico"), ("link", "link")):
        caminho_marc = fluxo.pastas_dentro_do_influenciador(
            "Ciclo 7", DATA, "REELS", marcacao=chave)
        conferir(caminho_marc == ["01/09", pasta, "reels"],
                 f"{chave} vira a pasta \"{pasta}\", ACIMA de reels",
                 str(caminho_marc))
    # O caso que a inversão tinha que garantir: o tipo é sempre o fim.
    conferir(all(fluxo.pastas_dentro_do_influenciador(
        "Ciclo 7", DATA, tipo, marcacao=chave)[-1] == esperado
        for chave in fluxo.PASTA_DA_MARCACAO
        for tipo, esperado in (("STORIES", "story"), ("REELS", "reels"),
                               ("FEED", "feed"))),
        "e o tipo é o último nível nas nove combinações")

    print()
    print("--- 4. cria data e tipo, NUNCA o influenciador ---")
    # A árvore do Marketing existe até o mês; a pasta do influenciador também,
    # porque é eles que criam. Faltam a data e a do tipo.
    drive = DriveFalso(existentes=[["03. LOTTU", "2026", "09. Setembro", "@novoinflu"]])
    destino = fluxo.descer_pelo_caminho(
        "raiz", caminho, drive.listar, criar=drive.criar,
        criar_somente_ultimos=CRIAVEIS_DE_DENTRO)
    conferir(destino is not None, "achou o destino")
    conferir(drive.criadas == ["01/09", "link", "story"],
             "criou SÓ a pasta do dia, a da marcação e a do tipo",
             str(drive.criadas))

    print()
    print("--- 4b. com a marcação, o influenciador CONTINUA protegido ---")
    # POR QUE ESTE TESTE EXISTE: o número de níveis que podem ser criados era
    # escrito à mão como 2. Quando a pasta de orgânico entrou, o caminho passou a
    # ter três níveis de dentro, e um 2 fixo criaria o terceiro contando do fim,
    # que é a pasta do INFLUENCIADOR. Ou seja: a regra mais importante do Drive
    # deles cairia como efeito colateral de acrescentar uma pasta.
    caminho_org = (["03. LOTTU", "2026", "09. Setembro", "@quemnaoexiste"]
                   + fluxo.pastas_dentro_do_influenciador("Ciclo 7", DATA,
                                                          "STORIES",
                                                          marcacao="organico"))
    drive_org = DriveFalso(existentes=[["03. LOTTU", "2026", "09. Setembro"]])
    try:
        fluxo.descer_pelo_caminho("raiz", caminho_org, drive_org.listar,
                                  criar=drive_org.criar,
                                  criar_somente_ultimos=CRIAVEIS_DE_DENTRO)
        conferir(False, "deveria ter interrompido no influenciador que falta")
    except fluxo.PastaNaoExisteNoDrive as e:
        conferir("@quemnaoexiste" in str(e),
                 "com três níveis de dentro, ainda para no influenciador",
                 str(e)[:110])
        conferir(not drive_org.criadas, "e não cria nada", str(drive_org.criadas))

    # E o caminho normal cria os três, sem tocar no influenciador.
    drive_org2 = DriveFalso(existentes=[["03. LOTTU", "2026", "09. Setembro",
                                         "@quemnaoexiste"]])
    fluxo.descer_pelo_caminho("raiz", caminho_org, drive_org2.listar,
                              criar=drive_org2.criar,
                              criar_somente_ultimos=CRIAVEIS_DE_DENTRO)
    conferir(drive_org2.criadas == ["01/09", "orgânico", "story"],
             "existindo o influenciador, cria dia, marcação e tipo, nessa ordem",
             str(drive_org2.criadas))

    print()
    print("--- 5. pasta de influenciador que falta INTERROMPE ---")
    # Este é o caso que a regra existe para pegar: @ digitado errado, que o
    # programa não tem como distinguir de influenciador novo. Sem a pasta dele, o
    # programa para e diz qual criar, em vez de criar uma pasta órfã.
    drive2 = DriveFalso(existentes=[["03. LOTTU", "2026", "09. Setembro"]])
    try:
        fluxo.descer_pelo_caminho("raiz", caminho, drive2.listar,
                                  criar=drive2.criar,
                                  criar_somente_ultimos=CRIAVEIS_DE_DENTRO)
        conferir(False, "deveria ter interrompido, e não interrompeu")
    except fluxo.PastaNaoExisteNoDrive as e:
        conferir("@novoinflu" in str(e),
                 "para e diz qual pasta de influenciador falta", str(e)[:110])
        conferir(not drive2.criadas,
                 "e não cria nada quando para", str(drive2.criadas))

    print()
    print("--- 6. mês que falta também interrompe ---")
    drive3 = DriveFalso(existentes=[["03. LOTTU", "2026"]])
    try:
        fluxo.descer_pelo_caminho("raiz", caminho, drive3.listar,
                                  criar=drive3.criar,
                                  criar_somente_ultimos=CRIAVEIS_DE_DENTRO)
        conferir(False, "deveria ter interrompido no mês")
    except fluxo.PastaNaoExisteNoDrive as e:
        conferir("09. Setembro" in str(e), "para no mês que falta", str(e)[:110])

    print()
    print("--- 7. a comparação de nomes continua tolerante ---")
    # Medido em 30/08: das 18 pastas de mês de 2026 no Drive deles, três não
    # batem letra por letra. Sem tolerância, o programa criaria uma segunda
    # pasta ao lado de cada uma, ou pararia dizendo que falta pasta que existe.
    drive4 = DriveFalso(existentes=[["03. LOTTU", "2026", "09. SETEMBRO ", "@novoinflu"]])
    destino4 = fluxo.descer_pelo_caminho("raiz", caminho, drive4.listar,
                                         criar=drive4.criar,
                                         criar_somente_ultimos=CRIAVEIS_DE_DENTRO)
    conferir(destino4 is not None,
             "acha \"09. SETEMBRO \" quando procura \"09. Setembro\"")
    conferir(drive4.criadas == ["01/09", "link", "story"],
             "e não cria um mês duplicado", str(drive4.criadas))

    print()
    print("--- 7b. \"story\" ENCONTRA a pasta \"stories\" que já existe ---")
    # ESTE É O DEFEITO QUE A MEDIÇÃO EVITOU. A comparação tolerante ignora espaço
    # e maiúscula, e nada além: para ela "story" e "stories" são palavras
    # diferentes, e as duas existem no Drive deles (124 e 2). Sem os sinônimos, o
    # programa criaria uma "story" ao lado da "stories" que já tem material, e o
    # material do mesmo dia ficaria dividido entre as duas.
    for grafia in ("stories", "STORY", "Story"):
        # A pasta do tipo agora fica DENTRO da marcação, então a grafia existente
        # tem que estar no lugar novo. Com ela no lugar antigo, o programa criaria
        # a árvore inteira ao lado, que é justamente o defeito desta seção.
        drive5 = DriveFalso(existentes=[
            ["03. LOTTU", "2026", "09. Setembro", "@novoinflu", "01/09", "link",
             grafia]])
        destino5 = fluxo.descer_pelo_caminho("raiz", caminho, drive5.listar,
                                            criar=drive5.criar,
                                            criar_somente_ultimos=CRIAVEIS_DE_DENTRO)
        conferir(destino5 is not None and not drive5.criadas,
                 f"procurando \"story\", usa a pasta \"{grafia}\" e não cria outra",
                 str(drive5.criadas))

    print()
    print("--- 7c. o programa AVISA quando cria pasta de nome discutível ---")
    # POR QUE ESTE AVISO EXISTE (01/09/2026): a pasta do tipo é criada pelo
    # programa e tem grafia variável, que era exatamente o problema do nível do
    # mês. Criar em silêncio é o que transforma um nome errado em dezenas de
    # pastas duplicadas antes de alguém notar.
    #
    # E a pasta do DIA fica fora do aviso de propósito: ela é criada uma vez por
    # influenciador por dia, então avisar sobre ela seriam dezenas de linhas
    # iguais por rodada, e aviso que aparece sempre é aviso que ninguém lê.
    ditos = []
    drive6 = DriveFalso(existentes=[["03. LOTTU", "2026", "09. Setembro", "@novoinflu"]])
    fluxo.descer_pelo_caminho("raiz", caminho, drive6.listar, criar=drive6.criar,
                              criar_somente_ultimos=CRIAVEIS_DE_DENTRO,
                              avisar=ditos.append)
    # SÃO DOIS AVISOS DESDE 03/09/2026, e não um: a marcação também é pasta de
    # palavra, e ela é NOVA no Drive deles (a medição de 02/09 não achou "publi"
    # nem "link" nesse nível em 60 influenciadores). Nome novo é exatamente o que
    # precisa ser conferido na primeira vez.
    #
    # A conferência é sobre QUAIS pastas entram no aviso, e não sobre a
    # quantidade: era `len(ditos) == 1`, e um número fixo aqui volta a quebrar na
    # próxima pasta que entrar, sem nada ter piorado.
    criadas_avisadas = [d.split("\"")[1] for d in ditos if "\"" in d]
    conferir(sorted(criadas_avisadas) == ["link", "story"],
             "avisa a pasta da marcação e a do tipo", str(criadas_avisadas))
    conferir("01/09" not in criadas_avisadas,
             "e NÃO avisa a pasta do dia, que é criada todo dia",
             str(criadas_avisadas))
    conferir(not fluxo.nome_de_pasta_a_conferir("01/09"),
             "pasta de data não entra no aviso")
    conferir(fluxo.nome_de_pasta_a_conferir("orgânico"),
             "pasta de orgânico entra, porque também é palavra")

    print()
    print("--- 8. o nome do arquivo é \"@influenciador - tela N\" ---")
    # O SEPARADOR MUDOU EM 02/09/2026. Era "@handle Tela N", e o auditor mostrou
    # arquivos reais da pasta do Marketing: "@juremafox - tela 1" e
    # "@juremafox - tela 2", sem data. O programa passou a escrever igual.
    #
    # Esta seção exigia antes que o nome NÃO tivesse hífen, o que era um jeito
    # torto de provar que a data havia saído. O hífen virou o separador, então a
    # conferência passou a olhar a data, que é o que ela sempre quis dizer.
    nome = fluxo.nome_no_padrao_marketing("novoinflu", DATA, 2, "algum/video.mp4")
    conferir(nome == "@novoinflu - tela 2.mp4", "igual ao padrão deles", nome)
    conferir("01/09" not in nome and "09" not in nome.replace("mp4", ""),
             "e sem a data, porque agora ela é pasta", nome)
    conferir(fluxo.ler_nome_de_arquivo(nome) == ("novoinflu", 2),
             "e o programa consegue LER de volta o que ele mesmo escreveu",
             "senão a numeração recomeça do 1 e cria dois \"tela 1\" no mesmo dia")

    print()
    print("--- 9. os DOIS padrões de nome continuam sendo lidos ---")
    # As pastas do Marketing estão cheias de arquivos no padrão antigo, e é
    # lendo esses nomes que o programa sabe em qual tela continuar. Deixar de
    # reconhecê-los faria a numeração recomeçar do 1.
    conferir(fluxo.ler_nome_de_arquivo("@juremafox - tela 3.mp4") == ("juremafox", 3),
             "lê o padrão com hífen, que é o deles")
    # Os arquivos que o PRÓPRIO programa criou entre 01/09 e 02/09/2026 estão
    # com este nome. Deixar de ler seria recomeçar a numeração em cima deles.
    conferir(fluxo.ler_nome_de_arquivo("@novoinflu Tela 3.mp4") == ("novoinflu", 3),
             "e continua lendo o que ele escreveu antes, sem hífen")
    conferir(fluxo.ler_nome_de_arquivo("27/08 - @dudafreiret - tela 2.mp4")
             == ("dudafreiret", 2),
             "e o padrão do Marketing que traz a data na frente")
    conferir(fluxo.ler_nome_de_arquivo("@FULANO - TELA 4.MP4") == ("fulano", 4),
             "sem se importar com maiúscula")
    # "colocar um traço ou underline", pedido do auditor em 02/09/2026. Escrever é
    # sempre com traço; a folga é para ler o que vier de quem sobe à mão.
    conferir(fluxo.ler_nome_de_arquivo("@juremafox_tela 5.mp4") == ("juremafox", 5),
             "lê sublinhado como separador também")
    # O CASO QUE PODIA DAR ERRADO: @ que TERMINA em sublinhado, e @ que tem
    # sublinhado no meio. Os dois existem de verdade (@ranchodomaia__ e
    # @lf_freitas), e o @ tem que ficar inteiro.
    conferir(fluxo.ler_nome_de_arquivo("@ranchodomaia__ - tela 1.mp4")
             == ("ranchodomaia__", 1),
             "e o @ que termina em sublinhado fica inteiro",
             str(fluxo.ler_nome_de_arquivo("@ranchodomaia__ - tela 1.mp4")))
    conferir(fluxo.ler_nome_de_arquivo("@lf_freitas_tela 2.mp4") == ("lf_freitas", 2),
             "assim como o @ com sublinhado no meio",
             str(fluxo.ler_nome_de_arquivo("@lf_freitas_tela 2.mp4")))
    # O nome que o programa escreveu ANTES desta mudança, e que está no Drive.
    conferir(fluxo.ler_nome_de_arquivo("@ranchodomaia__ Tela 1.mp4")
             == ("ranchodomaia__", 1),
             "e o arquivo que já está no Drive continua contando")
    conferir(fluxo.ler_nome_de_arquivo("qualquer coisa.mp4") is None,
             "e devolve nada para nome que não segue padrão nenhum")
    conferir(fluxo.ler_nome_de_arquivo("") is None, "sem quebrar com vazio")
    # O separador é exigido: sem isso, o @ ganancioso faria "@fulanotela3" ser
    # lido como tela 3 do @fulano, e um arquivo com nome parecido entraria na
    # contagem de outro influenciador.
    conferir(fluxo.ler_nome_de_arquivo("@fulanotela3.mp4") is None,
             "e não inventa tela em nome sem separador",
             str(fluxo.ler_nome_de_arquivo("@fulanotela3.mp4")))

    print()
    print("--- 10. a pasta do dia usa o formato do Marketing ---")
    conferir(fluxo.pasta_da_data(DATA) == "01/09",
             "DD/MM, como nas pastas \"DD/MM - bruto\" deles",
             fluxo.pasta_da_data(DATA))
    conferir(fluxo.pasta_da_data(None) == "sem-data",
             "e diz sem-data quando não há data, em vez de chutar hoje")

    print()
    print("--- 11. material bruto fica fora, em TODAS as grafias medidas ---")
    # O auditor confirmou em 01/09/2026 que os vídeos brutos vão para outro
    # Drive. O que já está neste continua tendo que ficar de fora, e as grafias
    # abaixo são as que a varredura encontrou de verdade.
    import drive_client
    conferir("bruto" in drive_client.NOMES_SUBPASTA_IGNORADA,
             "a regra é por pedaço do nome, e o termo é \"bruto\"",
             str(drive_client.NOMES_SUBPASTA_IGNORADA))
    for grafia in ("vídeo bruto", "VÍDEO BRUTO", "Vídeo bruto", "vídeos brutos",
                   "vído bruto", "bruto", "Bruto", "brutos", "brutas"):
        conferir(fluxo.e_pasta_de_bruto(grafia), f"reconhece \"{grafia}\"")
    # "brutas" É O CASO QUE ESTAVA PASSANDO. A regra procurava só "bruto", e
    # "brutas" não contém "bruto": 25 pastas de material não editado entravam na
    # análise como se fossem peça publicada. Encontrado na varredura dos ativos.
    conferir("bruta" in drive_client.NOMES_SUBPASTA_IGNORADA,
             "o feminino \"bruta\" está na lista, senão \"brutas\" passa",
             str(drive_client.NOMES_SUBPASTA_IGNORADA))
    conferir(not fluxo.e_pasta_de_bruto("story"), "e não confunde story com bruto")
    conferir(not fluxo.e_pasta_de_bruto("01/09"), "nem a pasta do dia")

    # A LISTAGEM TAMBÉM PULA BRUTO, e isso é economia com motivo: das pastas
    # dentro da pasta do dia, 127 eram de bruto e 124 de story, então pular corta
    # metade das visitas. E evita comparar um vídeo publicado com a versão não
    # editada dele, que apareceria como reaproveitamento.
    import inspect
    fonte_listagem = inspect.getsource(fluxo._arquivos_do_influenciador)
    conferir("e_pasta_de_bruto" in fonte_listagem,
             "a listagem de arquivos não desce em pasta de bruto")

    print()
    print("--- 12. a listagem desce TRÊS níveis, senão não vê os arquivos ---")
    # DEFEITO ENCONTRADO NO PRIMEIRO TESTE REAL, em 01/09/2026, e que os dublês
    # anteriores não pegariam: a listagem descia UM nível, o que bastava para
    # "@influenciador / Ciclo N / arquivos". Com a árvore nova os arquivos ficam
    # dois níveis abaixo, em "@influenciador / DD/MM / story", e três quando o
    # post é orgânico.
    #
    # O sintoma foi dois arquivos do mesmo dia saírem os dois como "Tela 1". O
    # estrago maior nem apareceu no teste: procurar_arquivo_repetido usa a mesma
    # listagem, então a detecção de vídeo reaproveitado parava em silêncio, e
    # reaproveitamento é achado de contrato.
    fonte = fonte_listagem
    conferir("profundidade=3" in fonte,
             "a listagem desce três níveis por padrão",
             "com dois, arquivo de post orgânico fica invisível")
    conferir("def descer(" in fonte,
             "e desce de forma recursiva, em vez de um laço de um nível")

    # O rótulo devolvido tem que carregar o caminho, senão quem conta telas do
    # dia não sabe de qual dia o arquivo é: ele veria só "Link".
    conferir("rotulo} / {sub['name']}" in fonte or "/ {sub['name']}" in fonte,
             "o rótulo carrega o caminho relativo, não só o último nome",
             "sem isso, arquivo em '01/09 / Link' apareceria como 'Link'")

    # E a contagem de telas usa o começo do rótulo para saber o dia.
    fonte_tela = inspect.getsource(fluxo.proxima_tela)
    conferir("startswith(pasta_do_dia)" in fonte_tela,
             "e a contagem de telas casa o dia pelo começo do caminho")

    print()
    print("--- 13. a marcação chega ao Drive pelos DOIS caminhos ---")
    # POR QUE OS DOIS: material entra por duas portas. A seção do link do
    # Instagram, que qualquer analista usa, e o envio de arquivo, que é da
    # SUPERVISÃO e é por onde a FOTO entra. Marcação que só funciona numa das duas
    # deixa metade do material sem ela, e a maioria do material orgânico que já
    # está no Drive deles é imagem (11 imagens contra 6 vídeos).
    #
    # A LEITURA DA CÉLULA VIROU TRÊS VALORES EM 03/09/2026. Antes era e_sim, que
    # só respondia sim ou não. O que não pode se perder é o "SIM" das linhas
    # gravadas até 02/09: sem isso, a marcação delas passaria a ser lida como
    # publi e ninguém perceberia.
    conferir(fluxo.marcacao_de_celula("SIM") == "organico",
             "o SIM das linhas antigas continua sendo lido como orgânico",
             fluxo.marcacao_de_celula("SIM"))
    for texto in ("ORGANICO", "orgânico", " x ", "TRUE"):
        conferir(fluxo.marcacao_de_celula(texto) == "organico",
                 f"{texto!r} é orgânico", fluxo.marcacao_de_celula(texto))
    conferir(fluxo.marcacao_de_celula("LINK") == "link", "LINK é link")
    conferir(fluxo.marcacao_de_celula("PUBLI") == "link",
             "PUBLI, que existiu por horas em 03/09, é lido como link",
             "ele corrigiu: publi e link sao a mesma coisa")
    # "LINK + ORGANICO" existiu por menos de uma hora e caiu: peça orgânica nunca
    # é link ao mesmo tempo. Célula com esse texto cai no padrão, que é link.
    conferir(fluxo.marcacao_de_celula("LINK + ORGANICO") == "link",
             "e LINK + ORGANICO, que caiu, é lido como link",
             fluxo.marcacao_de_celula("LINK + ORGANICO"))
    # Vazio cai em publi, que é o caso normal e é o que a tela oferece como
    # padrão. Antes vazio queria dizer "não é orgânico", que era o mesmo grupo.
    conferir(fluxo.marcacao_de_celula("") == "link"
             and fluxo.marcacao_de_celula(None) == "link",
             "vazio cai em link, que é a peça publicitária comum")
    conferir(fluxo.marcacao_de_celula("qualquer coisa") == "link",
             "e texto que não se reconhece também, em vez de derrubar o download",
             "parar aqui gastaria a chamada ao Instagram sem guardar nada")

    # A CONFERÊNCIA É PELA INTENÇÃO, e não pelo valor exato. A primeira versão
    # exigia ULTIMA_COLUNA_FILA == "F" e LARGURA_LINHA_MON == 28, e as duas
    # mudaram em 02/09/2026 quando a coluna de quem pediu entrou. O teste falhou
    # por ter congelado um número, e não por defeito: o que precisa valer é que a
    # coluna da marcação EXISTA e CAIBA na faixa gravada.
    conferir(fluxo.COL_FILA.get("marcacao") == 5,
             "a fila tem coluna de marcação, senão ela não chega ao trabalhador",
             str(fluxo.COL_FILA))
    ultima_da_fila = ord(fluxo.ULTIMA_COLUNA_FILA) - ord("A") + 1
    conferir(ultima_da_fila > fluxo.COL_FILA["marcacao"],
             "e a faixa gravada na fila alcança essa coluna",
             f"faixa até {fluxo.ULTIMA_COLUNA_FILA}, marcação na "
             f"{fluxo.letra_da_coluna(fluxo.COL_FILA['marcacao'] + 1)}")
    conferir(fluxo.COL_MON.get("marcacao") == 28,
             "a Monitoramento tem a coluna MARCACAO na AB",
             str(fluxo.COL_MON.get("marcacao")))
    conferir(fluxo.LARGURA_LINHA_MON >= fluxo.COL_MON["marcacao"],
             "e a largura da linha gravada alcança ela",
             f"largura={fluxo.LARGURA_LINHA_MON}")

    # A largura sai da última entrada do bloco, e não de uma chave escrita à mão.
    # Escrita à mão, acrescentar coluna faria a linha gravada ficar mais curta que
    # a faixa pedida ao Google, que é erro de API e não de dado.
    #
    # A CONFERÊNCIA MIROU NO LUGAR CERTO EM 16/09/2026: antes ela bania
    # qualquer menção a `COL_MON["validado_em"]` na função inteira, supondo
    # que só apareceria ali por engano (essa chave era a última do bloco antes
    # de marcacao/pedido_por/arquivo entrarem). Passou a existir um uso
    # legítimo dela (marcar VALIDADO_EM como "N/A" numa linha que nunca vai
    # ser analisada), então o texto largo passou a reprovar código correto. O
    # que precisa valer é só a linha que CRIA o vetor: `[""] * LARGURA_LINHA_MON`,
    # não `[""] * 30` nem `[""] * COL_MON["validado_em"]`.
    fonte_registro = inspect.getsource(fluxo.registrar_na_monitoramento)
    conferir('valores = [""] * LARGURA_LINHA_MON' in fonte_registro,
             "a largura da linha não está escrita à mão")

    caminhos = {
        "seção do link (tela)": ("pages/1_Downloads_e_Organizacao.py",
                                 "marcacao_nova"),
        # MUDOU PARA A PÁGINA DE UPLOADS EM 23/09/2026, junto com a seção
        # inteira de "Enviar arquivo do post".
        "envio de arquivo (supervisão)": ("pages/5_Uploads.py",
                                          '"marcacao": marcacao_foto'),
        "download no trabalhador": ("fluxo_downloads.py",
                                    'marcacao=marcacao_de_celula(item.get("marcacao"))'),
        "envio no trabalhador": ("trabalhador.py",
                                 'marcacao=campos.get("marcacao")'),
    }
    for rotulo, (arquivo, trecho) in caminhos.items():
        with open(os.path.join(BASE, arquivo), encoding="utf-8") as f:
            conferir(trecho in f.read(), f"{rotulo} passa a marcação adiante",
                     f"não achei {trecho!r} em {arquivo}")

    # FOTO É PARTE DISSO: é o formato mais comum do material orgânico, e o envio
    # de arquivo é o único caminho por onde ela entra.
    for extensao in (".png", ".jpg", ".jpeg"):
        conferir(extensao in fluxo.EXTENSOES_ENVIO, f"aceita {extensao}")
    # "ENVIAR ARQUIVO DO POST" SE MUDOU PARA A PÁGINA DE UPLOADS EM 23/09/2026.
    with open(os.path.join(BASE, "pages/5_Uploads.py"),
              encoding="utf-8") as f:
        tela = f.read()
    conferir(re.search(r"autorizacao_para\(\s*\n?\s*acesso\.PAPEL_SUPERVISAO",
                       tela) is not None,
             "e o envio de arquivo continua exigindo a credencial da supervisão")

    print()
    print("--- 14. as TRÊS marcações: nomes, aviso e o que é gravado ---")
    # As definições são do auditor, em 03/09/2026, e não são "orgânico contra
    # pago": são graus de peça publicitária. Orgânico só mostra a marca; publi
    # anuncia com os avisos; link anuncia e leva o redirecionamento.
    conferir(fluxo.pasta_da_marcacao("organico") == "orgânico",
             "orgânico é a pasta com acento, como no Drive deles")
    conferir(fluxo.pasta_da_marcacao("link") == "link", "link")
    conferir(len(fluxo.PASTA_DA_MARCACAO) == 2,
             "e são DUAS marcações, não três",
             str(sorted(fluxo.PASTA_DA_MARCACAO)))
    conferir(fluxo.pasta_da_marcacao("link") == "link", "link")
    conferir(fluxo.pasta_da_marcacao(None) == "link"
             and fluxo.pasta_da_marcacao("inventado") == "link",
             "marcação que não existe cai no padrão, em vez de derrubar o envio")
    conferir(fluxo.MARCACAO_PADRAO == "link",
             "e o padrão é link, que preserva o comportamento antigo",
             "quem não marcava nada caía no tipo direto, e o tipo direto é link")

    # AS TRÊS ENTRAM NO AVISO DE GRAFIA, e o motivo é medido: a varredura de
    # 02/09/2026 não achou "publi" nem "link" nesse nível em 60 influenciadores.
    # São nomes NOVOS no Drive deles, e nome novo é o que precisa ser conferido.
    for pasta in ("orgânico", "link"):
        conferir(fluxo.nome_de_pasta_a_conferir(pasta),
                 f"o programa avisa ao criar \"{pasta}\"")

    # O QUE VAI PARA A PLANILHA DA FILA é a palavra, e não "SIM": a linha é lida
    # por gente, e com três marcações "SIM" não diria qual.
    import sheets_client
    guardados = {"ler_fila": fluxo.ler_fila}
    escritas = []
    original = sheets_client.adicionar_linhas
    try:
        fluxo.ler_fila = lambda: []
        sheets_client.adicionar_linhas = (
            lambda pid, aba, faixa, linhas: escritas.extend(linhas))
        # A ARMADILHA QUE ISTO GUARDA (03/09/2026): texto_da_marcacao só
        # conhecia CHAVE, e recebendo o conteúdo de uma célula antiga ("SIM")
        # caía no padrão e devolvia "LINK" para uma peça ORGÂNICA. Numa rotina de
        # padronização da coluna isso trocaria a marcação em silêncio, e a linha
        # voltaria a ser julgada pela régua dos avisos. Pego pela conferência
        # antes de escrever, e não em produção.
        for chave, esperado in (("organico", "ORGANICO"), ("link", "LINK"),
                                ("SIM", "ORGANICO"), ("sim", "ORGANICO"),
                                ("PUBLI", "LINK"), ("orgânico", "ORGANICO"),
                                (None, "LINK")):
            escritas.clear()
            fluxo.adicionar_na_fila(
                [("", f"https://www.instagram.com/p/COD{chave}/", "", "LOTTU",
                  chave, "eu@egb")])
            gravado = escritas[0][fluxo.COL_FILA["marcacao"]] if escritas else None
            conferir(gravado == esperado,
                     f"a fila grava {esperado!r} para {chave!r}", str(gravado))
    finally:
        sheets_client.adicionar_linhas = original
        for nome, funcao in guardados.items():
            setattr(fluxo, nome, funcao)

    # E A MONITORAMENTO GRAVA SEMPRE, inclusive publi. Antes a coluna só recebia
    # valor quando era orgânico, porque vazio queria dizer "entrega normal". Com
    # três, vazio não distinguiria publi de "ninguém marcou", e essa coluna vai
    # decidir a régua da análise: célula ambígua ali é o pior lugar possível.
    fonte_reg = inspect.getsource(fluxo.registrar_na_monitoramento)
    trecho_marcacao = [l for l in fonte_reg.splitlines()
                       if 'COL_MON["marcacao"]' in l]
    conferir(len(trecho_marcacao) == 1, "escreve a marcação num lugar só",
             str(trecho_marcacao))
    conferir(trecho_marcacao and "if " not in trecho_marcacao[0],
             "e escreve SEMPRE, sem depender de a peça ser orgânica",
             str(trecho_marcacao))

    # A TELA OFERECE ESCOLHA ÚNICA DE TRÊS, e não caixas independentes. Pelas
    # definições do auditor as três são excludentes: orgânico não anuncia, publi
    # e link anunciam, e link é publi com redirecionamento.
    #
    # AS DUAS SEÇÕES FICARAM EM PÁGINAS DIFERENTES EM 23/09/2026: "Link" e o
    # formulário de download continuam em Downloads, "Enviar arquivo do
    # post" se mudou para Uploads. A lista ROTULO_DA_MARCACAO em si também se
    # mudou, para fluxo_downloads.py, justamente para as duas páginas
    # continuarem lendo a MESMA lista. Por isso as conferências abaixo somam
    # o conteúdo das duas telas, em vez de olhar uma só.
    with open(os.path.join(BASE, "pages/1_Downloads_e_Organizacao.py"),
              encoding="utf-8") as f:
        tela_downloads = f.read()
    tela_duas_paginas = tela_downloads + "\n" + tela
    conferir("ROTULO_DA_MARCACAO" in tela_duas_paginas,
             "as telas têm os três rótulos num lugar só")
    conferir(tela_duas_paginas.count("st.radio(") >= 2,
             "e usa escolha única nas duas seções, link e envio de arquivo",
             "caixa de marcar permitiria as duas ao mesmo tempo, e o arquivo mora "
             "num lugar só")
    # Linha de código, e não o arquivo todo: o comentário da mudança cita o
    # rótulo antigo de propósito. Foi o quarto tropeço igual em dois dias.
    codigo_da_tela = [l for l in tela_duas_paginas.splitlines()
                      if l.strip() and not l.strip().startswith("#")]
    conferir(not any("Este post é orgânico" in l for l in codigo_da_tela),
             "a caixa de marcar de orgânico saiu do código")
    conferir(not any("st.checkbox(\n" in l or "organico_foto" in l
                     for l in codigo_da_tela),
             "e a do envio de arquivo também")
    fonte_motor = inspect.getsource(fluxo)
    primeira = fonte_motor.split("ROTULO_DA_MARCACAO = {")[1].split(":")[0]
    conferir("link" in primeira,
             "e link é a primeira da lista, então é a que vem escolhida",
             primeira.strip())


if __name__ == "__main__":
    print("=" * 74)
    print("  Hierarquia das pastas, e o ciclo fora do Drive")
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
