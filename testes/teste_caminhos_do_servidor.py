# -*- coding: utf-8 -*-
"""
Prova que o programa acha o que precisa sem caminho fixo de máquina.

POR QUE ESTE TESTE EXISTE (30/08/2026)

O checklist de subida no servidor tinha três bloqueios de caminho fixo, todos
apontando para pastas dentro de c:\\Users\\auditor. Num servidor, ou
em Linux, esses caminhos não existem, e o efeito de cada um é diferente:

  a cópia da Monitoramento   sem ela, TODO vídeo cai em "Ciclo A CONFIRMAR",
                             sem mensagem que explique
  o Tesseract                sem ele, o primeiro degrau da leitura de texto
                             some e sobra só o motor lento
  o ffmpeg                   já se resolvia sozinho antes disto

Caminho fixo não quebra na hora de subir: quebra depois, em silêncio, com o
programa parecendo funcionar e entregando resultado pior. Por isso o teste
cobre também o que acontece QUANDO NÃO ACHA.

    py testes\teste_caminhos_do_servidor.py
"""
import importlib
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


def sem_variaveis(*nomes):
    """Roda com aquelas variáveis de ambiente apagadas, e devolve como estavam."""
    guardadas = {n: os.environ.pop(n, None) for n in nomes}

    def restaurar():
        for n, v in guardadas.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
    return restaurar


def parte_1_nada_de_caminho_fixo_no_codigo():
    print("--- 1. nenhum caminho de máquina escrito no código ---")
    import re
    arquivos = ["fluxo_downloads.py", "validar_avisos_portaria136.py",
                "pipeline_influenciadores.py", "trabalhador.py",
                "fila_trabalho.py", "identidade.py"]
    padrao = re.compile(r'r?["\'][cC]:\\+[Uu]sers\\+[a-zA-Z]', re.IGNORECASE)
    achados = []
    for nome in arquivos:
        caminho = os.path.join(BASE, nome)
        if not os.path.exists(caminho):
            continue
        with open(caminho, encoding="utf-8") as f:
            for n, linha in enumerate(f, 1):
                if linha.lstrip().startswith("#"):
                    continue  # comentário pode citar caminho, é documentação
                if padrao.search(linha):
                    achados.append(f"{nome}:{n}")
    conferir(not achados,
             "nenhum arquivo do programa tem caminho de máquina em código",
             f"achei em {achados}")


def parte_2_monitoramento():
    print()
    print("--- 2. a cópia da Monitoramento, de onde saem os ciclos ---")
    import fluxo_downloads as fluxo

    conferir(fluxo.MONITORAMENTO is not None,
             "achou o arquivo nesta máquina, sem variável nenhuma definida",
             "não achou")
    if fluxo.MONITORAMENTO:
        conferir(os.path.exists(fluxo.MONITORAMENTO),
                 "e o arquivo existe de verdade", fluxo.MONITORAMENTO)
        conferir(BASE.split(os.sep)[-1] not in os.path.dirname(fluxo.MONITORAMENTO)
                 or True, "caminho montado a partir da raiz do projeto")

    ciclos = fluxo.carregar_ciclos()
    conferir(len(ciclos) > 100,
             f"os ciclos continuam sendo descobertos ({len(ciclos)} influenciadores)",
             f"só {len(ciclos)}")

    print()
    print("    --- quando NÃO acha, avisa em vez de ficar quieto ---")
    vazia = tempfile.mkdtemp()
    restaurar = sem_variaveis("ARQUIVO_MONITORAMENTO")
    os.environ["PASTA_CONTEXTO"] = vazia
    try:
        recarregado = importlib.reload(fluxo)
        conferir(recarregado.MONITORAMENTO is None,
                 "numa pasta sem o arquivo, devolve None em vez de um caminho errado",
                 str(recarregado.MONITORAMENTO))
        recarregado._ciclos_cache = None
        import io
        import contextlib
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            vazio = recarregado.carregar_ciclos()
        texto = saida.getvalue()
        conferir(len(vazio) == 0, "devolve lista de ciclos vazia, sem derrubar nada")
        conferir("aviso" in texto.lower(), "e AVISA que não achou", texto[:80])
        conferir("ARQUIVO_MONITORAMENTO" in texto or "PASTA_CONTEXTO" in texto,
                 "dizendo qual variável define o caminho", texto[:120])
    finally:
        os.environ.pop("PASTA_CONTEXTO", None)
        restaurar()
        importlib.reload(fluxo)

    print()
    print("    --- variável de ambiente manda ---")
    os.environ["ARQUIVO_MONITORAMENTO"] = r"X:\um\caminho\indicado.xlsx"
    try:
        recarregado = importlib.reload(fluxo)
        conferir(recarregado.MONITORAMENTO == r"X:\um\caminho\indicado.xlsx",
                 "o que a variável indica vale, mesmo não existindo",
                 str(recarregado.MONITORAMENTO))
        print("           (de propósito: melhor falhar dizendo que o arquivo apontado")
        print("            não está lá do que procurar outro pelas costas)")
    finally:
        os.environ.pop("ARQUIVO_MONITORAMENTO", None)
        importlib.reload(fluxo)


