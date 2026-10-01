# -*- coding: utf-8 -*-
r"""
Quanto do #publi o OCR consegue ler, e se vale mexer nisso.

POR QUE ESTA FERRAMENTA EXISTE (07/09/2026)

A pendência aberta dizia "só 23% das peças têm publi legível por OCR" e propunha
duas saídas. Os 23% eram verdade e foram reproduzidos aqui, mas a conclusão que
se tirava deles estava errada, e a ferramenta existe para que a pergunta possa
ser refeita com material novo em vez de discutida de memória.

O QUE ELA MEDE

  1. quantas peças têm o publi lido hoje, que é a linha de base
  2. quanto cada variante de pré-processamento no recorte do topo acrescenta
  3. o cruzamento que decide a questão: em quantas peças o programa LÊ O RODAPÉ
     e mesmo assim não acha publi

O ITEM 3 É O QUE IMPORTA. O rodapé é o texto mais fino da tela, e o publi é
maior que ele. Numa peça em que o rodapé foi lido, está provado que o OCR
funcionou ali. Se o publi não aparece nessa mesma peça, a explicação provável
não é leitura fraca, é que o publi não está na peça. Isso deixa de ser assunto
de programa e vira assunto de conformidade, para quem é da área decidir.

ELA TAMBÉM DIZ DE QUAL GERAÇÃO DE BANNER É A AMOSTRA, e isso não é enfeite.
O banner mudou em 17/07/2026 junto com a regra: antes trazia o "jogue com
responsabilidade", depois traz a frase do Ministério da Fazenda. Medição feita
em peça velha descreve uma peça que não existe mais. Em 07/09/2026 o cache tinha
552 peças e só 2 posteriores à virada, e foi por isso que a medição daquele dia
não pôde ser transportada para a operação nova.

SÓ LÊ. Não fala com o Instagram, não toca em planilha e não altera arquivo
nenhum: trabalha sobre os quadros que a análise já deixou no cache.

    py ferramentas\medir_leitura_do_publi.py                 as peças recentes
    py ferramentas\medir_leitura_do_publi.py 2026-09-01      desde essa data
    py ferramentas\medir_leitura_do_publi.py tudo            o cache inteiro
    py ferramentas\medir_leitura_do_publi.py tudo 10         uma peça a cada 10
"""
import datetime
import os
import sys
import time

from _base import cabecalho, linha, secao

import validar_avisos_portaria136 as motor
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIDIA = os.path.join(os.path.dirname(BASE), "auditorias",
                     "avisos-influenciadores-portaria136", "midia")

# A mesma faixa que o programa usa no quarto degrau do OCR. Fica ligada à
# constante do motor de propósito: se ela mudar lá, a medição acompanha.
FAIXA_TOPO = motor.FAIXA_DO_PUBLI_TOPO

# A virada do banner. Serve só para dizer de que geração é a amostra.
VIRADA_DO_BANNER = motor.DATA_VIGENCIA_MINISTERIO_FAZENDA

DIAS_QUE_CONTAM_COMO_RECENTE = 30


def _cru(rec):
    return rec


def _contraste(rec):
    return ImageEnhance.Contrast(rec.convert("L")).enhance(2.0)


def _contraste_2x(rec):
    g = ImageEnhance.Contrast(rec.convert("L")).enhance(2.0)
    return g.resize((g.size[0] * 2, g.size[1] * 2), Image.LANCZOS)


def _contraste_forte_2x(rec):
    g = ImageEnhance.Contrast(rec.convert("L")).enhance(3.0)
    return g.resize((g.size[0] * 2, g.size[1] * 2), Image.LANCZOS)


def _binario(rec):
    return ImageOps.autocontrast(rec.convert("L")).point(
        lambda p: 255 if p > 140 else 0)


def _nitidez_2x(rec):
    g = ImageEnhance.Contrast(rec.convert("L")).enhance(2.0)
    g = g.filter(ImageFilter.SHARPEN)
    return g.resize((g.size[0] * 2, g.size[1] * 2), Image.LANCZOS)


