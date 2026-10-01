# -*- coding: utf-8 -*-
"""
Prova que o download escreve no Calendário, que a marcação de "não postou"
funciona, e que nenhuma das duas derruba o resto quando falha.

POR QUE ESTE TESTE EXISTE (11/09/2026)

O Calendário de Divulgações é o SEGUNDO destino de cada download, depois da
Monitoramento. Ele é conveniência para o Marketing, não é a evidência da
auditoria. Então a regra é a mesma já usada no registro de fechamentos: se
falhar, avisa e segue. Um vídeo baixado e organizado não pode virar falha
porque uma planilha de outra área estava fora do ar.

Confere também o "Monitorado por": só escreve nome que JÁ existe naquela
coluna da planilha deles. E-mail vindo do login deixa a célula vazia, porque
a coluna deles é de apelidos (Responsável F, Responsável A, Responsável G, Responsável E).

E confere que "não postou" não fala com o Instagram: não há vídeo para baixar,
e chamada é o recurso escasso do programa.

Nada aqui fala com o Google: a leitura e a escrita do Calendário são dublês.

    py testes\\teste_calendario_no_fluxo.py
"""
import datetime
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


# Uma linha livre e um vocabulário de apelidos com Responsável A e Responsável F.
LINHAS = [
    ["giroquue", "LOTTU", "Responsável F", "", "", "11/09/2026", "", "Responsável A", ""],
]


class Dubles:
    """Troca ler_aba e escrever do módulo do Calendário, e guarda o pedido."""

    def __init__(self, linhas=None, erro_na_leitura=False):
        self.linhas = linhas if linhas is not None else LINHAS
        self.erro_na_leitura = erro_na_leitura
        self.escrito = {}
        self.aba = None
        self.linha = None

    def __enter__(self):
        import calendario_divulgacoes as cal
        self.cal = cal
        self.guardado = (cal.ler_aba, cal.escrever)
        cal.ler_aba = self._ler
        cal.escrever = self._escrever
        return self

    def __exit__(self, *e):
        self.cal.ler_aba, self.cal.escrever = self.guardado
        return False

    def _ler(self, aba):
        if self.erro_na_leitura:
            raise RuntimeError("rede fora")
        self.aba = aba
        return [list(l) for l in self.linhas]

    def _escrever(self, aba, numero, valores):
        self.aba = aba
        self.linha = numero
        self.escrito = dict(valores)
        return True, ", ".join(k for k, v in valores.items() if v)


