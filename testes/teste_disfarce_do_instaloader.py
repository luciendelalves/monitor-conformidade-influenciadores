# -*- coding: utf-8 -*-
"""O instaloader também precisa chegar com cara de navegador.

POR QUE ESTE TESTE EXISTE (22/09/2026)

Até esta data o disfarce valia só para o yt-dlp. O instaloader, que é quem
busca Story e quem descobre o número interno do perfil, os dois endereços que
o Instagram vigia com mais rigor, falava por uma biblioteca de Python comum. E
a diferença aparece ANTES do HTTP: a forma como a conexão segura é aberta já
denuncia Python, e nenhum cabeçalho conserta isso.

A troca da sessão exige um adaptador, porque a biblioteca do disfarce entrega
os cookies em formato diferente do que o instaloader espera: ele percorre a
lista procurando o cookie de nome "csrftoken", e do outro lado vem só o nome,
em texto. Foi assim que a primeira tentativa quebrou, com AttributeError.

O QUE ESTE TESTE GUARDA, e é o que custa caro se voltar:
1. o adaptador entrega cookie com nome e valor, do jeito que o instaloader lê;
2. quando a rede recusa por certificado, a chamada repete pela sessão de
   sempre em vez de falhar, porque nessa recusa a chamada nem chegou ao
   Instagram (medido em 22/09: o mesmo endereço recusou numa chamada e passou
   na seguinte, é intermitente);
3. erro que NÃO é de certificado não recua, senão uma recusa do Instagram
   viraria uma segunda chamada, que é exatamente o que marcou duas contas em
   agosto de 2026;
4. o navegador vai declarado mesmo com o disfarce desligado.

Não fala com a rede: as duas sessões são dublês.

Rodar:

    py testes\\teste_disfarce_do_instaloader.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import fluxo_downloads as fd

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


class _CookiesDeMentira:
    def __init__(self, valores):
        self._valores = valores

    def get_dict(self):
        return dict(self._valores)


class _SessaoDeMentira:
    """Dublê de sessão. Anota o que foi chamado e pode falhar sob encomenda."""

    def __init__(self, nome, erro=None):
        self.nome = nome
        self.erro = erro
        self.chamadas = []
        self.cookies = _CookiesDeMentira({"csrftoken": "abc", "sessionid": "xyz"})
        self.headers = {}

    def get(self, endereco, **kwargs):
        self.chamadas.append(endereco)
        if self.erro:
            raise self.erro
        return f"resposta de {self.nome}"

    def post(self, endereco, **kwargs):
        return self.get(endereco, **kwargs)


class _ErroDeCertificado(Exception):
    pass


def rodar():
    guardado = fd._disfarce_funciona
    try:
        print("--- 1. o adaptador entrega cookie do jeito que o instaloader lê ---")
        adaptados = list(fd._CookiesParaInstaloader(
            _CookiesDeMentira({"csrftoken": "abc", "sessionid": "xyz"})))
        conferir(len(adaptados) == 2, "vieram os dois cookies", str(len(adaptados)))
        csrf = next((c for c in adaptados if c.name == "csrftoken"), None)
        conferir(csrf is not None, "dá pra achar o csrftoken pelo nome")
        conferir(csrf is not None and csrf.value == "abc",
                 "e o valor vem junto", str(getattr(csrf, "value", None)))

        print()
        print("--- 2. com disfarce de pé, quem atende é a sessão disfarçada ---")
        fd._disfarce_funciona = None
        disfarcada = _SessaoDeMentira("disfarcada")
        reserva = _SessaoDeMentira("reserva")
        sessao = fd._SessaoComDisfarce(disfarcada, reserva)
        resposta = sessao.get("https://www.instagram.com/qualquer")
        conferir(resposta == "resposta de disfarcada", "a chamada foi pela disfarçada", resposta)
        conferir(reserva.chamadas == [], "e a de reserva nem foi tocada", str(reserva.chamadas))
        conferir(any(c.name == "csrftoken" for c in sessao.cookies),
                 "os cookies saem adaptados enquanto o disfarce vale")

        print()
        print("--- 3. recusa por certificado repete pela sessão de sempre ---")
        fd._disfarce_funciona = None
        erro = _ErroDeCertificado("curl: (60) SSL certificate problem")
        conferir(fd.e_problema_de_certificado(erro),
                 "o erro do teste é reconhecido como de certificado")
        disfarcada = _SessaoDeMentira("disfarcada", erro=erro)
        reserva = _SessaoDeMentira("reserva")
        sessao = fd._SessaoComDisfarce(disfarcada, reserva)
        resposta = sessao.get("https://www.instagram.com/qualquer")
        conferir(resposta == "resposta de reserva",
                 "a resposta veio da sessão de sempre, sem estourar erro", str(resposta))
        conferir(fd._disfarce_funciona is False,
                 "e o disfarce ficou desligado até reiniciar")
        reserva.chamadas = []
        disfarcada.chamadas = []
        sessao.get("https://www.instagram.com/outra")
        conferir(disfarcada.chamadas == [],
                 "a próxima chamada nem tenta a disfarçada de novo", str(disfarcada.chamadas))
        conferir(len(reserva.chamadas) == 1, "vai direto pela de sempre", str(reserva.chamadas))

        print()
        print("--- 4. erro que não é de certificado NÃO vira segunda chamada ---")
        fd._disfarce_funciona = None
        recusa = RuntimeError("401 Unauthorized - please wait a few minutes")
        conferir(not fd.e_problema_de_certificado(recusa),
                 "recusa do Instagram não é confundida com certificado")
        disfarcada = _SessaoDeMentira("disfarcada", erro=recusa)
        reserva = _SessaoDeMentira("reserva")
        sessao = fd._SessaoComDisfarce(disfarcada, reserva)
        try:
            sessao.get("https://www.instagram.com/qualquer")
            conferir(False, "o erro do Instagram sobe em vez de ser engolido")
        except RuntimeError:
            conferir(True, "o erro do Instagram sobe em vez de ser engolido")
        conferir(reserva.chamadas == [],
                 "e NÃO gasta uma segunda chamada com o Instagram", str(reserva.chamadas))
        conferir(fd._disfarce_funciona is not False,
                 "recusa do Instagram não desliga o disfarce")

        print()
        print("--- 5. o navegador vai declarado com disfarce e sem ---")
        fd._disfarce_funciona = None
        com = fd.opcoes_de_disfarce()
        conferir(com.get("http_headers", {}).get("User-Agent") == fd.IDENTIFICACAO_DO_NAVEGADOR,
                 "com disfarce, o navegador vai nos cabeçalhos", str(com.get("http_headers")))
        fd._disfarce_funciona = False
        sem = fd.opcoes_de_disfarce()
        conferir(sem.get("http_headers", {}).get("User-Agent") == fd.IDENTIFICACAO_DO_NAVEGADOR,
                 "sem disfarce também, e é aí que importa", str(sem.get("http_headers")))
        conferir("impersonate" not in sem,
                 "e o disfarce desligado não volta sozinho", str(sem.keys()))

        print()
        print("--- 6. os três caminhos contam a mesma história ---")
        conferir(fd.PERFIL_DE_DISFARCE == "firefox",
                 "o perfil do disfarce é Firefox", fd.PERFIL_DE_DISFARCE)
        conferir("Firefox" in fd.IDENTIFICACAO_DO_NAVEGADOR,
                 "e o que vai escrito também", fd.IDENTIFICACAO_DO_NAVEGADOR)
        # Esta é a conferência que importa se alguém trocar o navegador dos
        # cookies: o programa passaria a mandar sessão de um navegador dizendo
        # ser outro, que é justamente o que se corrigiu em 22/09/2026.
        conferir(fd.NAVEGADOR_COOKIES == "firefox",
                 "igual ao navegador de onde vêm os cookies", fd.NAVEGADOR_COOKIES)

        print()
        print("--- 7. numa máquina Windows, diz o Firefox DELA ---")
        versao = fd._versao_do_firefox_instalado()
        if os.name == "nt" and versao:
            conferir("Windows" in fd.IDENTIFICACAO_DO_NAVEGADOR,
                     "diz Windows, e não macOS como o perfil da biblioteca",
                     fd.IDENTIFICACAO_DO_NAVEGADOR)
            conferir(f"Firefox/{versao}.0" in fd.IDENTIFICACAO_DO_NAVEGADOR,
                     f"e a versão é a instalada aqui ({versao})",
                     fd.IDENTIFICACAO_DO_NAVEGADOR)
        else:
            conferir(fd.IDENTIFICACAO_DO_NAVEGADOR == fd.IDENTIFICACAO_DO_DISFARCE,
                     "sem Firefox instalado, cai no texto medido do perfil",
                     fd.IDENTIFICACAO_DO_NAVEGADOR)

        print()
        print("--- 8. se a troca não der, o programa segue sem ela ---")
        fd._disfarce_funciona = None

        class _ContextoQuebrado:
            @property
            def _session(self):
                raise RuntimeError("o instaloader mudou de forma")

        class _InstaloaderQuebrado:
            context = _ContextoQuebrado()

        conferir(fd.disfarcar_sessao_do_instaloader(_InstaloaderQuebrado()) is False,
                 "devolve False em vez de derrubar o download")
    finally:
        fd._disfarce_funciona = guardado


if __name__ == "__main__":
    print("=" * 74)
    print("  Disfarce de navegador no instaloader")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
