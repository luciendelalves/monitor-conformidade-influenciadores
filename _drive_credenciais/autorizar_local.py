# -*- coding: utf-8 -*-
"""Servidor local do login OAuth, tolerante a conexão espúria na porta.

POR QUE ISSO EXISTE (16/09/2026). `InstalledAppFlow.run_local_server(port=0)`,
da própria biblioteca google-auth-oauthlib, abre um servidor local e desiste
na PRIMEIRA conexão que chegar naquela porta, seja ela a resposta de verdade
do Google ou não. Numa máquina com antivírus/EDR corporativo que sonda porta
recém-aberta (comportamento comum em notebook de empresa), essa sondagem
chega primeiro: o servidor já fecha, e quando o navegador da pessoa volta de
verdade com o código de autorização (depois dela terminar de logar e clicar
em "Permitir"), não tem mais ninguém escutando ali. O navegador mostra
"ERR_CONNECTION_REFUSED", sem erro nenhum do lado do Python além de um
`WSGITimeoutError` genérico na tentativa anterior.

Medido na instalação da Responsável A em 16/09/2026: reproduzido duas vezes
seguidas, sempre com a mesma sequência (timeout na 1ª tentativa, recusada na
2ª). A causa foi confirmada eliminando as outras hipóteses, uma por uma:
proxy do Windows sem configuração manual, aviso do Firewall nunca aparece
(nada pra ela aceitar), e a página do Google carrega normal.

A DIFERENÇA AQUI: o servidor continua escutando na mesma porta até receber
uma conexão que realmente tenha `code=` ou `error=` na URL (a resposta do
Google), ignorando qualquer outra coisa que bater ali antes disso. Um teto de
espera total evita travar para sempre se a pessoa fechar a aba sem terminar.
"""
import http.server
import time
import urllib.parse
import webbrowser


class WSGITimeoutError(RuntimeError):
    pass


class _ManipuladorDoRetorno(http.server.BaseHTTPRequestHandler):
    """Um GET por vez. Só marca `capturada["url"]` quando a query tem `code`
    ou `error` de verdade; qualquer outra coisa (sondagem, favicon, etc.) leva
    uma resposta vazia e o servidor continua esperando."""

    def log_message(self, *args):  # o log padrão poluiria o console da pessoa
        pass

    def do_GET(self):
        query = urllib.parse.urlsplit(self.path).query
        campos = urllib.parse.parse_qs(query)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if "code" in campos or "error" in campos:
            # "https", NÃO "http" (16/09/2026, achado na 2ª rodada da Responsável A):
            # o oauthlib recusa processar resposta de OAuth2 que não seja
            # https (InsecureTransportError), mesmo sendo localhost. O
            # run_local_server original da biblioteca faz essa mesma troca
            # antes de repassar pro fetch_token; a URL nunca é usada pra
            # abrir conexão de verdade, só pro oauthlib ler os parâmetros.
            self.server.capturada["url"] = (
                f"https://localhost:{self.server.server_port}{self.path}")
            self.wfile.write(
                "<html><body><p>Autorização recebida. Pode fechar "
                "esta aba e voltar para o Prompt de Comando.</p>"
                "</body></html>".encode("utf-8"))
        else:
            self.wfile.write(b"")


def autorizar(flow, minutos_de_espera=5, abrir_navegador=True):
    """Completa o fluxo OAuth do `flow` (InstalledAppFlow) usando um servidor
    local tolerante a conexão espúria. Devolve `flow.credentials`.

    `abrir_navegador=False` existe só para teste: injeta a resposta na porta
    certa por conta própria, sem depender de navegador nenhum.
    """
    httpd = http.server.HTTPServer(("localhost", 0), _ManipuladorDoRetorno)
    httpd.capturada = {}
    porta = httpd.server_port

    flow.redirect_uri = f"http://localhost:{porta}/"
    url_autorizacao, _ = flow.authorization_url()

    print(f"Please visit this URL to authorize this application: {url_autorizacao}")
    if abrir_navegador:
        try:
            webbrowser.open(url_autorizacao, new=1, autoraise=True)
        except Exception:
            pass

    # handle_request devolve o controle a cada 2s mesmo sem ninguém conectar,
    # pra dar chance do laço checar o teto de espera total.
    httpd.timeout = 2
    fim = time.monotonic() + minutos_de_espera * 60
    while "url" not in httpd.capturada and time.monotonic() < fim:
        httpd.handle_request()
    httpd.server_close()

    if "url" not in httpd.capturada:
        raise WSGITimeoutError(
            f"Não recebi a resposta do Google em {minutos_de_espera} minutos. "
            "Confirme que completou o login e clicou em Permitir na aba que "
            "abriu, e tente de novo.")

    flow.fetch_token(authorization_response=httpd.capturada["url"])
    return flow.credentials