def rodar():
    import calendario_divulgacoes as cal
    import fluxo_downloads as fluxo

    print("--- 1. o download escreve Publicada, hora, jogo e quem monitorou ---")
    with Dubles() as d:
        gravou, motivo = fluxo.registrar_no_calendario(
            handle="@Giroquue", marca="LOTTU",
            data_video=datetime.date(2026, 9, 11),
            hora_post=datetime.datetime(2026, 9, 11, 19, 7),
            jogo="Mines", quem="Responsável A")
        conferir(gravou, "gravou", motivo)
        conferir(d.aba == "SET.26", "na aba do mês do post", str(d.aba))
        conferir(d.linha == 3, "na linha que casou", str(d.linha))
        conferir(d.escrito.get("status") == cal.STATUS_PUBLICADA,
                 "com Status igual ao vocabulário deles",
                 str(d.escrito.get("status")))
        conferir(d.escrito.get("horario") == "19:07",
                 "hora em HH:MM, como está na planilha deles",
                 str(d.escrito.get("horario")))
        # SEMPRE MAIÚSCULA (15/09/2026): a entrada é "Mines", minúsculo de
        # propósito neste teste, para confirmar que a normalização acontece
        # aqui dentro e não só na tela (ver fluxo_downloads.registrar_no_calendario).
        conferir(d.escrito.get("jogo") == "MINES",
                 "e o jogo digitado na tela vira maiúscula", str(d.escrito.get("jogo")))
        conferir(d.escrito.get("monitorado") == "Responsável A",
                 "o nome de quem monitorou, que já existe na coluna deles",
                 str(d.escrito.get("monitorado")))

    print()
    print("--- 2. nome desconhecido deixa a célula vazia ---")
    with Dubles() as d:
        fluxo.registrar_no_calendario(
            handle="giroquue", marca="LOTTU",
            data_video=datetime.date(2026, 9, 11),
            hora_post=None, jogo="", quem="responsavel.e@empresa.com")
        conferir(not d.escrito.get("monitorado"),
                 "e-mail do login não vai para a coluna de apelidos",
                 str(d.escrito.get("monitorado")))
        conferir(d.escrito.get("horario") == "",
                 "e sem hora na origem, a coluna Horário fica vazia",
                 str(d.escrito.get("horario")))

    print()
    print("--- 3. falha no Calendário NÃO derruba o download ---")
    with Dubles(erro_na_leitura=True):
        gravou, motivo = fluxo.registrar_no_calendario(
            handle="giroquue", marca="LOTTU",
            data_video=datetime.date(2026, 9, 11),
            hora_post=None, jogo="", quem="Responsável A")
        conferir(gravou is False, "devolve False, sem levantar erro")
        conferir("rede fora" in motivo,
                 "e diz o motivo, para aparecer na tela", motivo)

    print()
    print("--- 4. sem data, não tenta adivinhar linha ---")
    with Dubles() as d:
        gravou, motivo = fluxo.registrar_no_calendario(
            handle="giroquue", marca="LOTTU", data_video=None,
            hora_post=None, jogo="", quem="Responsável A")
        conferir(gravou is False and "data" in motivo.lower(),
                 "explica que falta a data", motivo)
        conferir(d.linha is None, "e não escreve em lugar nenhum", str(d.linha))

    print()
    print("--- 5. 'não postou' escreve Não Postada, e mais nada ---")
    with Dubles() as d:
        gravou, motivo = fluxo.marcar_nao_postou(
            "giroquue", "LOTTU", datetime.date(2026, 9, 11), "Responsável A")
        conferir(gravou, "gravou", motivo)
        conferir(d.escrito.get("status") == cal.STATUS_NAO_POSTADA,
                 "com o vocabulário deles", str(d.escrito.get("status")))
        conferir("horario" not in d.escrito,
                 "e sem horário, porque não houve postagem", str(d.escrito))
        conferir("jogo" not in d.escrito,
                 "nem jogo, pelo mesmo motivo", str(d.escrito))

    print()
    print("--- 6. 'não postou' NÃO fala com o Instagram ---")
    import inspect
    corpo = inspect.getsource(fluxo.marcar_nao_postou)
    if '"""' in corpo:
        partes = corpo.split('"""')
        corpo = partes[0] + ("".join(partes[2:]) if len(partes) > 2 else "")
    for proibido in ("instaloader", "yt_dlp", "baixar_video", "baixar_story",
                     "_contar_uso_instagram", "resolver_userid"):
        conferir(proibido not in corpo,
                 f"não usa {proibido}",
                 "não há vídeo para baixar: gastar chamada aqui seria queimar "
                 "o recurso mais escasso do programa")

    print()
    print("--- 7. o fluxo chama o Calendário DEPOIS da Monitoramento ---")
    fonte = open(os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8").read()
    conferir("registrar_no_calendario(" in fonte, "o fluxo chama")
    # Compara a posição das CHAMADAS dentro de processar_fila, e não a do def.
    dentro = fonte.split("def processar_fila(")[1]
    conferir("enviar_para_drive(" in dentro
             and dentro.index("enviar_para_drive(")
             < dentro.index("registrar_no_calendario("),
             "o envio ao Drive e a linha da Monitoramento vêm primeiro",
             "se o Calendário falhar, a evidência da auditoria já está gravada")

    print()
    print("--- 8. a tela oferece a marcação ---")
    tela = open(os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py"),
                encoding="utf-8").read()
    conferir("marcar_nao_postou" in tela, "a tela de Downloads chama")
    conferir("não postou" in tela.lower(),
             "com nome em linguagem corrente")
    conferir("sem baixar nada" in tela,
             "e deixa claro que não baixa nada")


if __name__ == "__main__":
    print("=" * 74)
    print("  O Calendário dentro do fluxo, e a marcação de não postou")
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