# A primeira é o que o programa já faz hoje no quarto degrau. As outras cinco
# são as candidatas, e em 07/09/2026 nenhuma delas passou de +1 peça.
VARIANTES = [
    ("recorte cru (é o de hoje)", _cru),
    ("contraste, sem ampliar", _contraste),
    ("contraste + 2x", _contraste_2x),
    ("contraste forte + 2x", _contraste_forte_2x),
    ("binarização", _binario),
    ("nitidez + 2x", _nitidez_2x),
]


def pecas_do_cache():
    """Toda pasta de quadros do cache, em ordem estável.

    Uma pasta `frames_*` é uma peça. Só os `.jpg` contam: os `.png` são recortes
    que a própria análise gerou, e contá-los mediria o recorte duas vezes."""
    achadas = []
    for raiz, _dirs, arquivos in os.walk(MIDIA):
        if not os.path.basename(raiz).startswith("frames_"):
            continue
        quadros = sorted(a for a in arquivos if a.lower().endswith(".jpg"))
        if quadros:
            achadas.append((raiz, [os.path.join(raiz, q) for q in quadros]))
    achadas.sort(key=lambda x: x[0])
    return achadas


def medir_peca(quadros):
    """Devolve o que foi lido numa peça, olhando TODOS os quadros dela.

    Não para no primeiro acerto, ao contrário do programa: aqui a pergunta é o
    que dá para ler na peça, e não onde dá para economizar chamada."""
    texto = []
    achou = {nome: False for nome, _ in VARIANTES}
    for caminho in quadros:
        try:
            img = Image.open(caminho)
            img.load()
        except Exception:
            continue
        texto.append(motor.ocr_image_rapido(caminho))
        recorte = img.crop((0, 0, img.size[0], int(img.size[1] * FAIXA_TOPO)))
        for nome, preparar in VARIANTES:
            if achou[nome]:
                continue
            try:
                lido = pytesseract.image_to_string(preparar(recorte),
                                                   lang="por+eng")
            except Exception:
                continue
            if motor.REGEX_PUBLI.search(lido or ""):
                achou[nome] = True
    junto = "\n".join(texto)
    m18, mport, mextra, mmf, _ap, mpubli, _as = motor._buscar_matches(junto)
    return {
        "publi_quadro_inteiro": bool(mpubli),
        "por_variante": achou,
        "rodape": {"18": bool(m18), "portaria": bool(mport),
                   "responsabilidade": bool(mextra),
                   "ministerio_fazenda": bool(mmf)},
    }


def achou_publi(r):
    return r["publi_quadro_inteiro"] or any(r["por_variante"].values())


def linha_de_base(r):
    """O que o programa lê HOJE: o quadro inteiro mais o recorte cru do topo."""
    return r["publi_quadro_inteiro"] or r["por_variante"]["recorte cru (é o de hoje)"]


