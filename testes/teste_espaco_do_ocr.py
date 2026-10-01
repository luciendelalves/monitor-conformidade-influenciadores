# -*- coding: utf-8 -*-
r"""
Prova que as regras reconhecem a frase quando o OCR entrega as palavras coladas.

O DEFEITO, encontrado em 03/09/2026, e ele estava reprovando peça conforme.

O auditor mostrou uma peça da @perlladecassia com o rodapé perfeitamente legível
e perguntou por que o programa não pegou o aviso do Ministério da Fazenda. Rodei
os três motores de OCR no mesmo arquivo, e o resultado foi este:

    Tesseract   APOS IMVESTIMENTO                 leitura ruim de verdade
    RapidOCR    APOSTANAO EINVESTIMENTO           frase INTEIRA, sem espaços
    RapidOCR    APOSTANAOEINVESTIMENTO            idem, no quadro seguinte
    EasyOCR     APOSTA NÃO É INVESThento          leitura ruim de verdade

Ou seja: um dos três motores leu a frase CORRETA, e o programa a rejeitou. A
regra exigia `\s+` entre as palavras, e aquele motor entrega tudo colado. O mesmo
acontecia com "JOGUECOMRESPONSABILIDADE".

A peça estava conforme e o veredito saía REQUER ANÁLISE HUMANA. Numa auditoria,
isso é trabalho humano criado por defeito de leitura do programa.

POR QUE `\s*` NÃO AFROUXA A EXIGÊNCIA, que é a pergunta que importa: ele tolera a
AUSÊNCIA de espaço, e nada mais. As palavras continuam todas obrigatórias, na
mesma ordem, e `\s*` não casa caractere qualquer no meio. A seção 3 prova isso
contra frases que não devem passar.

O QUE FOI DESCARTADO NO CAMINHO: recortar a faixa do rodapé e ampliar antes de
ler. Medido no mesmo arquivo, melhorou a leitura do Tesseract ("APOSTÁTIM >
VESTIMENTO" no lugar de "APOS IMVESTIMENTO") mas não fez nenhuma peça passar, e
custava uma passada de OCR a mais por quadro. A correção da regra custa zero.

AS REGRAS DE ÁUDIO FICARAM COMO ESTAVAM, de propósito: elas leem transcrição do
Whisper, que emite espaço normalmente, e afrouxar ali só criaria risco de alerta
falso.

    py testes\teste_espaco_do_ocr.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

falhas = []

# TRECHOS REAIS, lidos na peça "@perlladecassia - tela 1.mp4" em 03/09/2026.
# Não são inventados: saíram da medição dos três motores naquele arquivo.
LIDO_RAPIDOCR_1 = ("MINISTERIO DA FAZENDAADVERTE:APOSTANAO EINVESTIMENTO "
                   "JOGUECOMRESPONSABILIDADE.CONSULTET&CS.AUTORIZADOPELA")
LIDO_RAPIDOCR_2 = ("MINISTERIO DA FAZENDA ADVERTE:APOSTANAOEINVESTIMENTO "
                   "JOGUECOMRESPONSABILIDADE.CONSULTET&CS.AUTORIZADOPEL")
LIDO_TESSERACT = ("MINISTE DA. ADVERTE: APOS IMVESTIMENTO Joa ONSABILIDADE, "
                  "ULTE T&Gs. A DNENA ALTARIA SPA/MF NO 136/25")
LIDO_DA_PECA_QUE_PASSOU = (
    "MINISTERIO DA FAZENDA ADVERTE: APOSTA NAO E INVESTIMENTO "
    "JOGUE COM RESPONSABILIDADE. CONSULTE T&Cs. AUTORIZADO PELA PORTARIA SPA/M")


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    import validar_avisos_portaria136 as motor

    print("--- 1. a frase colada passa a ser reconhecida ---")
    for rotulo, texto, esperado in (
            ("RapidOCR, quadro 1", LIDO_RAPIDOCR_1, "APOSTANAO EINVESTIMENTO"),
            ("RapidOCR, quadro 2", LIDO_RAPIDOCR_2, "APOSTANAOEINVESTIMENTO")):
        achado = motor.REGEX_MINISTERIO_FAZENDA.search(texto)
        conferir(achado is not None and achado.group(0) == esperado,
                 f"{rotulo}: acha a frase do Ministério",
                 str(achado.group(0) if achado else None))
        extra = motor.REGEX_EXTRA.search(texto)
        conferir(extra is not None,
                 f"{rotulo}: e acha o \"jogue com responsabilidade\" colado",
                 str(extra.group(0) if extra else None))

    print()
    print("--- 2. leitura que é ruim de verdade continua NÃO passando ---")
    # Este é o ponto que separa "regra cega" de "regra afrouxada". O Tesseract
    # leu "APOS IMVESTIMENTO": falta o TA de APOSTA, falta o "NÃO É" inteiro e o
    # INVESTIMENTO veio com M. Não há frase ali, e não deve passar.
    conferir(motor.REGEX_MINISTERIO_FAZENDA.search(LIDO_TESSERACT) is None,
             "\"APOS IMVESTIMENTO\" não é aceito",
             "se isso passasse, a regra teria deixado de exigir a frase")
    # E a peça que já passava continua passando, com espaço normal.
    conferir(motor.REGEX_MINISTERIO_FAZENDA.search(LIDO_DA_PECA_QUE_PASSOU)
             is not None,
             "e a leitura com espaço normal continua passando")

    print()
    print("--- 3. o espaço opcional NÃO cria falso positivo ---")
    # \s* tolera a AUSÊNCIA de espaço, não caractere qualquer. Estas frases têm
    # palavra a mais, palavra a menos, ordem trocada ou pontuação no meio.
    NAO_DEVE_PASSAR = [
        "aposta e investimento",
        "aposta nao investimento",
        "investimento nao e aposta",
        "aposta, nao. e! investimento",
        "apostas nao sao investimentos",
        "a aposta que nao parece investimento",
        "aposta e um bom investimento",
    ]
    for texto in NAO_DEVE_PASSAR:
        achado = motor.REGEX_MINISTERIO_FAZENDA.search(texto)
        conferir(achado is None, f"não casa: {texto!r}",
                 str(achado.group(0) if achado else ""))

    print()
    print("--- 4. as três frases do Ministério continuam valendo ---")
    for frase in ("APOSTA NÃO É INVESTIMENTO",
                  "APOSTAR PODE CAUSAR DEPENDÊNCIA",
                  "APOSTAR FAZ VOCÊ PERDER DINHEIRO"):
        conferir(motor.REGEX_MINISTERIO_FAZENDA.search(frase) is not None,
                 f"com espaço: {frase}")
        conferir(motor.REGEX_MINISTERIO_FAZENDA.search(
            frase.replace(" ", "")) is not None,
            f"colada: {frase.replace(' ', '')}")

    print()
    print("--- 5. as outras exigências também aceitam texto colado ---")
    conferir(motor.REGEX_EXTRA.search("JOGUECOMRESPONSABILIDADE") is not None,
             "jogue com responsabilidade")
    conferir(motor.REGEX_18.search("PROIBIDOPARAMENOR") is not None,
             "proibido para menor")
    conferir(motor.REGEX_18.search("MAIORESDEIDADE") is not None,
             "maiores de idade")
    conferir(motor.REGEX_CONTEUDO_APOSTA.search("VEMSEDIVERTIR") is not None,
             "vem se divertir, que é conteúdo de aposta")
    conferir(motor.REGEX_PUBLI.search("PARCERIAPAGA") is not None,
             "parceria paga")

    print()
    print("--- 6. as regras de ÁUDIO ficaram como estavam ---")
    # Elas leem transcrição do Whisper, que emite espaço normalmente. Afrouxar
    # ali só criaria risco de alerta falso, e alerta de fala é o mais delicado
    # que este programa produz.
    import inspect
    fonte = inspect.getsource(motor)
    trecho_audio = fonte.split("REGEX_SINAL_FRACO_AVISO")[1]
    conferir(r"\s+" in trecho_audio,
             "os padrões de fala continuam exigindo espaço",
             "eles não leem OCR, então o defeito não se aplica a eles")


if __name__ == "__main__":
    print("=" * 74)
    print("  O OCR entrega palavra colada, e a regra tem que reconhecer")
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