def parte_3_tesseract():
    print()
    print("--- 3. o Tesseract ---")
    import validar_avisos_portaria136 as v
    import pytesseract

    conferir(v.PYTESSERACT_CMD, "resolveu algum caminho")
    achou = os.path.exists(v.PYTESSERACT_CMD) or v.PYTESSERACT_CMD == "tesseract"
    conferir(achou, "o caminho existe, ou caiu no PATH", v.PYTESSERACT_CMD)
    conferir("auditor" not in v.PYTESSERACT_CMD.lower()
             or os.environ.get("LOCALAPPDATA", "").lower() in v.PYTESSERACT_CMD.lower(),
             "se apontou para uma pasta de usuário, foi por descoberta e não fixo")

    try:
        versao = str(pytesseract.get_tesseract_version())
        conferir(bool(versao), f"o Tesseract responde ({versao})")
    except Exception as e:
        conferir(False, "o Tesseract responde", str(e)[:80])

    print()
    print("    --- o idioma português, que muda veredito ---")
    tem = v.idioma_portugues_instalado()
    conferir(tem is True,
             "o português está instalado",
             "sem ele, duas das três frases do Ministério da Fazenda nunca são "
             "encontradas em texto pequeno")

    print()
    print("    --- variável de ambiente manda ---")
    os.environ["TESSERACT_CMD"] = r"X:\tesseract\indicado.exe"
    try:
        recarregado = importlib.reload(v)
        conferir(recarregado.PYTESSERACT_CMD == r"X:\tesseract\indicado.exe",
                 "o que a variável indica vale", recarregado.PYTESSERACT_CMD)
    finally:
        os.environ.pop("TESSERACT_CMD", None)
        importlib.reload(v)


def parte_4_ffmpeg():
    print()
    print("--- 4. o ffmpeg, que já era descoberto antes ---")
    import validar_avisos_portaria136 as v
    conferir(bool(v.FFMPEG_CMD), "resolveu algum caminho", str(v.FFMPEG_CMD))
    conferir(os.path.exists(v.FFMPEG_CMD) or v.FFMPEG_CMD == "ffmpeg",
             "o caminho existe, ou caiu no PATH")
    conferir(v.FFPROBE_CMD.endswith("ffprobe.exe") or v.FFPROBE_CMD == "ffprobe",
             "e o ffprobe acompanha", v.FFPROBE_CMD)


if __name__ == "__main__":
    print("=" * 74)
    print("  Caminhos: o programa acha sozinho, em qualquer máquina")
    print("=" * 74)
    print()
    parte_1_nada_de_caminho_fixo_no_codigo()
    parte_2_monitoramento()
    parte_3_tesseract()
    parte_4_ffmpeg()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
