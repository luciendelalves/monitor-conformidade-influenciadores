# -*- coding: utf-8 -*-
"""
A idade da biblioteca de download é visível, e a falha aponta a saída manual.

POR QUE ESTE ARQUIVO EXISTE (05/09/2026)

Pedido do auditor: "e sobre a queda do yt-dlp, caso isso aconteça qual seria o
plano b? temos que pensar num plano B nesses casos", seguido de "queria
implementar mecanismos que pode atualizar ou alterar o programa de baixar, pq
sei que são voláteis".

O LEVANTAMENTO MOSTROU QUE O PLANO B JÁ EXISTIA, em camadas, e é melhor do que
parecia: Story tenta yt-dlp e cai no instaloader; post tenta yt-dlp anônimo,
depois autenticado, depois instaloader pelo código do post; e o envio de arquivo
pela tela funciona sem biblioteca nenhuma de download.

FALTAVAM DUAS COISAS, e são elas que este teste protege:

  1. Nada dizia que a versão instalada estava envelhecendo. Medido naquele dia:
     yt-dlp 2026.7.4, de 63 dias, com a 2026.8.19 publicada. O requirements.txt
     já avisava que versão travada por muito tempo para de funcionar, e que o
     sintoma é download falhando sem motivo aparente. O envelhecimento
     acontecia em silêncio.
  2. A mensagem de falha genérica não apontava a saída manual. Quem lia a
     planilha via "FALHA: <erro técnico>" e ficava sem próximo passo, mesmo
     existindo um caminho que resolve.

O PROGRAMA PASSOU A ATUALIZAR PELO BOTÃO, e a seção 5 mudou de lado por causa
disso. A primeira versão dela proibia qualquer execução de comando; hoje ela
exige o contrário, com as travas. O motivo da virada foi o auditor apontar que
"outras pessoas mais leigas que irão utilizar": para quem não abre terminal,
mostrar um comando não é instrução, é obstáculo, e o efeito prático é que a peça
mais volátil do programa nunca é atualizada. As três coisas que o botão escondia
viraram travas dentro dele, e é isso que a seção 5 protege agora.

Rodar:

    py testes\teste_baixadores_e_plano_b.py
"""
import datetime
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


