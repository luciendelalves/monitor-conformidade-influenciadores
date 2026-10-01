# -*- coding: utf-8 -*-
"""
Perfil que o programa ja conhece nao gasta a chamada mais limitada.

POR QUE ESTE TESTE EXISTE (07/09/2026)

Descobrir o numero interno de um perfil passa pelo endereco que o Instagram
limita com mais rigor. E a chamada mais cara do programa, a que ficou travada
por horas em 25/08/2026, e por isso existe o mapa de perfis: descobriu uma vez,
nao descobre de novo.

O mapa era consultado so quando o endereco trazia o @ no caminho. No formato
curto, instagram.com/p/CODIGO, que e justamente o que o botao de compartilhar do
Instagram gera, o @ nao esta no endereco, entao nao havia o que consultar e o
programa ia direto para a conversa autenticada.

So que a tentativa ANONIMA, que acontece antes e e de graca, costuma trazer o @
mesmo quando nao traz o numero. Com o @ em maos da para consultar o mapa, e num
perfil ja conhecido a chamada autenticada deixa de ser necessaria.

O teste NAO chama o Instagram: o yt-dlp e substituido por um duble, o mapa de
perfis e o contador vao para uma pasta temporaria.

    py testes\teste_perfil_conhecido_nao_gasta_chamada.py
"""
import json
import os
import sys
import tempfile

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


LINK_CURTO = "https://www.instagram.com/p/DcT0RkaCHbc/"
CONHECIDO = "perfilqueoprogramaconhece"
DESCONHECIDO = "perfilnuncavisto"
NUMERO_GUARDADO = 987654321


class DubleDoYtDlp:
    """Responde como o Instagram responderia, sem sair da maquina.

    ANONIMO (sem cookiefile): devolve o @ e NAO devolve o numero. E o caso real
    que motiva a correcao.
    AUTENTICADO (com cookiefile): devolve o numero."""

    construcoes = []
    handle_da_vez = CONHECIDO

    def __init__(self, opcoes):
        DubleDoYtDlp.construcoes.append(opcoes)
        self.autenticado = "cookiefile" in opcoes

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def extract_info(self, *_a, **_k):
        if self.autenticado:
            return {"channel": DubleDoYtDlp.handle_da_vez,
                    "uploader_id": "123123123"}
        return {"channel": DubleDoYtDlp.handle_da_vez, "uploader_id": ""}


def preparar(pasta):
    import fluxo_downloads as fluxo
    fluxo.ARQUIVO_ESTADO_CONTA = os.path.join(pasta, "estado_conta.json")
    # DESLIGA O CONTADOR COMPARTILHADO (24/09/2026): sem isto,
    # _contar_uso_instagram e situacao_da_conta tentariam ler/escrever de
    # verdade na planilha de fechamentos configurada NESTA máquina, porque
    # esse identificador não é isolado por pasta temporária como os outros.
    fluxo._planilha_fechamentos_id = lambda: None
    fluxo.ARQUIVO_USERIDS = os.path.join(pasta, "instagram_userids.json")
    # Cookies presentes e falsos: sem isso o caminho autenticado nem e tentado,
    # e o teste nao conseguiria distinguir os dois casos.
    fluxo.ARQUIVO_COOKIES = os.path.join(pasta, "cookies.txt")
    with open(fluxo.ARQUIVO_COOKIES, "w", encoding="utf-8") as f:
        f.write("# cookies de mentira, so para o arquivo existir\n")
    with open(fluxo.ARQUIVO_USERIDS, "w", encoding="utf-8") as f:
        json.dump({CONHECIDO: NUMERO_GUARDADO}, f)

    # O recuo pelo instaloader tambem e desligado: sem isto, um caminho lateral
    # levaria o teste a falar com o Instagram de verdade.
    def _reserva_desligada(*_a, **_k):
        raise RuntimeError("duble: reserva desligada no teste")
    fluxo._userid_e_handle_pelo_instaloader = _reserva_desligada

    import yt_dlp
    yt_dlp.YoutubeDL = DubleDoYtDlp
    return fluxo


def usados(fluxo):
    _p, _m, quantos, _r = fluxo.situacao_da_conta()
    return quantos


def rodar():
    with tempfile.TemporaryDirectory() as pasta:
        fluxo = preparar(pasta)

        print("--- 1. perfil ja conhecido: nenhuma chamada gasta ---")
        DubleDoYtDlp.handle_da_vez = CONHECIDO
        DubleDoYtDlp.construcoes = []
        antes = usados(fluxo)
        numero, handle = fluxo.userid_e_handle_por_link_de_post(LINK_CURTO)
        conferir(numero == NUMERO_GUARDADO,
                 "devolve o numero que ja estava guardado",
                 f"veio {numero}, esperado {NUMERO_GUARDADO}")
        conferir(handle == CONHECIDO, "e o @ certo", f"veio {handle}")
        conferir(usados(fluxo) == antes,
                 "e NAO gastou chamada nenhuma",
                 f"foi de {antes} para {usados(fluxo)}")
        conferir(len(DubleDoYtDlp.construcoes) == 1,
                 "so houve a tentativa anonima, que e de graca",
                 f"houve {len(DubleDoYtDlp.construcoes)}")

        print()
        print("--- 2. perfil desconhecido: o caminho antigo continua valendo ---")
        # Sem isto a correcao poderia estar apenas devolvendo qualquer coisa sem
        # nunca consultar o Instagram, e o programa deixaria de aprender perfil
        # novo.
        DubleDoYtDlp.handle_da_vez = DESCONHECIDO
        DubleDoYtDlp.construcoes = []
        antes = usados(fluxo)
        numero, handle = fluxo.userid_e_handle_por_link_de_post(LINK_CURTO)
        conferir(numero == 123123123,
                 "descobre o numero pelo caminho autenticado", f"veio {numero}")
        conferir(usados(fluxo) == antes + 1,
                 "e a chamada e contada no teto do dia",
                 f"foi de {antes} para {usados(fluxo)}")
        conferir(len(DubleDoYtDlp.construcoes) == 2,
                 "houve as duas tentativas, anonima e autenticada",
                 f"houve {len(DubleDoYtDlp.construcoes)}")

        print()
        print("--- 3. no teto, o perfil conhecido continua respondendo ---")
        # Isto e o ganho pratico da correcao: a conta no limite nao impede mais
        # o programa de trabalhar com quem ele ja conhece.
        while usados(fluxo) < fluxo.limite_diario_vigente():
            fluxo._contar_uso_instagram()
        DubleDoYtDlp.handle_da_vez = CONHECIDO
        DubleDoYtDlp.construcoes = []
        numero, handle = fluxo.userid_e_handle_por_link_de_post(LINK_CURTO)
        conferir(numero == NUMERO_GUARDADO,
                 "responde mesmo com a conta no teto", f"veio {numero}")

        print()
        print("--- 4. o mapa de perfis de verdade nao foi tocado ---")
        conferir(fluxo.ARQUIVO_USERIDS.startswith(pasta),
                 "o teste trabalhou numa pasta temporaria",
                 fluxo.ARQUIVO_USERIDS)


if __name__ == "__main__":
    print("=" * 74)
    print("  Perfil ja conhecido nao gasta a chamada mais limitada")
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
