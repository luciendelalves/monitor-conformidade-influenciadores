# -*- coding: utf-8 -*-
"""
EXERCITA A RESERVA: prova que o plano B do download ainda funciona.

POR QUE ESTE ARQUIVO EXISTE (05/09/2026)

Pedido do auditor, depois de conversarmos sobre o que fazer se o yt-dlp cair:
"faça o teste para exercitar a ferramenta reserva sim".

O PROBLEMA QUE ELE RESOLVE É O DO BACKUP NUNCA TESTADO. A cadeia de recuo do
download é boa no papel: Story tenta yt-dlp e cai no instaloader; post tenta
yt-dlp anônimo, depois autenticado, depois instaloader pelo código do post. Só
que a reserva só roda quando a principal falha, ou seja, quase nunca. Se ela
apodrecer, ninguém descobre no dia a dia: descobre no dia em que o yt-dlp
quebrar, que é exatamente o dia em que ela era necessária.

As duas raspam o mesmo Instagram. Quando o Instagram muda de verdade, as duas
podem quebrar na mesma semana, e a segunda não avisa.

O QUE ESTE ARQUIVO TESTA, E O QUE ELE NÃO TESTA. Ele NÃO baixa vídeo de verdade,
de propósito: bater no Instagram dentro da suíte gastaria o teto diário da conta
(cada conversa conta, mesmo sem trazer vídeo) e deixaria o resultado do teste
dependendo do humor da rede. O que ele prova é o que dá para provar sem rede:

  - a reserva está instalada e IMPORTA (o modo de falha mais comum de uma
    biblioteca velha é parar de importar, por causa de dependência incompatível)
  - as funções que o recuo chama existem e têm a assinatura esperada
  - o recuo é acionado quando a principal falha
  - o recuo NÃO é acionado quando a falha parece bloqueio
  - a ordem de tentativa é a esperada, e não uma coincidência do código

A PARTE QUE EXIGE REDE tem arquivo próprio, `teste_download_em_duas_etapas.py`,
que é o que se roda depois de atualizar. Este aqui roda sempre, de graça.

Rodar:

    py testes\teste_reserva_de_download.py
"""
import inspect
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
    import fluxo_downloads as fluxo

    print("--- 1. a reserva esta instalada e IMPORTA ---")
    # O MODO DE FALHA MAIS COMUM de biblioteca velha nao e dar erro ao usar, e
    # sim parar de importar, porque alguma dependencia dela subiu de versao e
    # ficou incompativel. Isso quebra o recuo inteiro, e em silencio: so aparece
    # quando o yt-dlp falha e o programa tenta a reserva.
    try:
        import instaloader
        conferir(True, "instaloader importa")
        versao = getattr(instaloader, "__version__", None)
        conferir(bool(versao), "e diz a propria versao", str(versao))
    except Exception as e:
        conferir(False, "instaloader importa", f"{type(e).__name__}: {e}")

    print()
    print("--- 2. as funcoes do recuo existem ---")
    for nome in ("baixar_story_ytdlp", "baixar_story_instaloader",
                 "baixar_post_instaloader", "baixar_video"):
        conferir(callable(getattr(fluxo, nome, None)),
                 f"{nome} existe e e chamavel")

    print()
    print("--- 3. o recuo do STORY: yt-dlp primeiro, instaloader depois ---")
    # Substituo as duas pontas por funcoes falsas e vejo a ORDEM real, em vez de
    # ler o codigo e torcer. A principal falha; a reserva tem que ser chamada.
    chamadas = []

    def falso_ytdlp(link, pasta):
        chamadas.append("ytdlp")
        raise RuntimeError("erro qualquer de extracao")

    def falso_insta(link, pasta, link_post_do_perfil=None):
        chamadas.append("instaloader")
        return "/caminho/do/video.mp4"

    guardados = (fluxo.baixar_story_ytdlp, fluxo.baixar_story_instaloader)
    fluxo.baixar_story_ytdlp = falso_ytdlp
    fluxo.baixar_story_instaloader = falso_insta
    try:
        link_story = "https://www.instagram.com/stories/fulano/123456789/"
        resultado = fluxo.baixar_video(link_story, "/pasta")
        conferir(chamadas == ["ytdlp", "instaloader"],
                 "tenta o yt-dlp e, ao falhar, chama a reserva",
                 str(chamadas))
        conferir(resultado == "/caminho/do/video.mp4",
                 "e devolve o que a reserva baixou", str(resultado))

        print()
        print("--- 4. mas o recuo NAO acontece se parecer BLOQUEIO ---")
        # E a trava mais importante da cadeia. Tentar o segundo caminho logo
        # depois de o Instagram ter dito nao e uma segunda chamada em sequencia,
        # que e justamente o comportamento que marca a conta. Melhor falhar
        # aquele link do que arriscar a conta que atende todo mundo.
        chamadas.clear()

        def falso_ytdlp_bloqueado(link, pasta):
            chamadas.append("ytdlp")
            raise RuntimeError("HTTP Error 429: Too Many Requests")

        fluxo.baixar_story_ytdlp = falso_ytdlp_bloqueado
        try:
            fluxo.baixar_video(link_story, "/pasta")
            conferir(False, "bloqueio NAO cai para a reserva",
                     "nao levantou erro, e devia")
        except Exception as e:
            conferir(chamadas == ["ytdlp"],
                     "bloqueio NAO cai para a reserva",
                     f"chamadas: {chamadas}")
            conferir("429" in str(e),
                     "e o erro original sobe, sem ser mascarado", str(e)[:60])
    finally:
        fluxo.baixar_story_ytdlp, fluxo.baixar_story_instaloader = guardados

    print()
    print("--- 5. o reconhecedor de bloqueio esta de pe ---")
    # A secao 4 depende inteiramente dele. Se ele parar de reconhecer as
    # mensagens de bloqueio, a trava vira decorativa e o programa passa a bater
    # de novo no Instagram logo depois de levar um nao.
    for mensagem, esperado in (
        ("HTTP Error 429: Too Many Requests", True),
        ("rate-limit reached", True),
        ("Please wait a few minutes before you try again", True),
        ("No video formats found", False),
        ("arquivo nao encontrado no disco", False),
    ):
        obtido = bool(fluxo.parece_bloqueio(RuntimeError(mensagem)))
        conferir(obtido is esperado,
                 f"{'reconhece' if esperado else 'nao confunde'}: {mensagem[:42]}",
                 f"esperado {esperado}, veio {obtido}")

    print()
    print("--- 6. o recuo do POST tambem existe, e pela mesma regra ---")
    fonte = inspect.getsource(fluxo.baixar_video)
    conferir("baixar_post_instaloader" in fonte,
             "post tem recuo para o instaloader")
    conferir("parece_bloqueio" in fonte,
             "e o recuo do post tambem respeita a trava de bloqueio",
             "sem isso, post bloqueado bateria duas vezes seguidas")

    print()
    print("--- 7. existe caminho que NAO depende de biblioteca nenhuma ---")
    # O ultimo degrau do plano B: a pessoa baixa a mao e sobe pela tela. Se este
    # caminho sumir, uma quebra simultanea das duas bibliotecas para a auditoria
    # inteira, em vez de so tornar o trabalho mais lento.
    conferir(hasattr(fluxo, "PASTA_ENVIOS"),
             "a pasta de envio manual existe no programa")
    # "ENVIAR ARQUIVO DO POST" SE MUDOU PARA A PÁGINA DE UPLOADS EM
    # 23/09/2026, junto com "Link só para registrar". Downloads ficou só com
    # a fila automatizada do Instagram.
    with open(os.path.join(BASE, "pages", "5_Uploads.py"),
              encoding="utf-8") as f:
        tela = f.read()
    conferir("file_uploader" in tela,
             "e a tela de Uploads tem o campo para subir o arquivo")

    print()
    print("--- 8. a reserva aparece no retrato das bibliotecas ---")
    import baixadores
    nomes = [b["nome"] for b in baixadores.estado()]
    conferir("instaloader" in nomes,
             "o instaloader e acompanhado junto com o yt-dlp",
             "se a reserva nao for acompanhada, ela apodrece sem ninguem ver")
    insta = [b for b in baixadores.estado() if b["nome"] == "instaloader"][0]
    conferir(insta["presente"], "e consta como instalado", str(insta["versao"]))


if __name__ == "__main__":
    print("=" * 74)
    print("  Exercita a RESERVA do download: o plano B ainda esta de pe?")
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