def rodar():
    import baixadores

    print("--- 1. a idade sai da propria versao, sem consultar a internet ---")
    # O yt-dlp versiona por data ("2026.8.19"), entao a versao ja diz quando
    # saiu. Depender de consulta a internet para saber isso seria fragil na rede
    # da empresa, que ja bloqueia dominio de ferramenta.
    conferir(baixadores._data_da_versao("2026.8.19") == datetime.date(2026, 8, 19),
             "versao de calendario vira data")
    conferir(baixadores._data_da_versao("4.15.3") is None,
             "versao que NAO e de calendario devolve None",
             "instaloader usa 4.15.3, e para ele nao ha idade a calcular")
    conferir(baixadores._data_da_versao("") is None
             and baixadores._data_da_versao(None) is None,
             "vazio nao quebra")
    conferir(baixadores._data_da_versao("2026.13.99") is None,
             "data impossivel devolve None em vez de estourar",
             "mes 13 nao existe")

    print()
    print("--- 2. 'sem data' NAO e a mesma coisa que 'esta novo' ---")
    # A distincao importa: dizer as duas com o mesmo valor esconderia que o
    # programa simplesmente nao sabe a idade daquela biblioteca.
    hoje = datetime.date(2026, 9, 5)
    linhas = {b["nome"]: b for b in baixadores.estado(hoje)}
    insta = linhas.get("instaloader")
    conferir(insta is not None and insta["dias"] is None,
             "instaloader nao tem idade calculavel", str(insta and insta["dias"]))
    conferir(insta is not None and insta["envelheceu"] is False,
             "e por isso nao e marcado como velho",
             "sem data nao vira alarme falso")

    print()
    print("--- 3. o limite de idade e explicito e testavel ---")
    conferir(isinstance(baixadores.DIAS_ATE_ENVELHECER, int)
             and baixadores.DIAS_ATE_ENVELHECER > 0,
             f"existe um limite em dias ({baixadores.DIAS_ATE_ENVELHECER})")
    # Uma versao de ontem nunca pode ser marcada como velha; uma de um ano
    # atras sempre tem que ser. Sao os dois extremos, e travam a regra sem
    # depender do numero exato.
    ontem = hoje - datetime.timedelta(days=1)
    antiga = hoje - datetime.timedelta(days=365)
    for data, esperado, rotulo in ((ontem, False, "de ontem"),
                                   (antiga, True, "de um ano atras")):
        versao = f"{data.year}.{data.month}.{data.day}"
        d = baixadores._data_da_versao(versao)
        dias = (hoje - d).days
        conferir((dias > baixadores.DIAS_ATE_ENVELHECER) is esperado,
                 f"versao {rotulo} " + ("e" if esperado else "nao e") + " velha",
                 f"{dias} dia(s)")

    print()
    print("--- 4. a tela mostra o aviso, e so quando ha o que avisar ---")
    with open(os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py"),
              encoding="utf-8") as f:
        tela = f.read()
    conferir("import baixadores" in tela, "a tela conhece o modulo")
    conferir("precisa_de_atencao" in tela,
             "e pergunta se ha algo precisando de atencao")
    conferir("if _baixadores_velhos:" in tela,
             "o aviso so aparece quando ha biblioteca velha",
             "alerta permanente vira parte do cenario e para de ser lido")
    # O PASSO A PASSO SAIU DA TELA em 05/09/2026 ("o que der para tirar desses
    # avisos e frase e deixar so o que for essencial"). Nao houve perda: o botao
    # ja executa as travas que os passos mandavam fazer a mao, e quem prefere
    # terminal recebe o comando pronto. O texto longo continua existindo para o
    # `py baixadores.py`, que e onde ainda faz sentido.
    conferir("comando_de_atualizacao" in tela,
             "a tela mostra o comando para quem prefere terminal")
    # ATUALIZADO EM 17/09/2026: o aviso solto virou o botao de verdade
    # (painel_trabalhador.botao_encerrar), bem aqui, em vez de mandar a
    # pessoa procurar la embaixo em "Manutencao". A trava em si
    # (disabled=_de_pe no botao Atualizar agora) continua no lugar.
    conferir('painel_trabalhador.botao_encerrar(key_sufixo="_atualizar")' in tela,
             "e o botao de encerrar aparece aqui mesmo, nao so um aviso",
             "e a unica trava que a pessoa precisa fazer a mao")
    conferir("baixadores.SAIDA_MANUAL" in tela,
             "junto da saida manual, que e o plano B de verdade")

    print()
    print("--- 5. atualizar pelo botao, COM as travas ---")
    # ESTA SECAO JA EXIGIU O CONTRARIO, e a mudanca foi deliberada. A primeira
    # versao proibia qualquer execucao de comando, com o argumento de que um
    # botao de um clique esconde tres coisas que quebram: trabalhador de pe
    # segura a versao velha em memoria, requirements.txt desatualizado faz a
    # proxima maquina instalar a versao velha, e sem teste ninguem sabe se a
    # versao nova funciona.
    #
    # O auditor trouxe o que faltava: "outras pessoas mais leigas que irao
    # utilizar". Para quem nao abre terminal, mostrar um comando nao e
    # instrucao, e obstaculo, e o resultado e que ninguem atualiza nunca.
    #
    # A resposta certa nao era tirar o botao, era por as travas DENTRO dele. E
    # sao essas travas que este teste passa a exigir.
    conferir(callable(getattr(baixadores, "atualizar", None)),
             "existe funcao de atualizar")
    conferir("executor=None" in
             str(__import__("inspect").signature(baixadores.atualizar)),
             "e ela aceita um executor de mentira, para poder ser testada",
             "sem isso, testar exigiria instalar pacote de verdade")

    # TRAVA 1: recusa com o trabalhador de pe.
    conferir("trabalhador_de_pe" in tela,
             "a tela pergunta se o trabalhador esta de pe antes de deixar "
             "atualizar")
    conferir("disabled=_de_pe" in tela,
             "e o botao fica desabilitado enquanto ele estiver",
             "atualizar com ele rodando nao tem efeito: a versao velha "
             "continua carregada na memoria daquele processo")

    # TRAVA 2: anota no requirements.txt.
    conferir(callable(getattr(baixadores, "anotar_no_requirements", None)),
             "existe funcao que anota a versao nova no requirements.txt")
    conferir("anotar_no_requirements" in tela,
             "e a tela a chama depois de atualizar",
             "sem isso a proxima maquina instala a versao velha de novo")

    # TRAVA 3: sabe voltar atras.
    conferir(callable(getattr(baixadores, "comando_de_volta", None)),
             "existe o comando para voltar a versao anterior")
    conferir("comando_de_volta" in tela,
             "e a tela o mostra junto do resultado",
             "atualizar sem saber voltar e aposta")

    # E NAO DIZ QUE DEU CERTO SEM PROVA: comparar antes e depois importa porque
    # o pip pode terminar sem erro e sem atualizar nada.
    conferir('_r["mudou"]' in tela,
             "o sucesso e julgado pela versao ter MUDADO, nao pelo pip "
             "terminar sem erro")

    print()
    print("--- 5b. atualizar de verdade, com um pip de mentira ---")
    # NAO BASTA a funcao aceitar um executor: o que importa e o que ela FAZ com
    # a resposta dele. Aqui o pip "termina sem erro" mas nada muda de versao, e
    # a funcao tem que reconhecer isso como "nao mudou", nao como sucesso. Foi o
    # caso que motivou comparar antes e depois em vez de olhar so o codigo de
    # saida.
    class RespostaFalsa:
        returncode = 0
        stdout = "Requirement already satisfied: yt-dlp"
        stderr = ""

    r = baixadores.atualizar(["yt-dlp"], executor=lambda cmd: RespostaFalsa())
    conferir(r["ok"] is True, "pip sem erro devolve ok", str(r["ok"]))
    conferir(r["mudou"] == [],
             "mas 'mudou' fica vazio quando a versao continua a mesma",
             str(r["mudou"]))

    # E quando o pip nao roda de jeito nenhum, a funcao nao pode estourar: ela
    # devolve o problema, para a tela poder mostrar em vez de quebrar.
    def executor_que_explode(cmd):
        raise OSError("pip nao encontrado")

    r2 = baixadores.atualizar(["yt-dlp"], executor=executor_que_explode)
    conferir(r2["ok"] is False, "pip que nem roda devolve ok=False")
    conferir("pip" in r2["saida"].lower(),
             "e explica o que houve, em vez de estourar", r2["saida"][:60])
    conferir(r2["mudou"] == [], "e nao inventa mudanca nenhuma")

    print()
    print("--- 5c. anotar no requirements.txt troca a linha certa ---")
    import tempfile
    exemplo = "\n".join((
        "# comentario que MENCIONA yt-dlp no meio do texto explicativo",
        "yt-dlp==2026.7.4",
        "instaloader==4.15.3",
        "",
    ))
    pasta = tempfile.mkdtemp(prefix="req_")
    caminho = os.path.join(pasta, "requirements.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(exemplo)
    ok, detalhe = baixadores.anotar_no_requirements("yt-dlp", "2026.8.19",
                                                    caminho=caminho)
    novo = open(caminho, encoding="utf-8").read()
    conferir(ok, "anota a versao nova", str(detalhe))
    conferir("yt-dlp==2026.8.19" in novo, "com a versao certa")
    conferir("atualizado em" in novo, "e com a data da troca")
    # O PONTO DELICADO: o nome do pacote tambem aparece em COMENTARIO, e trocar
    # la estragaria o texto que explica por que a versao e travada.
    conferir("comentario que MENCIONA yt-dlp no meio" in novo,
             "sem estragar o comentario que cita o mesmo nome")
    conferir("instaloader==4.15.3" in novo,
             "e sem tocar na linha das outras bibliotecas")
    ok2, motivo = baixadores.anotar_no_requirements("naoexiste", "1.0",
                                                    caminho=caminho)
    conferir(not ok2, "pacote que nao esta no arquivo devolve recusa, nao erro",
             str(motivo))

    print()
    print("--- 6. as instrucoes nao esquecem o trabalhador ---")
    # Ja aconteceu de atualizar e nao funcionar porque o processo antigo seguia
    # de pe com a versao velha carregada em memoria.
    texto = baixadores.instrucoes()
    conferir("trabalhador" in texto.lower(),
             "as instrucoes mandam fechar o trabalhador antes")
    conferir("requirements" in texto.lower(),
             "e mandam anotar a versao nova no requirements.txt",
             "senao a proxima maquina instala a versao velha de novo")
    conferir("teste_download_em_duas_etapas" in texto,
             "e mandam rodar o teste depois de atualizar")

    print()
    print("--- 7. a falha do download aponta a saida manual ---")
    fonte_fluxo = open(os.path.join(BASE, "fluxo_downloads.py"),
                       encoding="utf-8").read()
    conferir("da para subir o arquivo" in fonte_fluxo
             or "dá para subir o arquivo" in fonte_fluxo,
             "o rotulo de falha generica diz que ha saida",
             'antes era so "FALHA: <erro tecnico>", sem proximo passo')
    conferir("envio de arquivo" in fonte_fluxo,
             "e o texto na tela nomeia o envio de arquivo")

    print()
    print("--- 8. a cadeia de reserva do download continua de pe ---")
    # O plano B automatico ja existia, e nada aqui pode te-lo removido.
    conferir("baixar_story_instaloader" in fonte_fluxo
             and "baixar_story_ytdlp" in fonte_fluxo,
             "Story tem dois caminhos: yt-dlp e instaloader")
    conferir("baixar_post_instaloader" in fonte_fluxo,
             "post tambem tem recuo para o instaloader")
    # A regra que impede a segunda chamada logo apos um bloqueio: e o que evita
    # marcar a conta. Se sumir, o recuo vira risco em vez de protecao.
    conferir(fonte_fluxo.count("parece_bloqueio(") >= 2,
             "e o recuo NAO acontece quando a falha parece bloqueio",
             "segunda chamada logo depois de um nao e o que marca conta")


    print()
    print("--- 9. VISAO DE QUEBRA: le o registro, sem gastar chamada ---")
    # Pedido do auditor depois de a ferramenta do Marketing parar por
    # atualizacao do Instagram. A ideia central: uma quebra de biblioteca tem
    # assinatura propria no registro (falha residual em serie), e distinguir
    # isso de bloqueio importa porque a acao e outra.
    hoje = datetime.date(2026, 9, 5)

    def log_de(status, quantos, dia=None):
        d = (dia or hoje).isoformat()
        return [{"estagio": "A", "quando": f"{d} 10:00", "status": status}
                for _ in range(quantos)]

    quebra = log_de("FALHA, dá para subir o arquivo à mão: erro X", 9) + log_de("OK", 1)
    r = baixadores.saude_do_download(7, ler_log=lambda: quebra, hoje=hoje)
    conferir(r["suspeita_de_quebra"] is True,
             "falha residual em serie ACUSA suspeita de quebra", r["motivo"][:70])

    # AS TRES CAUSAS QUE NAO SAO QUEBRA. Cada uma tem acao diferente, e
    # confundi-las mandaria alguem atualizar biblioteca quando o problema e
    # ritmo, ou esperar quando o problema e a biblioteca.
    for status, rotulo in (
        ("BAIXAR MANUALMENTE (Instagram bloqueou ou exige login)", "bloqueio"),
        ("SEM STORY NO AR (o perfil não tem story publicada agora)", "sem story"),
        ("CONTA PAUSADA — aguardando", "conta pausada"),
    ):
        r2 = baixadores.saude_do_download(7, ler_log=lambda s=status: log_de(s, 12),
                                          hoje=hoje)
        conferir(r2["suspeita_de_quebra"] is False,
                 f"{rotulo} NAO e confundido com quebra de biblioteca",
                 str(r2["por_classe"]))

    # VOLUME MINIMO: alarme falso ensina a ignorar o alarme.
    r3 = baixadores.saude_do_download(7, ler_log=lambda: log_de("FALHA: x", 3),
                                      hoje=hoje)
    conferir(r3["suspeita_de_quebra"] is False,
             "poucas tentativas NAO geram alarme",
             "3 falhas num dia parado nao caracterizam quebra")

    # So o estagio A e download; analise e correcao nao entram no denominador.
    misturado = ([{"estagio": "B", "quando": hoje.isoformat() + " 10:00",
                   "status": "FALHA: analise"} for _ in range(20)]
                 + log_de("OK", 2))
    r4 = baixadores.saude_do_download(7, ler_log=lambda: misturado, hoje=hoje)
    conferir(r4["tentativas"] == 2,
             "so o estagio A conta como tentativa de download",
             f"contou {r4['tentativas']}, esperado 2")

    print()
    print("--- 10. IDADE TAMBEM PARA QUEM NAO VERSIONA POR DATA ---")
    # instaloader (4.15.3) e curl_cffi (0.15.0) nao tem data na versao. Sem a
    # segunda fonte, a reserva envelhecia sem ninguem ver - e a reserva e
    # justamente a que apodrece calada, porque quase nunca roda.
    import json
    import tempfile
    pasta = tempfile.mkdtemp(prefix="versoes_")
    caminho = os.path.join(pasta, "versoes.json")
    mapa = baixadores.registrar_versoes_vistas(hoje=hoje, caminho=caminho)
    conferir(set(mapa) >= {"yt-dlp", "instaloader"},
             "as tres bibliotecas entram no registro de versao vista",
             str(sorted(mapa)))
    conferir(all("visto_em" in v for v in mapa.values()),
             "cada uma com a data em que foi vista")
    # Rodar de novo no mesmo dia nao pode reescrever a data: e isso que faz o
    # contador de "parada ha X dias" medir tempo de verdade.
    antes = json.load(open(caminho, encoding="utf-8"))
    baixadores.registrar_versoes_vistas(
        hoje=hoje + datetime.timedelta(days=30), caminho=caminho)
    depois = json.load(open(caminho, encoding="utf-8"))
    conferir(antes == depois,
             "versao que nao mudou mantem a data original",
             "reescrever zeraria o contador de tempo parado a cada abertura")

    print()
    print("--- 11. a tela mostra as duas coisas ---")
    conferir("saude_do_download" in tela,
             "a tela consulta a saude do download")
    conferir("suspeita_de_quebra" in tela,
             "e avisa quando ha suspeita de quebra")
    conferir("registrar_versoes_vistas" in tela,
             "e mantem a linha de base de versao sozinha",
             "sem isso o contador de tempo parado nunca comeca")

if __name__ == "__main__":
    print("=" * 74)
    print("  Idade do baixador visivel, e falha que aponta a saida manual")
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
