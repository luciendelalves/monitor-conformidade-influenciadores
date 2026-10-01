# -*- coding: utf-8 -*-
r"""
O que cada motor de OCR lê num arquivo, quadro por quadro.

SOMENTE LEITURA. Baixa o arquivo do Drive pelo identificador que o cache guarda,
ou por um caminho local. Zero chamada ao Instagram.

    py ferramentas\ler_com_ocr.py @maumauzk              todos os arquivos dele
    py ferramentas\ler_com_ocr.py "Tela 1"               por pedaço do nome
    py ferramentas\ler_com_ocr.py C:\caminho\video.mp4   arquivo local
    py ferramentas\ler_com_ocr.py @maumauzk rapido       só Tesseract (bem mais rápido)

É A FERRAMENTA QUE RESPONDE "o programa errou ou a peça não tem o aviso?"

Em 02/09/2026 ela respondeu isso em cinco arquivos e derrubou uma suspeita minha
de defeito de leitura. O OCR tinha lido a faixa inteira do rodapé no story da
Lottu ("MINISTÉRIO DA FAZENDA ADVERTE: APOSTA NÃO É INVESTIMENTO"), e os outros
quatro eram receita de bolo, venda de boné, convite para live e pessoa falando em
casa. Nenhum era peça publicitária.

CUSTO: o EasyOCR é lento, cerca de 13 s por quadro no pior caso. Com o
trabalhador analisando ao mesmo tempo, os dois disputam a mesma CPU. Use o modo
`rapido` quando só quiser saber se há texto, e o completo quando o Tesseract não
achou nada e você precisa saber se é a peça ou o motor.
"""
import os
import shutil
import sys
import tempfile

from _base import cabecalho, linha, pedir_argumento, secao

import fluxo_downloads as fluxo
import pipeline_influenciadores as pipeline
import validar_avisos_portaria136 as motor

# Referência DIRETA, sem hasattr: se algum destes for renomeado no motor, esta
# ferramenta tem que quebrar na hora. A primeira versão usava hasattr para um
# deles, e isso apenas deixaria o item sumir da conferência em silêncio, que é o
# tipo de coisa que faz uma medição parecer certa estando errada.
ITENS = (
    ("18+", motor.REGEX_18),
    ("portaria", motor.REGEX_PORTARIA),
    ("min. fazenda", motor.REGEX_MINISTERIO_FAZENDA),
    ("jogo responsável", motor.REGEX_EXTRA),
    ("conteúdo de aposta", motor.REGEX_CONTEUDO_APOSTA),
    ("publi", motor.REGEX_PUBLI),
)


def achados_em(texto):
    saida = []
    for rotulo, regex in ITENS:
        achado = regex.search(texto)
        if achado:
            saida.append(f"{rotulo}={achado.group(0)!r}")
    return saida


def mostrar_quadro(caminho, completo=True):
    from PIL import Image
    try:
        largura, altura = Image.open(caminho).size
        tamanho = f"{largura}x{altura}"
    except Exception:
        tamanho = "?"
    print(f"      {os.path.basename(caminho)}   {tamanho}")

    juntos = []
    passadas = [("Tesseract", motor.ocr_image_rapido)]
    if completo:
        passadas.append(("EasyOCR  ", motor.ocr_image_forte))
    for rotulo, funcao in passadas:
         # O texto vem com muitas quebras; junta para caber numa linha.
        try:
            texto = " ".join((funcao(caminho) or "").split())
        except Exception as e:
            print(f"         {rotulo}: FALHOU  {type(e).__name__}: {str(e)[:60]}")
            continue
        juntos.append(texto)
        print(f"         {rotulo}: {texto[:200] or '(nada)'}")

    achados = achados_em(" ".join(juntos))
    print(f"            -> {', '.join(achados) if achados else 'NENHUM item reconhecido'}")
    numero = motor.numero_da_portaria(" ".join(juntos))
    if numero:
        print(f"            -> número da portaria citado: {numero}")


def alvos_do_cache(procurado):
    """[(nome, drive_id)] das entradas do cache que casam com o pedido."""
    chave = procurado.lstrip("@").lower()
    saida = []
    for r in pipeline.carregar_cache().values():
        nome = str(r.get("arquivo") or "")
        influ = str(r.get("influenciador") or "")
        if chave in nome.lower() or chave in influ.lower():
            if r.get("drive_id"):
                saida.append((nome or r["drive_id"], r["drive_id"], r))
    return saida


def main():
    pedido = pedir_argumento(1, None, "arquivo, @influenciador ou pedaço do nome")
    completo = pedir_argumento(2, "completo") != "rapido"
    cabecalho("O que o OCR lê",
              f"modo: {'Tesseract + EasyOCR' if completo else 'só Tesseract'}")

    if os.path.exists(pedido):
        secao(f"arquivo local: {pedido}")
        pasta = tempfile.mkdtemp(prefix="ocr_")
        try:
            duracao = motor.duracao_do_video(pedido)
            linha("duração", duracao if duracao else "não legível (pode ser imagem)")
            quadros = motor.extract_frames(pedido, pasta) if duracao else [pedido]
            linha("quadros", len(quadros))
            for q in quadros:
                mostrar_quadro(q, completo)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)
        return 0

    alvos = alvos_do_cache(pedido)
    if not alvos:
        print(f"   Não achei nada no cache que case com {pedido!r}.")
        print("   O cache guarda o identificador do Drive de cada análise; se ele")
        print("   foi limpo, use o caminho de um arquivo local.")
        return 1

    linha("arquivos encontrados no cache", len(alvos))
    import drive_client
    for nome, ident, registro in alvos:
        secao(nome)
        linha("veredito guardado", registro.get("classificacao"))
        linha("motivo", str(registro.get("motivo") or "")[:140])
        pasta = tempfile.mkdtemp(prefix="ocr_")
        try:
            local = os.path.join(pasta, "arquivo" + os.path.splitext(nome)[1])
            try:
                drive_client.download_file(ident, local)
            except Exception as e:
                print(f"   não baixei: {str(e)[:130]}")
                continue
            linha("baixado", f"{os.path.getsize(local) / 1024:.0f} KB")
            duracao = motor.duracao_do_video(local)
            quadros = motor.extract_frames(local, pasta) if duracao else [local]
            linha("quadros", len(quadros))
            for q in quadros:
                mostrar_quadro(q, completo)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
