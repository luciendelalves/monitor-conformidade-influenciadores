# -*- coding: utf-8 -*-
"""
O servidor local de login OAuth aguenta sondagem espúria na porta.

POR QUE ESTE TESTE EXISTE

Achado na instalação da Responsável A em 16/09/2026:
`InstalledAppFlow.run_local_server(port=0)`, da biblioteca, desiste na
PRIMEIRA conexão que chegar na porta local, seja ela a resposta de verdade do
Google ou não. Numa máquina com antivírus/EDR corporativo que sonda porta
recém-aberta, essa sondagem chega primeiro, o servidor fecha, e quando o
navegador volta de verdade com o código, a porta já não existe mais
(`ERR_CONNECTION_REFUSED`). `_drive_credenciais/autorizar_local.py` resolve
isso continuando a escutar até uma conexão com `code=`/`error=` na query.

Este teste não abre navegador nem fala com o Google: injeta as conexões
numa thread, como se fossem chegando na porta.

Rodar:

    py testes\\teste_autorizacao_local_tolerante.py
"""
import os
import sys
import threading
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "_drive_credenciais"))

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


class FlowFalso:
    """Substitui o InstalledAppFlow real: guarda o redirect_uri que
    autorizar() define, devolve uma URL qualquer, e finge trocar o código
    pelo token sem falar com o Google de verdade."""

    def __init__(self):
        self.redirect_uri = None
        self.respondido_com = None

    def authorization_url(self):
        return f"https://exemplo-google-falso/authorize?redirect_uri={self.redirect_uri}", "state"

    def fetch_token(self, authorization_response):
        self.respondido_com = authorization_response
        self.credentials = "credencial-falsa"  # o Flow real expõe isso depois


def rodar():
    import autorizar_local as al

    print("--- 1. sondagem sem code/error é ignorada, servidor continua esperando ---")
    flow = FlowFalso()
    resultado = {}

    def chamar_autorizar():
        try:
            al.autorizar(flow, minutos_de_espera=1, abrir_navegador=False)
            resultado["ok"] = True
        except Exception as e:
            resultado["erro"] = e

    t = threading.Thread(target=chamar_autorizar, daemon=True)
    t.start()

    # Espera o servidor abrir e publicar a porta no redirect_uri do flow
    # falso (autorizar() grava isso antes de qualquer coisa).
    fim_espera = time.monotonic() + 5
    while flow.redirect_uri is None and time.monotonic() < fim_espera:
        time.sleep(0.05)
    conferir(flow.redirect_uri is not None,
             "o servidor local publica o redirect_uri antes de esperar",
             "nunca chegou a definir flow.redirect_uri")

    if flow.redirect_uri:
        base = flow.redirect_uri
        # SONDAGEM: um GET sem code nem error, como um antivírus tocando a
        # porta recém-aberta faria.
        urllib.request.urlopen(base, timeout=3).read()
        # A THREAD PRECISA CONTINUAR VIVA depois da sondagem: é exatamente
        # isso que a biblioteca original não fazia.
        time.sleep(0.3)
        conferir(t.is_alive(),
                 "depois da sondagem sem code/error, o servidor CONTINUA de pé",
                 "a thread já tinha terminado, como no bug original")

        # RESPOSTA DE VERDADE, chegando depois: tem que ser aceita.
        urllib.request.urlopen(base + "?code=abc123&state=state", timeout=3).read()
        t.join(timeout=5)
        conferir(not t.is_alive(), "termina assim que a resposta de verdade chega",
                 "ainda estava rodando depois do code chegar")
        conferir(resultado.get("ok") is True,
                 "autorizar() retorna sem erro quando o code chega depois da sondagem",
                 str(resultado.get("erro")))
        conferir(flow.respondido_com is not None and "code=abc123" in flow.respondido_com,
                 "o fetch_token recebe a URL com o code de verdade, não a da sondagem",
                 str(flow.respondido_com))
        # ESQUEMA TEM QUE SER https, NUNCA http (achado na 2ª rodada da
        # Responsável A, 16/09/2026): o oauthlib recusa processar authorization_
        # response que não seja https, mesmo em localhost
        # (InsecureTransportError). O FlowFalso não chama o oauthlib de
        # verdade, então só essa checagem de string pega a regressão.
        conferir(str(flow.respondido_com).startswith("https://"),
                 "a URL passada pro fetch_token começa com https, não http",
                 str(flow.respondido_com))

    print()
    print("--- 2. sem nenhuma resposta, desiste no teto de espera, com mensagem clara ---")
    flow2 = FlowFalso()
    inicio = time.monotonic()
    try:
        al.autorizar(flow2, minutos_de_espera=0.02, abrir_navegador=False)  # ~1,2s
        conferir(False, "deveria ter estourado o teto de espera", "não levantou nada")
    except al.WSGITimeoutError as e:
        duracao = time.monotonic() - inicio
        conferir(duracao < 10, "desiste em tempo razoável, não trava para sempre",
                 f"levou {duracao:.1f}s")
        conferir("Permitir" in str(e) or "tente" in str(e).lower(),
                 "a mensagem explica o que fazer, não só que deu erro",
                 str(e))


if __name__ == "__main__":
    print("=" * 74)
    print("  Servidor local de login: tolerante a sondagem na porta")
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
