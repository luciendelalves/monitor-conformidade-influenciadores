# -*- coding: utf-8 -*-
"""
Prova que link colado DEPOIS do primeiro não espera a pausa de rodada inteira.

POR QUE ESTE TESTE EXISTE (11/09/2026)

O jeito real de trabalhar do auditor, descrito por ele: "quando o usuário tem
dois vídeos de stories, eu coloco o link pra baixar e logo após eu coloco outro
link, o que eu estou dizendo que tá demorando é esse intervalo entre um video
baixar depois do primeiro".

O QUE ACONTECIA ATÉ AQUI: o segundo link chega depois de a rodada já ter lido a
fila, então ele não entra na rodada do primeiro. No fim da rodada o programa
relê a fila, acha o link novo (ver o comentário de RELÊ A FILA ANTES DE
DESISTIR, 06/09/2026) e aplicava a PAUSA DE RODADA, de 180 a 420 segundos. O
auditor esperava cerca de 5 minutos pelo segundo story. O print que ele mandou
mostrava 369s.

POR QUE A PAUSA DE RODADA NÃO SERVE NESTE CASO, e é o raciocínio que autoriza a
mudança: a pausa maior existe para conter RAJADA, o caso em que a rodada bateu o
limite de 3 links e a seguinte encadearia mais 3 (ver PAUSA_ENTRE_RODADAS_*).
Quando a rodada fez UMA chamada e chegou UM link novo, não há rajada nenhuma a
conter: o ritmo de continuar após a pausa curta é idêntico ao de quem colou os
dois links juntos, que é o ritmo já aceito hoje.

O QUE ESTE TESTE PROTEGE, nos dois sentidos:

  - link que chega no meio continua com a pausa CURTA (entre links)
  - rodada que bateu o LIMITE continua com a pausa MAIOR, intacta. Esta é a
    proteção que nasceu do 429 de 25/08/2026 e não pode ser afrouxada por
    tabela

Nada aqui fala com o Instagram, com o Google ou com o disco: fila, download,
Drive e planilha são dublês. O que está sob teste é a decisão de quanto esperar.

    py testes\\teste_link_que_chega_no_meio.py
"""
import os
import sys
import time

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


class Cenario:
    """Mundo de mentira para processar_fila rodar dentro.

    `chegam_no_meio` é o ponto deste teste: esses links só aparecem na fila a
    partir da SEGUNDA leitura, imitando quem cola o segundo link enquanto o
    primeiro está baixando."""

    def __init__(self, quantos_no_começo, chegam_no_meio=0):
        self.linhas = [self._linha(i) for i in range(quantos_no_começo)]
        self.atrasados = [self._linha(100 + i) for i in range(chegam_no_meio)]
        self.leituras = 0
        self.baixados = []
        self.esperas = []

    @staticmethod
    def _linha(i):
        return {"numero_linha": 10 + i,
                "link": f"https://www.instagram.com/stories/exemplo/{1000 + i}/",
                "influenciador": "exemplo", "status": "", "ciclo": "",
                "marca": "LOTTU"}

    # --- dublês ---

    def ler_fila(self):
        self.leituras += 1
        if self.leituras >= 2 and self.atrasados:
            # Entra na fila de verdade, e fica: quem colou o link não o remove.
            self.linhas.extend(self.atrasados)
            self.atrasados = []
        return [dict(l) for l in self.linhas]

    def situacao_da_conta(self):
        return True, "", len(self.baixados), 20 - len(self.baixados)

    def baixar_video(self, link, pasta, post_do_perfil=None):
        self.baixados.append(link)
        for l in self.linhas:
            if l["link"] == link:
                l["status"] = "BAIXADO E ORGANIZADO"
        import datetime
        return "arquivo.mp4", datetime.date(2026, 9, 1), "exemplo", None

    def enviar_para_drive(self, *a, **kw):
        return "https://drive.google.com/file/d/exemplo/view", "Ciclo 9"

    def dormir(self, segundos):
        self.esperas.append(segundos)


