# -*- coding: utf-8 -*-
"""
Prova de onde sai o @ que vira nome de pasta no Drive.

POR QUE ESTE TESTE EXISTE (30/08/2026)

O nome da pasta é o que liga o vídeo ao influenciador. Errar o @ não quebra
nada de imediato: cria uma pasta a mais no Drive do Marketing, com um vídeo
dentro, e ninguém percebe até alguém procurar. O programa não tem como
distinguir @ errado de influenciador novo, então esse erro não dá aviso.

Duas fontes alimentam esse @:

  1. o ENDEREÇO, quando ele traz (story, /perfil/reel/CODIGO)
  2. os DADOS QUE VÊM COM O VÍDEO, para os endereços curtos que não trazem
     (instagram.com/reel/CODIGO), que é o que o "copiar link" gera

A fonte 2 entrou hoje. Sem ela, o endereço curto obrigava a digitar o @ à mão,
e é a digitação que erra.

    py testes\teste_handle_do_servidor.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fluxo_downloads as fluxo

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


ENDERECOS = [
    # (endereço, @ esperado, o que é)
    ("https://www.instagram.com/stories/luket4/3712345678901234567/",
     "luket4", "story com o número da mídia"),
    ("https://www.instagram.com/stories/luket4/",
     "luket4", "story sem o número"),
    ("https://www.instagram.com/feijhonys/reel/DMvHalbg8dD/",
     "feijhonys", "reel com o perfil no endereço"),
    ("https://www.instagram.com/reel/DMvHalbg8dD/",
     None, "endereço curto: não tem @ nenhum ali"),
    ("https://www.instagram.com/p/DMvHalbg8dD/",
     None, "post curto: idem"),
    ("https://www.instagram.com/share/reel/DMvHalbg8dD/",
     None, "o 'copiar link' do Instagram, que já criou uma pasta @share"),
    ("https://www.youtube.com/watch?v=abc123",
     None, "YouTube não tem @ no endereço"),
    ("https://www.tiktok.com/@alguem/video/12345",
     None, "TikTok tem, mas em outro formato, e não é baixado aqui"),
]

DADOS_DO_VIDEO = [
    # (o que a plataforma devolveu, @ esperado, o que é)
    ({"channel": "feijhonys"}, "feijhonys", "campo principal"),
    ({"uploader_id": "luket4"}, "luket4", "quando só o segundo campo vem"),
    ({"uploader": "@Bahiadohype"}, "bahiadohype", "tira o @ e baixa a caixa"),
    ({"channel": "", "uploader_id": "luket4"}, "luket4", "campo vazio não conta"),
    ({}, None, "sem dado nenhum"),
    (None, None, "nem o conjunto de dados veio"),

    # Os que precisam ser RECUSADOS, e o motivo de cada um
    ({"channel": "4777871830"}, None,
     "número interno de perfil: virou nome de pasta no baixador local"),
    ({"channel": "Canal do Fulano"}, None,
     "nome de exibição com espaço, não é @"),
    ({"uploader": "Responsável D Silva"}, None, "idem, com maiúscula"),
    ({"channel": "share"}, None, "palavra da lista de recusa"),
    ({"channel": "perfil oficial"}, None, "espaço no meio"),
    ({"channel": "nome-com-hifen"}, None, "hífen não existe em @ do Instagram"),

    # Recusar um campo não pode impedir de olhar o seguinte
    ({"channel": "Canal do Fulano", "uploader_id": "canaloficial"}, "canaloficial",
     "recusa o primeiro e aceita o próximo"),
    ({"channel": "4777871830", "uploader": "luket4"}, "luket4",
     "número no primeiro campo, @ de verdade no terceiro"),
]


def rodar():
    print("--- 1. o @ tirado do endereço ---")
    for endereco, esperado, oque in ENDERECOS:
        veio = fluxo.handle_do_link(endereco)
        conferir(veio == esperado, f"{oque}: {esperado}", f"veio {veio!r}")

    print()
    print("--- 2. o @ tirado dos dados que vêm com o vídeo ---")
    for info, esperado, oque in DADOS_DO_VIDEO:
        veio = fluxo.handle_dos_dados_do_video(info)
        conferir(veio == esperado, f"{oque}: {esperado}", f"veio {veio!r}")

    print()
    print("--- 3. a regra que não pode voltar atrás ---")
    conferir(fluxo.handle_dos_dados_do_video({"channel": "Canal do Fulano"}) is None,
             "nome de exibição NUNCA vira @ à força",
             "limpar em vez de recusar criaria @canaldofulano, que não existe")
    conferir(fluxo.handle_do_link("https://www.instagram.com/share/reel/DMvHalbg8dD/") is None,
             "o endereço de 'copiar link' NUNCA devolve @share")
    conferir(fluxo.handle_dos_dados_do_video({"channel": "4777871830"}) is None,
             "número de perfil NUNCA vira nome de pasta")

    print()
    print("--- 4. quem baixa devolve caminho, data e @ ---")
    # A ordem endereço > dados do vídeo > digitado só existe se as funções de
    # download entregarem o @ junto. Conferido lendo o código, sem chamar o
    # Instagram: uma delas voltar a devolver duas coisas faria o programa
    # quebrar só na hora de um download de verdade.
    import ast
    import inspect
    import textwrap

    # baixar_post_instaloader entrou em 02/09/2026, para post de FEED com foto,
    # que o yt-dlp não devolve ("No video formats found"). Ela devolve LISTA de
    # caminhos no primeiro item, por causa de carrossel.
    #
    # PASSOU DE TRÊS PARA QUATRO EM 11/09/2026, e o quarto é a HORA do post.
    # Ela já chegava do Instagram e era jogada fora por um `.date()`, e é o que
    # preenche a coluna Horário do Calendário de Divulgações. A regra que esta
    # seção guarda não mudou: toda saída devolve o MESMO tanto de coisas, senão
    # o desempacotamento de quem chama quebra só na hora de um download real.
    ESPERADO = 4
    for nome in ("_extrair_e_baixar_story", "baixar_story_instaloader",
                 "baixar_post_instaloader"):
        fonte = textwrap.dedent(inspect.getsource(getattr(fluxo, nome)))
        devolucoes = [
            no.value for no in ast.walk(ast.parse(fonte))
            if isinstance(no, ast.Return) and no.value is not None
        ]
        conferir(devolucoes and all(isinstance(v, ast.Tuple)
                                    and len(v.elts) == ESPERADO
                                    for v in devolucoes),
                 f"{nome} devolve as {ESPERADO} coisas em todo caminho de saída",
                 f"{len(devolucoes)} devolução(ões)")

    fonte_fila = textwrap.dedent(inspect.getsource(fluxo.processar_fila))
    # LÊ A ESTRUTURA, E NÃO O NOME DA VARIÁVEL (corrigido em 02/09/2026).
    #
    # Antes exigia o texto exato "caminho, data_video, handle_do_video =
    # baixar_video". A variável passou a se chamar outra coisa quando o download
    # ganhou a possibilidade de devolver vários arquivos, e o teste falhou sem
    # que nada tivesse quebrado: ele estava guardando o nome, não a regra.
    desempacotamentos = [
        no for no in ast.walk(ast.parse(fonte_fila))
        if isinstance(no, ast.Assign)
        and isinstance(no.value, ast.Call)
        and getattr(no.value.func, "id", "") == "baixar_video"
    ]
    conferir(len(desempacotamentos) == 1,
             "processar_fila chama baixar_video num lugar só",
             f"{len(desempacotamentos)} chamada(s)")
    conferir(desempacotamentos
             and isinstance(desempacotamentos[0].targets[0], ast.Tuple)
             and len(desempacotamentos[0].targets[0].elts) == ESPERADO,
             f"quem chama recebe as {ESPERADO}",
             "o @ que vem com o vídeo se perde se a chamada voltar a receber duas")
    conferir("handle_do_endereco or handle_do_video or" in fonte_fila
             or ("handle_do_endereco" in fonte_fila and "handle_do_video" in fonte_fila),
             "e usa o do endereço antes do que veio com o vídeo")


if __name__ == "__main__":
    print("=" * 72)
    print("  De onde sai o @ que vira nome de pasta")
    print("=" * 72)
    print()
    rodar()
    print()
    print("=" * 72)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 72)
    sys.exit(1 if falhas else 0)
