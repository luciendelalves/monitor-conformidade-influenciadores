# -*- coding: utf-8 -*-
"""
Prova que o número da portaria é informação extra, e NÃO exigência.

DECISÃO DO AUDITOR EM 02/09/2026, com as palavras dele:

> "vamos deixar como está, sem exigir o número, o número vai entrar como um PLUS,
>  pq o obrigatório mesmo é o AUTORIZADO PELA PORTARIA, e a frase do ministério
>  com o aviso de APOSTA NÃO É INVESTIMENTO"

Ele confirmou que "AUTORIZADO PELA PORTARIA SPA/MF Nº 136/25" é o que a peça deve
conter, e que 136/25 é a versão atual.

POR QUE O NÚMERO NÃO É EXIGIDO, mesmo sendo o texto correto: ele é a linha mais
fina do banner e falha no OCR com frequência. Exigi-lo criaria Não Conforme em
peça que traz o aviso completo com o número ilegível, que é o erro mais caro que
esta ferramenta pode cometer, porque acusa indevidamente.

O QUE ESTE TESTE PROTEGE: que ninguém, no futuro, "melhore" a checagem passando a
exigir o número. Se alguém fizer isso, este teste falha, e a mudança passa a ser
deliberada em vez de acidental.

    py testes\teste_numero_da_portaria.py
"""
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


# Texto REAL da faixa, como o Tesseract leu do @maumauzk em 02/09/2026.
FAIXA_REAL = ("18+ MINISTÉRIO DA FAZENDA ADVERTE: APOSTA NÃO É INVESTIMENTO "
              "JOGUE COM RESPONSABILIDADE. CONSULTE T&Cs. AUTORIZADO PELA "
              "PORTARIA SPA/MF Nº 136/25.")


def rodar():
    import validar_avisos_portaria136 as motor

    print("--- 1. a EXIGÊNCIA continua sendo a menção à portaria ---")
    # Cada um destes satisfaz o item sozinho, e é assim de propósito.
    for texto in ("AUTORIZADO PELA PORTARIA SPA/MF Nº 136/25",
                  "AUTORIZADO PELA PORTARIA",
                  "portaria",
                  "SPA/MF"):
        conferir(bool(motor.REGEX_PORTARIA.search(texto)),
                 f"aceita {texto[:42]!r}")

    print()
    print("--- 2. e o NÚMERO não é exigido ---")
    # Este é o ponto do teste: peça com a menção e SEM número legível continua
    # satisfazendo o item.
    sem_numero = "AUTORIZADO PELA PORTARIA SPA/MF"
    conferir(bool(motor.REGEX_PORTARIA.search(sem_numero)),
             "peça sem número legível satisfaz o item",
             "exigir o número acusaria peça com aviso completo e número ilegível")
    conferir(motor.numero_da_portaria(sem_numero) is None,
             "e o número sai como desconhecido, sem inventar")

    print()
    print("--- 3. o número é CAPTURADO quando dá para ler ---")
    conferir(motor.numero_da_portaria(FAIXA_REAL) == "136/25",
             "lê 136/25 da faixa real do @maumauzk",
             str(motor.numero_da_portaria(FAIXA_REAL)))

    print()
    print("--- 4. tolera o ruído do OCR no \"Nº\" ---")
    # O OCR devolve o "Nº" de várias formas, e o número não pode se perder por
    # causa disso.
    for variacao, esperado in [
        ("PORTARIA SPA/MF Nº 136/25", "136/25"),
        ("PORTARIA SPA/MF No 136/25", "136/25"),
        ("PORTARIA SPA/MF N° 136/25", "136/25"),
        ("PORTARIA SPA/MF N. 136/25", "136/25"),
        ("PORTARIA SPA/MF 136/25", "136/25"),
        ("PORTARIA SPA / MF Nº 136 / 25", "136/25"),
        ("portaria spa/mf no 1231/2024", "1231/2024"),
        # AS TRÊS ABAIXO SÃO RUÍDO REAL, do levantamento de 02/09/2026 sobre as
        # peças já analisadas. A primeira pegou a versão anterior deste padrão:
        # com "N2136/25" ela absorvia o 2 e devolvia "2136/25", um número que
        # não existe.
        ("PORTARIA SPA/MF N2136/25", "136/25"),
        ("PORTARIA SPAIMF N2 136/25", "136/25"),
        ("PORTARIA SPAMF N2 136/25", "136/25"),
    ]:
        veio = motor.numero_da_portaria(variacao)
        conferir(veio == esperado, f"{variacao[:36]!r} -> {esperado}", str(veio))

    print()
    print("--- 4b. e sem o \"Nº\", um número que começa com 2 é lido inteiro ---")
    # O "2" só é tratado como ruído DEPOIS de um "n". Sem o "Nº", ele é dígito.
    conferir(motor.numero_da_portaria("PORTARIA 2136/25") == "2136/25",
             "\"PORTARIA 2136/25\" -> 2136/25",
             str(motor.numero_da_portaria("PORTARIA 2136/25")))

    print()
    print("--- 5. número DIFERENTE é lido como é, sem julgamento ---")
    # É para isso que a captura existe: alguém olhar a coluna e perceber uma peça
    # citando número antigo. O programa NÃO acusa a partir disso.
    conferir(motor.numero_da_portaria("AUTORIZADO PELA PORTARIA SPA/MF Nº 999/99")
             == "999/99",
             "lê um número qualquer sem reclamar",
             "quem julga se o número está certo é gente, não o programa")

    print()
    print("--- 6. a captura NÃO participa de decisão nenhuma ---")
    import inspect
    fonte = inspect.getsource(motor)
    # O número só pode aparecer na montagem da evidência. Se ele entrar num
    # achou_*, num nucleo_ok ou na lista de faltando, virou exigência.
    for proibido in ("achou_numero", "numero_ok",
                     'faltando.append("numero'):
        conferir(proibido not in fonte,
                 f"não existe {proibido!r} no motor",
                 "isso transformaria o número em exigência")
    trecho = fonte[fonte.find("numero_portaria = numero_da_portaria"):][:400]
    conferir("evidencia_partes.append" in trecho,
             "o número só entra na evidência", trecho[:80])
    conferir("informação" in trecho and "não é exigência" in trecho,
             "e a própria evidência diz que é informação extra")


if __name__ == "__main__":
    print("=" * 74)
    print("  Número da portaria: informação extra, nunca exigência")
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