def rodar_cenario(quantos_no_começo, chegam_no_meio=0, limite_rodada=3):
    import fluxo_downloads as fluxo

    cen = Cenario(quantos_no_começo, chegam_no_meio)
    guardado = {}

    def trocar(nome, valor):
        guardado[nome] = getattr(fluxo, nome)
        setattr(fluxo, nome, valor)

    class TempDirFalso:
        def __enter__(self):
            return "pasta_de_mentira"

        def __exit__(self, *e):
            return False

    dormir_original = time.sleep
    antigo_sheets = sys.modules.get("sheets_client")
    antigo_tempfile = sys.modules.get("tempfile")
    try:
        trocar("ler_fila", cen.ler_fila)
        trocar("situacao_da_conta", cen.situacao_da_conta)
        trocar("baixar_video", cen.baixar_video)
        trocar("enviar_para_drive", cen.enviar_para_drive)
        trocar("mapa_de_posts_por_handle", lambda links: {})
        trocar("gravar_log", lambda log: None)
        trocar("enfileirar_analise", lambda *a, **kw: None)
        trocar("_planilha_fila_id", lambda: "planilha_de_mentira")
        trocar("LIMITE_INSTAGRAM_POR_RODADA", limite_rodada)

        import types
        falso_sheets = types.ModuleType("sheets_client")
        falso_sheets.escrever_lote = lambda *a, **kw: None
        sys.modules["sheets_client"] = falso_sheets

        falso_tempfile = types.ModuleType("tempfile")
        falso_tempfile.TemporaryDirectory = TempDirFalso
        falso_tempfile.mkdtemp = lambda *a, **kw: "pasta_de_mentira"
        sys.modules["tempfile"] = falso_tempfile

        time.sleep = cen.dormir

        mensagens = []
        fluxo.processar_fila(log_fn=lambda m: mensagens.append(str(m)),
                             analisar_depois=False)
        cen.mensagens = mensagens
        return cen
    finally:
        time.sleep = dormir_original
        for nome, valor in guardado.items():
            setattr(fluxo, nome, valor)
        if antigo_sheets is not None:
            sys.modules["sheets_client"] = antigo_sheets
        else:
            sys.modules.pop("sheets_client", None)
        if antigo_tempfile is not None:
            sys.modules["tempfile"] = antigo_tempfile


def rodar():
    import fluxo_downloads as fluxo

    curta_min = fluxo.PAUSA_INSTAGRAM_MIN_SEG
    curta_max = fluxo.PAUSA_INSTAGRAM_MAX_SEG
    longa_min = fluxo.PAUSA_ENTRE_RODADAS_MIN_SEG

    print(f"       pausa entre links: {curta_min} a {curta_max}s")
    print(f"       pausa entre rodadas: {longa_min} a "
          f"{fluxo.PAUSA_ENTRE_RODADAS_MAX_SEG}s")
    print()

    print("--- 1. a ordem das duas pausas continua sendo a base do desenho ---")
    # Se a pausa entre links passar a ser maior ou igual à de rodada, todo o
    # resto deste teste deixa de significar o que diz.
    conferir(curta_max < longa_min,
             "a maior pausa entre links é menor que a menor pausa de rodada",
             f"{curta_max}s contra {longa_min}s")

    print()
    print("--- 2. UM link, e outro chega enquanto ele baixa ---")
    # O caso do auditor, 11/09/2026: dois stories, colados um atrás do outro.
    cen = rodar_cenario(1, chegam_no_meio=1)
    conferir(len(cen.baixados) == 2,
             "os dois são baixados, sem precisar de novo clique",
             str(len(cen.baixados)))
    conferir(len(cen.esperas) == 1,
             "e houve UMA espera entre eles", str(cen.esperas))
    conferir(cen.esperas and cen.esperas[0] <= curta_max,
             "que é a pausa CURTA, de entre links",
             f"{cen.esperas} — pausa de rodada aqui fazia o auditor esperar "
             f"cerca de 5 minutos pelo segundo story")
    conferir(any("entraram na fila enquanto eu trabalhava" in m
                 for m in cen.mensagens),
             "o registro diz que o link chegou no meio",
             str([m for m in cen.mensagens if "fila" in m])[:200])
    conferir(not any("rajada" in m for m in cen.mensagens),
             "e NÃO justifica a espera com rajada, que não existe aqui",
             str([m for m in cen.mensagens if "rajada" in m])[:200])

    print()
    print("--- 3. rodada que bate o LIMITE continua com a pausa maior ---")
    # A proteção que nasceu do 429 de 25/08/2026. Afrouxar isto seria trocar um
    # incômodo de minutos por risco de bloqueio de conta.
    cen = rodar_cenario(4)
    conferir(len(cen.baixados) == 4, "baixou os quatro", str(len(cen.baixados)))
    longas = [e for e in cen.esperas if e >= longa_min]
    conferir(len(longas) == 1,
             "e a pausa entre as duas rodadas continua sendo a MAIOR",
             str(cen.esperas))
    conferir(any("rajada" in m for m in cen.mensagens),
             "dizendo no registro que é para não virar rajada",
             str([m for m in cen.mensagens if "rajada" in m])[:200])

    print()
    print("--- 4. limite batido E link novo no meio: ainda é a pausa maior ---")
    # Os dois casos juntos. Quando há rajada a conter, ela manda, mesmo que
    # também tenha chegado linha nova no meio.
    cen = rodar_cenario(4, chegam_no_meio=1)
    conferir(len(cen.baixados) == 5, "baixou os cinco", str(len(cen.baixados)))
    longas = [e for e in cen.esperas if e >= longa_min]
    conferir(len(longas) >= 1,
             "houve pausa maior ao menos uma vez, por causa do limite",
             str(cen.esperas))


if __name__ == "__main__":
    print("=" * 74)
    print("  Link colado depois do primeiro não espera a rodada inteira")
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
