# -*- coding: utf-8 -*-
r"""
Prova que story de FOTO é baixado e analisado, e não recusado.

O QUE HAVIA ATÉ 02/09/2026

O download de story recusava foto com "Story é uma foto, não um vídeo, fora do
escopo atual da automação". Era recusa de política, não limite técnico: naquele
ponto do código o item JÁ ESTÁ EM MÃO, vindo da mesma chamada ao Instagram, e
baixar a foto é o mesmo `download_storyitem`.

O auditor perguntou duas vezes, a segunda já esperando um não: "NÃO DÁ pra baixar
foto pelo mesmo link do video não ne?".

POR QUE A RECUSA ERA ERRADA, e não só uma limitação: peça publicitária em foto
tem os mesmos deveres da em vídeo. Aviso da portaria, +18, "aposta não é
investimento" e declaração de publicidade não dependem de a peça se mover.
Recusar foto deixava fora da auditoria peça que a Portaria alcança igual, e a
recusa aparecia como FALHA na tela, o que lê como defeito do programa.

E o resto do caminho já estava pronto, o que este teste também prova: a análise
tem escada de OCR para imagem, mede nitidez, pergunta à visão no próprio arquivo
e pula o áudio; o envio pela tela já aceitava PNG e JPG desde antes; e o nome do
arquivo preserva a extensão que vier.

Foto é até mais simples de analisar que vídeo: uma tela só, sem amostragem de
quadros, então sem o risco que existiu até 29/08/2026 de todos os quadros saírem
do primeiro segundo do clipe.

    py testes\teste_story_de_foto.py
"""
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


