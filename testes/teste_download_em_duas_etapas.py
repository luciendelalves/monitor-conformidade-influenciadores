# -*- coding: utf-8 -*-
"""
Prova que baixar em DUAS ETAPAS funciona: extrair sem baixar, escolher, e
baixar a partir do que já veio.

POR QUE ESTE TESTE EXISTE (30/08/2026)

Em 29/08 a função que baixa Story foi refatorada para falar uma vez só com o
Instagram, em vez de duas. A mudança troca o modo de baixar: antes era
`extract_info(download=True)`, agora é `extract_info(download=False)`, escolher
a story certa, e `process_ie_result(escolhida, download=True)`.

Essa última etapa NUNCA foi provada. Duas tentativas contra o Instagram
esbarraram em obstáculos diferentes (certificado da rede da empresa numa,
recusa da sessão na outra), e em nenhuma das duas o download chegou a rodar.
Ficou risco aberto a três dias de subir no servidor.

Este teste responde a pergunta sem depender do Instagram: serve um arquivo de
vídeo pelo próprio computador e roda exatamente as mesmas duas etapas. Se
passar, o que resta de incerto é só o comportamento do Instagram, não o
mecanismo.

É também o primeiro teste automatizado do programa. Não usa framework nenhum
de propósito: roda com `py`, sem instalar nada.

    py testes\teste_download_em_duas_etapas.py
"""
import http.server
import os
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import validar_avisos_portaria136 as motor


def fazer_video_pequeno(pasta):
    """Um vídeo de 1 segundo, gerado aqui, para não depender de arquivo de
    fora nem de rede."""
    destino = os.path.join(pasta, "amostra.mp4")
    subprocess.run(
        [motor.FFMPEG_CMD, "-y", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10",
         "-t", "1", "-pix_fmt", "yuv420p", destino],
        capture_output=True, check=False,
    )
    return destino if os.path.exists(destino) else None


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def servir(pasta, porta):
    """Serve a pasta em 127.0.0.1, só para este teste. Nada sai da máquina."""
    handler = lambda *a, **kw: Silencioso(*a, directory=pasta, **kw)
    servidor = socketserver.TCPServer(("127.0.0.1", porta), handler)
    fio = threading.Thread(target=servidor.serve_forever, daemon=True)
    fio.start()
    return servidor


def rodar():
    import yt_dlp

    trabalho = tempfile.mkdtemp()
    origem = os.path.join(trabalho, "origem")
    baixados = os.path.join(trabalho, "baixados")
    os.makedirs(origem, exist_ok=True)
    os.makedirs(baixados, exist_ok=True)

    print("preparando um vídeo de 1 segundo...")
    if not fazer_video_pequeno(origem):
        print("  FALHOU: não consegui gerar o vídeo. O ffmpeg está instalado?")
        return False

    porta = porta_livre()
    servidor = servir(origem, porta)
    url = f"http://127.0.0.1:{porta}/amostra.mp4"
    print(f"servindo em {url}")
    print()

    try:
        opcoes = {
            "outtmpl": os.path.join(baixados, "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }

        # Exatamente as duas etapas que a função de Story faz hoje.
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            print("etapa 1: extrair SEM baixar")
            info = ydl.extract_info(url, download=False)
            entradas = [e for e in (info.get("entries") or [info]) if e]
            print(f"  {len(entradas)} item(ns) encontrado(s)")
            if not entradas:
                print("  FALHOU: extração não devolveu item nenhum")
                return False

            escolhida = entradas[0]
            print(f"  escolhido: id={escolhida.get('id')}")

            print()
            print("etapa 2: baixar a escolhida, sem extrair de novo")
            baixada = ydl.process_ie_result(dict(escolhida), download=True)

            escolhida = baixada or escolhida
            caminho = ydl.prepare_filename(escolhida)

        print(f"  arquivo esperado: {os.path.basename(caminho)}")

        if not os.path.exists(caminho):
            print("  FALHOU: o arquivo não foi gerado")
            print(f"  o que existe na pasta: {os.listdir(baixados)}")
            return False

        tamanho = os.path.getsize(caminho)
        print(f"  existe, {tamanho} bytes")
        if tamanho == 0:
            print("  FALHOU: arquivo vazio")
            return False

        # Só existir não basta: tem que ser o vídeo, não uma página de erro
        # gravada com nome de vídeo.
        duracao = motor.duracao_do_video(caminho)
        print(f"  duração lida: {duracao}s")
        if not duracao or duracao <= 0:
            print("  FALHOU: o arquivo não é um vídeo legível")
            return False

        return True
    finally:
        servidor.shutdown()
        servidor.server_close()


if __name__ == "__main__":
    print("=" * 66)
    print("  Baixar em duas etapas: extrair sem baixar, depois baixar")
    print("=" * 66)
    print()
    passou = rodar()
    print()
    print("=" * 66)
    if passou:
        print("  PASSOU. O mecanismo de download em duas etapas funciona.")
        print("  O que resta de incerto no Story é só o Instagram, não isto.")
    else:
        print("  FALHOU. A refatoração de 29/08 não baixa, e precisa voltar")
        print("  para o modo antigo antes de ir para o servidor.")
    print("=" * 66)
    sys.exit(0 if passou else 1)
