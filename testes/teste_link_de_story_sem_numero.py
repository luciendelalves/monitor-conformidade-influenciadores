# -*- coding: utf-8 -*-
"""
Prova o aviso do endereço de story SEM o número da peça.

O PROBLEMA (achado em 29/08/2026, virou aviso em 01/09/2026)

O endereço de story só ganha o número da mídia quando a pessoa NAVEGA entre os
stories do perfil. Os dois endereços abaixo são reais, do mesmo story, tirados
pelo auditor:

    instagram.com/stories/maumauzk/?hl=pt                       sem o número
    instagram.com/stories/maumauzk/3976150764074509695/?hl=pt   com o número

O segundo aparece depois de passar para o story seguinte e voltar. O auditor
conhece o contorno, mas ninguém deveria precisar saber disso, e nada na tela
dizia. A pergunta dele em 01/09 foi exatamente essa: "como ficou a questão de ter
que passar de storie e voltar para aparecer um link válido?".

O QUE ACONTECIA SEM AVISO, e é o pior tipo de falha deste programa: a chamada ao
Instagram é o recurso escasso, e ela era gasta para descobrir que o link não
servia. Medido no log de 31/08/2026, com @andersonneiff:

    status: Ainda não sei o número do perfil de @andersonneiff, e a consulta
    pelo @ não respondeu agora (429 Too Many Requests)

DOIS CASOS DIFERENTES, e é por isso que a regra não é "barrar tudo":

    perfil já conhecido    passa, com aviso. Funciona se houver UM story no ar.
    perfil desconhecido    barra, porque exigiria a consulta que levou 429.

Barrar tudo tiraria o caso legítimo de quem tem um story só, que foi preservado
de propósito quando essa parte foi escrita em 29/08.

A conferência custa ZERO chamada ao Instagram: é texto do endereço mais o arquivo
de perfis já conhecidos. É isso que permite fazê-la no clique.

    py testes\teste_link_de_story_sem_numero.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

falhas = []

# Os dois endereços reais dos prints do auditor, em 01/09/2026.
SEM_NUMERO = "https://www.instagram.com/stories/maumauzk/?hl=pt"
COM_NUMERO = "https://www.instagram.com/stories/maumauzk/3976150764074509695/?hl=pt"


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    import fluxo_downloads as fluxo

    print("--- 1. endereço COM o número passa sem aviso nenhum ---")
    pode, aviso = fluxo.conferir_link_antes_da_fila(COM_NUMERO)
    conferir(pode and aviso is None,
             "o endereço que o auditor pegou navegando entre os stories",
             f"pode={pode} aviso={str(aviso)[:70]}")

    print()
    print("--- 2. o que NÃO é story não é assunto desta conferência ---")
    for link in ("https://www.instagram.com/maumauzk/reel/Dct7HEOPkjP/?hl=pt",
                 "https://www.instagram.com/p/ABC123/",
                 "https://www.youtube.com/watch?v=abc",
                 ""):
        pode, aviso = fluxo.conferir_link_antes_da_fila(link)
        conferir(pode and aviso is None, f"passa sem aviso: {link[:52] or '(vazio)'}")

    print()
    print("--- 3. sem o número, e perfil DESCONHECIDO: barra ---")
    guardado_antes = fluxo.userid_guardado
    try:
        fluxo.userid_guardado = lambda handle: None
        pode, aviso = fluxo.conferir_link_antes_da_fila(SEM_NUMERO)
        conferir(not pode, "não deixa entrar na fila", f"pode={pode}")
        conferir(bool(aviso) and "429" in aviso,
                 "e a mensagem diz o que já aconteceu de verdade",
                 "sem isso o aviso lê como capricho")
        # A MENSAGEM DEIXOU DE MANDAR NAVEGAR ENTRE OS STORIES (02/09/2026).
        #
        # Esta seção exigia o contrário: que ela ensinasse a "passar para o
        # seguinte e voltar". Em 02/09 o auditor colou um story de perfil novo e
        # respondeu o caso que a mensagem não previa: "nesse caso, o story é
        # único no momento, não consigo passar pro próximo".
        #
        # E o pior não era a instrução impossível, era estar errada: com perfil
        # desconhecido, o número da PEÇA não substitui o número do PERFIL, que é
        # o que falta. Seguir a instrução passaria pela tela e cairia na mesma
        # consulta que levou 429. A conferência estava certa em barrar; a
        # explicação é que apontava para o lugar errado.
        conferir(bool(aviso) and "passe para o seguinte e volte" not in aviso,
                 "NÃO manda navegar entre os stories neste caso",
                 "com um story só não há para onde passar, e não resolveria")
        conferir(bool(aviso) and "não ajuda aqui" in aviso,
                 "e diz que pegar o número não resolve este caso",
                 "senão a pessoa tenta o contorno e volta ao mesmo lugar")
        conferir(bool(aviso) and "Reel ou post" in aviso,
                 "oferece a saída que ensina o perfil ao programa")
        conferir(bool(aviso) and "Ensinar um perfil ao programa" in aviso,
                 "citando o controle pelo nome que está na tela",
                 "mandar 'colar um Reel' sem dizer onde deixava a saída escondida")
        conferir(bool(aviso) and "navegador" in aviso,
                 "e a saída de último caso, para perfil sem Reel nem post")
        conferir(bool(aviso) and "@maumauzk" in aviso,
                 "citando o @ de quem é, para não virar aviso genérico")

        print()
        print("--- 4. sem o número, mas perfil JÁ CONHECIDO: passa avisando ---")
        # Este é o caso que existe desde 29/08 e não pode ser barrado: quem tem
        # UM story só nunca consegue navegar, então nunca consegue o número.
        fluxo.userid_guardado = lambda handle: 1234567890
        pode, aviso = fluxo.conferir_link_antes_da_fila(SEM_NUMERO)
        conferir(pode, "deixa entrar na fila", f"pode={pode}")
        conferir(bool(aviso) and "UM story" in aviso,
                 "avisando que só funciona com um story no ar")
        conferir(bool(aviso) and "passe para o seguinte e volte" in aviso,
                 "e dizendo como pegar o endereço com o número, se houver vários")

    finally:
        fluxo.userid_guardado = guardado_antes

    print()
    print("--- 5. arquivo de perfis ilegível NÃO vira download ---")
    # FALHA FECHADA, e aqui ela é testada de verdade, contra um arquivo corrompido
    # em disco. A primeira versão desta seção trocava userid_guardado por uma
    # função que estourava, o que não prova nada: em produção ela nunca estoura,
    # porque tem o próprio try/except. O que precisa ser provado é o efeito de
    # "não sei", que é barrar em vez de gastar chamada.
    import tempfile
    arquivo_antes = fluxo.ARQUIVO_USERIDS
    try:
        with tempfile.TemporaryDirectory() as tmp:
            ruim = os.path.join(tmp, "instagram_userids.json")
            with open(ruim, "w", encoding="utf-8") as f:
                f.write("{isto nao e json valido")
            fluxo.ARQUIVO_USERIDS = ruim
            conferir(fluxo.userid_guardado("maumauzk") is None,
                     "arquivo corrompido responde \"não sei\", em vez de estourar")
            pode, aviso = fluxo.conferir_link_antes_da_fila(SEM_NUMERO)
            conferir(not pode,
                     "e \"não sei\" leva a BARRAR, não a tentar e gastar chamada",
                     f"pode={pode}")
    finally:
        fluxo.ARQUIVO_USERIDS = arquivo_antes

    print()
    print("--- 6. a conferência não fala com o Instagram ---")
    # É o que a torna possível no clique. Se ela passar a fazer chamada, o aviso
    # deixa de ser barato e o remédio fica pior que a doença.
    # NOMES DE CÓDIGO, e não palavras do texto. A primeira versão desta seção
    # proibia também "descobrir", que aparece na EXPLICAÇÃO da função ("precisa
    # descobrir o número interno do perfil"), então ela reprovava a própria
    # documentação. Conferir prosa por engano é fácil quando o comentário é longo.
    import inspect
    corpo = inspect.getsource(fluxo.conferir_link_antes_da_fila)
    if '"""' in corpo:
        # Tira o docstring, para sobrar só o que executa.
        partes = corpo.split('"""')
        corpo = partes[0] + ("".join(partes[2:]) if len(partes) > 2 else "")
    for proibido in ("yt_dlp", "instaloader", "requests", "urlopen",
                     "userid_por_link_de_post", "baixar_story"):
        conferir(proibido not in corpo,
                 f"não usa {proibido}",
                 "a conferência tem que custar zero chamada")

    print()
    print("--- 7. a tela usa a conferência ANTES de enfileirar ---")
    caminho = os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py")
    with open(caminho, encoding="utf-8") as f:
        tela = f.read()
    conferir("conferir_link_antes_da_fila" in tela,
             "a tela de Downloads chama a conferência")
    posicao_conferencia = tela.find("link_serve, aviso_do_link")
    posicao_fila = tela.find("fluxo.adicionar_na_fila")
    conferir(0 < posicao_conferencia < posicao_fila,
             "e chama ANTES de adicionar_na_fila",
             "depois seria tarde: o link já estaria na fila para o trabalhador")

    print()
    print("--- 8. ensinar o perfil: sem baixar, sem linha na Monitoramento ---")
    # A saída criada em 02/09 para o caso do story único num perfil novo. A outra
    # saída que existia, colar um Reel na fila, resolve o perfil mas baixa o vídeo
    # e cria linha na Monitoramento: material entrando na auditoria só para o
    # programa aprender um número.
    conferir("aprender_perfil_por_link" in tela,
             "a tela oferece o controle")
    conferir("Ensinar um perfil ao programa" in tela,
             "com o mesmo nome que a mensagem de recusa cita",
             "nome diferente na mensagem e na tela manda a pessoa procurar")

    guardados = {n: getattr(fluxo, n) for n in
                 ("userid_guardado", "userid_por_link_de_post",
                  "userid_e_handle_por_link_de_post", "guardar_userid",
                  "situacao_da_conta")}
    try:
        print("     endereço que não é de Reel nem de post:")
        for ruim in (SEM_NUMERO, "https://www.youtube.com/watch?v=abc", "", "oi"):
            try:
                fluxo.aprender_perfil_por_link(ruim)
                conferir(False, f"recusa {ruim[:40] or '(vazio)'}", "não recusou")
            except ValueError as e:
                conferir("Reel" in str(e),
                         f"recusa e explica: {ruim[:34] or '(vazio)'}", str(e)[:60])
            except Exception as e:
                conferir(False, f"recusa {ruim[:40] or '(vazio)'}",
                         f"erro errado: {type(e).__name__}")

        print("     perfil que o programa JÁ conhece:")
        # Não pode consultar nada nem gastar chamada: se consultasse, clicar duas
        # vezes no botão gastaria duas vezes o recurso escasso.
        def _nao_deveria(*a, **k):
            raise AssertionError("consultou o Instagram para perfil já conhecido")
        fluxo.userid_guardado = lambda handle: 999
        fluxo.userid_por_link_de_post = _nao_deveria
        fluxo.userid_e_handle_por_link_de_post = _nao_deveria
        handle, uid, gastou = fluxo.aprender_perfil_por_link(
            "https://www.instagram.com/maumauzk/reel/Dct7HEOPkjP/?hl=pt")
        conferir((handle, uid, gastou) == ("maumauzk", 999, 0),
                 "responde do que já sabe, sem gastar chamada",
                 f"{handle} {uid} {gastou}")

        print("     perfil novo:")
        guardados_agora = {}
        fluxo.userid_guardado = lambda handle: None
        # DUBLE DA FUNCAO NOVA (06/09/2026): aprender_perfil_por_link passou a
        # chamar userid_e_handle_por_link_de_post, que devolve (numero, @).
        # Sem trocar o duble aqui, a funcao de VERDADE rodava dentro do
        # teste e falava com o Instagram, gastando chamada do teto.
        fluxo.userid_e_handle_por_link_de_post = lambda link: (55501, None)
        fluxo.guardar_userid = lambda h, u: guardados_agora.update({h: u})
        # Dublê do contador: primeiro a leitura de antes, depois a de depois.
        leituras = iter([(True, "", 3, 17), (True, "", 4, 16)])
        fluxo.situacao_da_conta = lambda: next(leituras)
        handle, uid, gastou = fluxo.aprender_perfil_por_link(
            "https://www.instagram.com/ranchodomaia__/reel/DcoV8jCgNB3/")
        conferir(handle == "ranchodomaia__", "lê o @ do próprio endereço", handle)
        conferir(guardados_agora == {"ranchodomaia__": 55501},
                 "guarda o número do perfil", str(guardados_agora))
        conferir(gastou == 1,
                 "e diz que o teto do dia andou, quando andou",
                 "a tentativa anônima é grátis e a autenticada não, e quem "
                 "clica não tem como saber qual aconteceu")

        print("     perfil novo, resolvido sem gastar chamada:")
        leituras = iter([(True, "", 3, 17), (True, "", 3, 17)])
        fluxo.situacao_da_conta = lambda: next(leituras)
        _h, _u, gastou = fluxo.aprender_perfil_por_link(
            "https://www.instagram.com/ranchodomaia__/p/ABC123/")
        conferir(gastou == 0, "não inventa gasto que não houve", str(gastou))
    finally:
        for nome, funcao in guardados.items():
            setattr(fluxo, nome, funcao)


if __name__ == "__main__":
    print("=" * 74)
    print("  Endereço de story sem o número da peça")
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