def relatar(medidas):
    total = len(medidas)
    if not total:
        print("  Nenhuma peça na seleção.")
        return
    base = sum(1 for r in medidas if linha_de_base(r))

    secao("DE QUAL GERAÇÃO DE BANNER É ESTA AMOSTRA")
    resp = sum(1 for r in medidas if r["rodape"]["responsabilidade"])
    mf = sum(1 for r in medidas if r["rodape"]["ministerio_fazenda"])
    linha("com 'jogue com responsabilidade'", f"{resp} peça(s), banner anterior "
          f"a {VIRADA_DO_BANNER}")
    linha("com a frase do Min. da Fazenda", f"{mf} peça(s), banner de "
          f"{VIRADA_DO_BANNER} em diante")
    if mf == 0 and resp:
        print()
        print("   ATENÇÃO: a amostra é toda do banner antigo. O número abaixo")
        print("   descreve uma peça que não é mais publicada, e não deve ser")
        print("   usado para decidir nada sobre a operação de hoje.")

    secao("O PUBLI, POR PEÇA")
    linha("peças medidas", total)
    linha("publi lido hoje", f"{base} ({base / total * 100:.1f}%)")
    print()
    print("   Cada variante nova, somada ao que já se lê hoje:")
    for nome, _ in VARIANTES[1:]:
        com = sum(1 for r in medidas if linha_de_base(r) or r["por_variante"][nome])
        so_ela = sum(1 for r in medidas
                     if not linha_de_base(r) and r["por_variante"][nome])
        print(f"      {nome:<28} {com:>4} peça(s)   ganho {com - base:+d}"
              f"   (só ela acha: {so_ela})")
    teto = sum(1 for r in medidas if achou_publi(r))
    print()
    linha("teto, somando TODAS", f"{teto} ({teto / total * 100:.1f}%), "
          f"ganho {teto - base:+d}")

    secao("O PUBLI ESTÁ AUSENTE OU SÓ ILEGÍVEL?")
    print(f"   Rodapé provado = {motor.MINIMO_LINHAS_PARA_PROVAR_RODAPE} ou mais "
          f"das 4 linhas lidas, que é a regra do programa.")
    print()
    com_rodape = [r for r in medidas
                  if sum(r["rodape"].values()) >= motor.MINIMO_LINHAS_PARA_PROVAR_RODAPE]
    com_os_dois = sum(1 for r in com_rodape if achou_publi(r))
    linha("peças com o rodapé lido", len(com_rodape))
    linha("   dessas, com publi", com_os_dois)
    linha("   dessas, SEM publi", len(com_rodape) - com_os_dois)
    if com_rodape:
        n = len(com_rodape) - com_os_dois
        print()
        print(f"   Nessas {n} peça(s) o OCR provou que lê o texto mais fino da")
        print(f"   tela e não achou publi. É {n / total * 100:.1f}% da amostra, e")
        print("   aponta para publi AUSENTE, não para leitura fraca. Confirmar")
        print("   olhando algumas antes de tratar como achado.")


def selecionar(argumento, passo):
    todas = pecas_do_cache()
    if argumento == "tudo":
        escolhidas, desde = todas, None
    else:
        desde = (datetime.date.fromisoformat(argumento) if argumento else
                 datetime.date.today() - datetime.timedelta(
                     days=DIAS_QUE_CONTAM_COMO_RECENTE))
        # O corte é pela data em que a peça foi PROCESSADA, e não pela data no
        # nome: peça recente costuma chegar sem data no nome (por exemplo
        # "frames_REELS" ou "frames_tela 2").
        escolhidas = [
            (p, q) for p, q in todas
            if datetime.date.fromtimestamp(os.path.getmtime(p)) >= desde]
    if passo > 1:
        escolhidas = escolhidas[::passo]
    return todas, escolhidas, desde


if __name__ == "__main__":
    argumento = sys.argv[1] if len(sys.argv) > 1 else None
    passo = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    cabecalho("Quanto do #publi o OCR consegue ler",
              "só leitura, não fala com o Instagram")

    todas, escolhidas, desde = selecionar(argumento, passo)
    linha("peças no cache", len(todas))
    if desde:
        linha("recorte", f"processadas em {desde:%d/%m/%Y} ou depois")
    else:
        linha("recorte", "o cache inteiro")
    if passo > 1:
        linha("amostragem", f"uma peça a cada {passo}")
    linha("peças a medir", len(escolhidas))
    linha("quadros", sum(len(q) for _, q in escolhidas))

    if not escolhidas:
        print()
        print("  Nada a medir nesse recorte. Use 'tudo' para o cache inteiro.")
        sys.exit(0)

    print()
    print("  Medindo. Leva alguns segundos por peça, o OCR é a parte lenta.")
    print()
    medidas = []
    inicio = time.time()
    for i, (pasta, quadros) in enumerate(escolhidas, 1):
        medidas.append(medir_peca(quadros))
        print(f"   [{i}/{len(escolhidas)}] {os.path.basename(pasta)[:46]:<46} "
              f"{(time.time() - inicio) / i:.1f}s/peça", flush=True)

    print()
    relatar(medidas)
    print()
    print("=" * 74)
