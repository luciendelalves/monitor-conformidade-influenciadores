# -*- coding: utf-8 -*-
"""
Prova que as rodadas se repetem sozinhas, e que a pausa não acontece à toa.

POR QUE ESTE TESTE EXISTE (01/09/2026)

Duas coisas nasceram do uso real em 31/08, e as duas mexem no mesmo trecho:

  1. o auditor mandou 4 links, o programa processou 3 e ESPEROU UM NOVO CLIQUE.
     Ele pediu primeiro subir o limite por rodada de 3 para 5, e desistiu ao ver
     que 5 resolve o caso de 4 e volta a pedir clique a partir de 6
  2. com UM link só na fila, o programa pausou 125 segundos "antes do próximo
     link" que não existia. A tarefa ficou parada dois minutos e a análise, que
     só é enfileirada no fim, atrasou esse tempo inteiro

O RISCO QUE ESTE TESTE PROTEGE, e é o que faria a mudança piorar tudo: se as
rodadas se encadearem SEM pausa entre elas, o resultado é uma rajada de 6
chamadas seguidas com espaçamento curto, pior do que simplesmente subir o limite
para 5. Por isso o teste mede as pausas, e não só o número de downloads.

Nada aqui fala com o Instagram, com o Google ou com o disco de verdade: a fila, o
download, o envio ao Drive e a planilha são todos dublês. O que está sob teste é
a decisão de quando processar e quando esperar.

    py testes\teste_rodadas_seguidas.py
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
    """Um mundo de mentira para processar_fila rodar dentro.

    Guarda o que aconteceu: quais links foram baixados, em que ordem, e quanto
    o programa quis esperar em cada momento."""

    def __init__(self, quantos_links, conta_para_de_poder_apos=None):
        self.linhas = [
            {"numero_linha": 10 + i,
             "link": f"https://www.instagram.com/stories/exemplo/{1000 + i}/",
             "influenciador": "exemplo", "status": "", "ciclo": "", "marca": "LOTTU"}
            for i in range(quantos_links)
        ]
        self.baixados = []
        self.esperas = []          # (segundos, motivo)
        self.conta_para_de_poder_apos = conta_para_de_poder_apos
        self.consultas_de_conta = 0

    # --- dublês do que fala com o mundo ---

    def ler_fila(self):
        # Devolve cópia: o programa relê a fila em cada rodada, e o que já foi
        # processado tem status e não volta.
        return [dict(l) for l in self.linhas]

    def situacao_da_conta(self):
        self.consultas_de_conta += 1
        if (self.conta_para_de_poder_apos is not None
                and len(self.baixados) >= self.conta_para_de_poder_apos):
            # A mensagem carrega o mesmo trecho que o programa usa para
            # reconhecer que a linha parou por causa da conta, e não por defeito
            # do link. Ver MARCA_DE_TETO em fluxo_downloads.
            return False, "A conta já fez o teto combinado hoje.", 20, 0
        return True, "", len(self.baixados), 20 - len(self.baixados)

    def baixar_video(self, link, pasta, post_do_perfil=None):
        # CONFERE A CONTA ANTES DE BAIXAR, igual ao programa de verdade.
        #
        # A primeira versão deste dublê não conferia, e por isso o teste esperava
        # que o laço de rodadas fosse o guardião do teto. Não é: o teto é
        # conferido dentro do caminho de download, a cada chamada. O teste
        # passava a mentir sobre onde a proteção mora.
        pode, motivo, _u, _r = self.situacao_da_conta()
        if not pode:
            raise RuntimeError(motivo)
        self.baixados.append(link)
        # Marca a linha como feita, igual à planilha de verdade.
        for l in self.linhas:
            if l["link"] == link:
                l["status"] = "BAIXADO E ORGANIZADO"
        import datetime
        return "arquivo.mp4", datetime.date(2026, 9, 1), "exemplo", None

    def enviar_para_drive(self, *a, **kw):
        return "https://drive.google.com/file/d/exemplo/view", "Ciclo 9"

    def dormir(self, segundos):
        self.esperas.append(segundos)


def rodar_cenario(quantos_links, conta_para_de_poder_apos=None, limite_rodada=3,
                  maximo_rodadas=12):
    import fluxo_downloads as fluxo

    cen = Cenario(quantos_links, conta_para_de_poder_apos)
    guardado = {}

    def trocar(nome, valor):
        guardado[nome] = getattr(fluxo, nome)
        setattr(fluxo, nome, valor)

    class SheetsFalso:
        @staticmethod
        def escrever_lote(*a, **kw):
            pass

    class TempDirFalso:
        def __enter__(self):
            return "pasta_de_mentira"

        def __exit__(self, *e):
            return False

    dormir_original = time.sleep
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
        trocar("MAXIMO_RODADAS_SEGUIDAS", maximo_rodadas)

        # O módulo importa sheets_client e tempfile DENTRO da função, então o
        # jeito de substituir é pelo sys.modules.
        import types
        falso_sheets = types.ModuleType("sheets_client")
        falso_sheets.escrever_lote = SheetsFalso.escrever_lote
        antigo_sheets = sys.modules.get("sheets_client")
        sys.modules["sheets_client"] = falso_sheets

        falso_tempfile = types.ModuleType("tempfile")
        falso_tempfile.TemporaryDirectory = TempDirFalso
        falso_tempfile.mkdtemp = lambda *a, **kw: "pasta_de_mentira"
        antigo_tempfile = sys.modules.get("tempfile")
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

    print("--- 1. UM link: baixa e NÃO espera por um próximo que não existe ---")
    cen = rodar_cenario(1)
    conferir(len(cen.baixados) == 1, "baixou o único link", str(len(cen.baixados)))
    conferir(cen.esperas == [],
             "e não esperou nada",
             f"esperou {cen.esperas} — era o defeito de 31/08, 125s à toa")

    print()
    print("--- 2. TRÊS links: duas pausas curtas, nenhuma no fim ---")
    cen = rodar_cenario(3)
    conferir(len(cen.baixados) == 3, "baixou os três", str(len(cen.baixados)))
    conferir(len(cen.esperas) == 2,
             "esperou DUAS vezes, e não três", str(cen.esperas))
    conferir(all(curta_min <= e <= curta_max for e in cen.esperas),
             "e as duas foram pausas curtas, entre links", str(cen.esperas))

    print()
    print("--- 3. QUATRO links: continua sozinho, sem pedir clique ---")
    # É o caso exato que o auditor encontrou em 31/08.
    cen = rodar_cenario(4)
    conferir(len(cen.baixados) == 4,
             "baixou TODOS os quatro, em duas rodadas",
             f"baixou {len(cen.baixados)} — antes paravam 3 e pediam clique")

    longas = [e for e in cen.esperas if e >= longa_min]
    curtas = [e for e in cen.esperas if e < longa_min]
    conferir(len(longas) == 1,
             "houve UMA pausa maior, entre as duas rodadas", str(cen.esperas))
    conferir(len(curtas) == 2,
             "e duas pausas curtas, entre os links da primeira rodada",
             str(curtas))
    conferir(any("Rodada 2" in m for m in cen.mensagens),
             "e o registro diz que houve uma segunda rodada",
             str([m for m in cen.mensagens if "Rodada" in m]))

    print()
    print("--- 4. o encadeamento NÃO vira rajada ---")
    # Este é o ponto que faria a mudança piorar tudo. Entre o último link de uma
    # rodada e o primeiro da seguinte tem que haver a pausa MAIOR.
    conferir(cen.esperas[-1] >= longa_min,
             "a última espera antes da rodada nova é a pausa maior",
             f"{cen.esperas} — se fosse curta, seriam 6 chamadas em rajada")
    conferir(cen.esperas[-1] >= curta_max,
             "e ela é maior que a maior pausa entre links",
             f"{cen.esperas[-1]:.0f}s contra {curta_max}s")

    print()
    print("--- 5. SETE links: três rodadas, todas atendidas ---")
    cen = rodar_cenario(7)
    conferir(len(cen.baixados) == 7, "baixou os sete", str(len(cen.baixados)))
    longas = [e for e in cen.esperas if e >= longa_min]
    conferir(len(longas) == 2,
             "com duas pausas maiores, uma entre cada par de rodadas",
             str(cen.esperas))

    print()
    print("--- 6. quando o teto do dia acaba, para e DIZ por quê ---")
    cen = rodar_cenario(9, conta_para_de_poder_apos=4)
    conferir(len(cen.baixados) == 4,
             "baixou só o que a conta permitia, e o teto é conferido a cada "
             "download, dentro do caminho de download",
             str(len(cen.baixados)))
    conferir(any("ficam para depois" in m for m in cen.mensagens),
             "e o laço de rodadas para, dizendo que o resto fica para depois",
             str([m for m in cen.mensagens if "depois" in m])[:160])
    conferir(any("teto" in m.lower() for m in cen.mensagens),
             "citando o motivo, que é o teto",
             str([m for m in cen.mensagens if "teto" in m.lower()])[:160])

    # A LINHA BARRADA PELO TETO VOLTA SOZINHA, e isto era um defeito até
    # 01/09/2026: a detecção reconhecia a pausa por bloqueio e não o teto, então
    # a linha virava FALHA permanente e não voltava no dia seguinte, quando o
    # contador zera.
    import fluxo_downloads as f
    conferir(f.MARCA_DE_TETO in "A conta já fez o teto combinado hoje.",
             "a marca do teto está na mensagem que a conta devolve",
             f.MARCA_DE_TETO)
    fonte = open(os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8").read()
    conferir("MARCA_DE_TETO in str(e)" in fonte,
             "e a linha barrada pelo teto é marcada como espera, não como falha",
             "sem isso ela não voltaria sozinha quando o contador zerar")

    print()
    print("--- 7. a rede de segurança das rodadas existe ---")
    cen = rodar_cenario(30, maximo_rodadas=2)
    conferir(len(cen.baixados) == 6,
             "com o máximo em 2 rodadas, baixou 6 e parou", str(len(cen.baixados)))
    conferir(any("rodadas seguidas" in m for m in cen.mensagens),
             "e avisou que parou por segurança, em vez de parar calado",
             str([m for m in cen.mensagens if "rodadas" in m])[:160])
    conferir(any("mande de" in m for m in cen.mensagens),
             "dizendo o que fazer para continuar")

    print()
    print("--- 8. fila vazia não faz nada ---")
    cen = rodar_cenario(0)
    conferir(cen.baixados == [], "não baixou nada")
    conferir(cen.esperas == [], "e não esperou nada")

    print()
    print("--- 9. de onde veio o ciclo fica registrado ---")
    # Pedido do auditor em 01/09/2026, junto com o campo de ciclo na primeira
    # seção da tela: ciclo escolhido por uma pessoa é discricionariedade, e a
    # ferramenta existe para deixar discricionariedade rastreável. Até aqui,
    # ciclo digitado e ciclo tirado da data ficavam iguais na planilha.
    conferir("origem_ciclo" in fluxo.CAMPOS_LOG,
             "o registro do fluxo tem coluna para a origem do ciclo",
             str(fluxo.CAMPOS_LOG))
    # O QUE IMPORTA É NÃO DESLOCAR AS COLUNAS ANTIGAS, e não ser literalmente a
    # última. A primeira versão exigia CAMPOS_LOG[-1] == "origem_ciclo", e isso
    # falhou em 02/09/2026 quando o campo `quem` entrou depois dela. O campo novo
    # também foi para o fim, então a regra foi respeitada; era o teste que estava
    # exigindo mais do que a regra.
    ORIGINAIS = ["quando", "estagio", "origem", "handle", "data_video", "ciclo",
                 "destino", "status"]
    conferir(fluxo.CAMPOS_LOG[:len(ORIGINAIS)] == ORIGINAIS,
             "os campos antigos continuam na mesma ordem, do começo",
             str(fluxo.CAMPOS_LOG[:len(ORIGINAIS)]))
    conferir(fluxo.CAMPOS_LOG.index("origem_ciclo") >= len(ORIGINAIS),
             "e a origem do ciclo entrou DEPOIS deles, sem deslocar nada",
             str(fluxo.CAMPOS_LOG))

    fonte = open(os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8").read()
    conferir("origem_ciclo=origem_do_ciclo" in fonte,
             "o processamento grava a origem junto com a linha do registro")
    conferir('"digitado" if ciclo_manual else "pela data do vídeo"' in fonte,
             "distinguindo digitado de calculado pela data")

    # A migração do cabeçalho precisa existir, senão a coluna nova desalinha a
    # leitura do arquivo que já está no disco.
    conferir("_migrar_cabecalho_do_log" in fonte,
             "e existe migração do cabeçalho do arquivo antigo",
             "sem isso a leitura por nome de coluna quebraria")

    # Prova a migração de verdade, com um arquivo no formato antigo.
    import csv as csv_
    import tempfile as tempfile_
    pasta = tempfile_.mkdtemp(prefix="log_antigo_")
    caminho = os.path.join(pasta, "log_fluxo_completo.csv")
    antigos = ["quando", "estagio", "origem", "handle", "data_video", "ciclo",
               "destino", "status"]
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv_.DictWriter(f, fieldnames=antigos)
        w.writeheader()
        w.writerow({c: f"valor_{c}" for c in antigos})

    guardado = fluxo.ARQUIVO_LOG
    try:
        fluxo.ARQUIVO_LOG = caminho
        fluxo.gravar_log([dict(quando="agora", estagio="A", origem="link",
                               handle="exemplo", data_video="", ciclo="Ciclo 9",
                               destino="", status="OK", origem_ciclo="digitado")])
        lidas = fluxo.ler_log()
        conferir(len(lidas) == 2, "a linha antiga sobreviveu à migração", str(len(lidas)))
        conferir(lidas[0].get("ciclo") == "valor_ciclo",
                 "com os valores dela no lugar certo", str(lidas[0])[:120])
        conferir(lidas[0].get("origem_ciclo") == "",
                 "e a coluna nova vazia na linha antiga, que é honesto",
                 str(lidas[0].get("origem_ciclo")))
        conferir(lidas[1].get("origem_ciclo") == "digitado",
                 "e preenchida na linha nova", str(lidas[1].get("origem_ciclo")))
    finally:
        fluxo.ARQUIVO_LOG = guardado


if __name__ == "__main__":
    print("=" * 74)
    print("  Rodadas seguidas, e a pausa no lugar certo")
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