def rodar():
    import inspect
    import fluxo_downloads as fluxo

    print("--- 1. o download de story não recusa mais foto ---")
    fonte = inspect.getsource(fluxo.baixar_story_instaloader)
    conferir("fora do escopo atual da automação" not in fonte,
             "a recusa saiu do código",
             "ela aparecia como FALHA na tela, lendo como defeito do programa")
    conferir("if not item.is_video" not in fonte,
             "e não há mais desvio por não ser vídeo")
    conferir("EXTENSOES_IMAGEM" in fonte,
             "o arquivo gerado pode ser imagem",
             "sem isto o download 'daria certo' e não acharia o arquivo")
    conferir("EXTENSOES_VIDEO" in fonte,
             "e vídeo continua valendo, pelo mesmo caminho")

    print()
    print("--- 2. as extensões de imagem são as que o Instagram entrega ---")
    for extensao in (".jpg", ".jpeg", ".png"):
        conferir(extensao in fluxo.EXTENSOES_IMAGEM, f"aceita {extensao}")
    conferir(not (fluxo.EXTENSOES_IMAGEM & fluxo.EXTENSOES_VIDEO),
             "e nenhuma extensão está nos dois conjuntos",
             "senão a preferência por vídeo não decidiria nada")

    print()
    print("--- 3. o nome do arquivo preserva a extensão da foto ---")
    import datetime
    data = datetime.date(2026, 9, 2)
    for origem, esperado in (("algum/story.jpg", ".jpg"),
                             ("algum/story.PNG", ".png"),
                             ("algum/story.mp4", ".mp4")):
        nome = fluxo.nome_no_padrao_marketing("fulano", data, 1, origem)
        conferir(nome.endswith(esperado), f"{origem} -> {nome}", nome)
    # E o nome continua legível pela contagem de telas, que é o que evita dois
    # "tela 1" no mesmo dia.
    nome_foto = fluxo.nome_no_padrao_marketing("fulano", data, 3, "x/story.jpg")
    conferir(fluxo.ler_nome_de_arquivo(nome_foto) == ("fulano", 3),
             "e a contagem de telas lê o nome da foto igual",
             str(fluxo.ler_nome_de_arquivo(nome_foto)))

    print()
    print("--- 4. a análise trata imagem de ponta a ponta ---")
    import validar_avisos_portaria136 as motor
    for extensao in (".jpg", ".jpeg", ".png"):
        conferir(extensao in motor.IMAGE_EXTS,
                 f"o motor de análise reconhece {extensao}")
    fonte_visual = inspect.getsource(motor.analisar_visual)
    conferir("if ext in IMAGE_EXTS" in fonte_visual,
             "e tem caminho próprio para imagem, antes do de vídeo")
    conferir("ocr_image_rapido" in fonte_visual and "ocr_image_forte" in fonte_visual,
             "com a mesma escada de OCR do vídeo",
             "imagem ilegível não pode virar 'conforme' por falta de tentativa")
    # Áudio não existe em foto, e pedir transcrição de imagem gastaria a etapa
    # mais lenta do programa para nada.
    conferir(motor.analisar_audio("qualquer/coisa.jpg", "/tmp") == "",
             "e o áudio é pulado, sem tentar transcrever imagem")

    print()
    print("--- 5. o resto do caminho já aceitava foto ---")
    import pipeline_influenciadores as pipeline
    conferir(pipeline.is_midia("image/jpeg") and pipeline.is_midia("image/png"),
             "a orquestração considera imagem como mídia")
    conferir(pipeline.MIME_EXT.get("image/jpeg") == ".jpg",
             "e sabe a extensão de cada tipo de imagem")
    conferir(fluxo.EXTENSOES_IMAGEM <= fluxo.EXTENSOES_ENVIO,
             "e o envio pela tela já aceitava foto desde antes")

    print()
    print("--- 6. a acusação de reaproveitamento não chama foto de vídeo ---")
    # Ela compara BYTE A BYTE, então sempre alcançou imagem; só o texto dizia
    # vídeo. Com story de foto baixando, o texto errado passou a ser alcançável.
    fonte_envio = inspect.getsource(fluxo.enviar_para_drive)
    conferir("PEÇA REAPROVEITADA" in fonte_envio,
             "a marca fala de peça, não de vídeo")
    conferir("VÍDEO REAPROVEITADO" not in fonte_envio,
             "e o texto antigo saiu",
             "essa marca vai para a planilha da auditoria")

    print()
    print("--- 7. post de FEED com foto: o yt-dlp não devolve, o instaloader sim ---")
    # MEDIDO PELO AUDITOR em 02/09/2026, e é o que motivou este caminho. Ele
    # colou um post de carrossel e trouxe o erro exato:
    #
    #     ERROR: [Instagram] DcT0RkaCHbc: No video formats found!
    #
    # O yt-dlp é extrator de vídeo: post sem vídeo nenhum não tem formato para
    # ele achar. No mesmo teste, story de foto funcionou, porque story já tinha
    # caminho pelo instaloader.
    for endereco, esperado in (
            ("https://www.instagram.com/p/DcT00FOFtmf/?img_index=1", "DcT00FOFtmf"),
            ("https://www.instagram.com/juremafox/p/DcT00FOFtmf/", "DcT00FOFtmf"),
            ("https://www.instagram.com/juremafox/reel/Dct7HEOPkjP/?hl=pt", "Dct7HEOPkjP"),
            ("https://www.instagram.com/reel/Dct7HEOPkjP/", "Dct7HEOPkjP")):
        achado = fluxo._REGEX_CODIGO_DO_POST.search(endereco)
        conferir(achado and achado.group("codigo") == esperado,
                 f"lê o código de {endereco[:52]}",
                 str(achado and achado.group("codigo")))
    conferir(fluxo._REGEX_CODIGO_DO_POST.search(
        "https://www.instagram.com/stories/fulano/123/") is None,
        "e não confunde endereço de story com post")

    fonte_baixar = inspect.getsource(fluxo.baixar_video)
    conferir("baixar_post_instaloader" in fonte_baixar,
             "o caminho normal recua para o instaloader")
    conferir("parece_bloqueio" in fonte_baixar,
             "mas NÃO recua quando foi bloqueio",
             "seria segunda chamada logo depois de o Instagram dizer não, que é "
             "o comportamento que marca conta")

    fonte_post = inspect.getsource(fluxo.baixar_post_instaloader)
    conferir("situacao_da_conta" in fonte_post,
             "o caminho novo respeita a pausa e o teto do dia")
    conferir("_contar_uso_instagram" in fonte_post,
             "e conta a chamada, mesmo que o arquivo não venha",
             "sem isso o programa acharia ter feito menos chamadas do que fez")
    conferir("_acionar_freio" in fonte_post,
             "e aciona o freio ao levar bloqueio")
    conferir("from_shortcode" in fonte_post,
             "baixa pelo CÓDIGO do post",
             "não pelo número interno do perfil, que é a consulta limitada")
    conferir("Profile.from_username" not in fonte_post,
             "e não toca no endereço que respondeu 429 em 31/08")

    print()
    print("--- 8. carrossel: cada imagem é uma tela, com linha própria ---")
    conferir(fluxo._chave_natural("x_2.jpg") < fluxo._chave_natural("x_10.jpg"),
             "a ordem coloca _2 antes de _10",
             "tela trocada aponta o achado para a imagem errada")
    ordenado = sorted(["p_10.jpg", "p_2.jpg", "p_1.jpg"], key=fluxo._chave_natural)
    conferir(ordenado == ["p_1.jpg", "p_2.jpg", "p_10.jpg"],
             "e um carrossel de dez sai na ordem certa", str(ordenado))

    fonte_fila = inspect.getsource(fluxo.processar_fila)
    conferir("isinstance(baixado, str)" in fonte_fila,
             "a fila distingue um caminho de uma lista de caminhos",
             "texto tem len(), e sem isso o programa criaria uma linha por letra")
    conferir("for indice, caminho in enumerate(caminhos" in fonte_fila,
             "e envia cada arquivo do post")
    # A fila de análise sai do log, então uma entrada por link deixaria as outras
    # imagens do carrossel no Drive e fora da análise.
    trecho_laco = fonte_fila.split("for indice, caminho in enumerate(caminhos")[1]
    trecho_laco = trecho_laco.split("sheets_client.escrever_lote")[0]
    conferir("log.append" in trecho_laco,
             "com uma entrada de log por arquivo, e não por link",
             "é do log que sai a fila de análise")


if __name__ == "__main__":
    print("=" * 74)
    print("  Story de foto: baixa e analisa, em vez de recusar")
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
