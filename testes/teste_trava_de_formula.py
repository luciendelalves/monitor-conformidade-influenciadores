# -*- coding: utf-8 -*-
"""
Nenhuma escrita no Sheets deixa passar texto que vira fórmula.

POR QUE ESTE ARQUIVO EXISTE (04/09/2026)

Achado do parecer de cibersegurança que revisou o projeto seis dias depois do
parecer sobre o SAST original: toda escrita deste projeto usa
valueInputOption="USER_ENTERED", que é o modo do Google Sheets que INTERPRETA
texto começando com "=", "+", "-" ou "@" como fórmula. Nenhuma das funções de
escrita sanitizava isso.

O caminho de hoje não é explorável (a única edição em lote da tela usa um
dropdown de opções fixas, não texto livre), mas a trava foi colocada na camada
mais baixa e compartilhada (sheets_client.py), porque protege de saída
qualquer tela futura que reuse escrever_lote, adicionar_linhas, ou o
values().update() direto de registrar_na_monitoramento com texto livre.

A CONVENÇÃO DO PROJETO GRAVA @HANDLE COM O @ NA FRENTE, e por isso a
neutralização não pode simplesmente recusar ou cortar valor que comece com @:
teria que corromper toda linha de influenciador. A solução (a mesma que
Excel/Sheets usam quando alguém digita manualmente) é prefixar com apóstrofo,
que força texto e não aparece na célula.

Rodar:

    py testes\teste_trava_de_formula.py
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


def rodar():
    import sheets_client

    print("--- 1. os quatro caracteres perigosos ganham apóstrofo na frente ---")
    for perigoso in ("=SOMA(A1:A10)", "+SOMA(A1)", "-1+1", "@SOMA(A1)"):
        resultado = sheets_client._neutralizar_formula(perigoso)
        conferir(resultado == "'" + perigoso,
                 f"{perigoso!r} ganha apóstrofo na frente", resultado)

    print()
    print("--- 2. @handle, a convenção do próprio projeto, não é corrompido ---")
    # É o caso que uma trava ingênua ("recusar valor com @") quebraria: toda
    # linha de influenciador grava o handle com @ na frente.
    resultado = sheets_client._neutralizar_formula("@fulaninho")
    conferir(resultado == "'@fulaninho",
             "o @ do handle ganha apóstrofo, não é removido nem recusado",
             resultado)
    conferir("fulaninho" in resultado,
             "o texto do handle continua inteiro dentro do valor gravado",
             resultado)

    print()
    print("--- 3. texto comum não é tocado ---")
    for normal in ("PENDENTE", "01:30:00", "STORIES", "", "2026-09-04"):
        conferir(sheets_client._neutralizar_formula(normal) == normal,
                 f"{normal!r} passa sem mudança", normal)

    print()
    print("--- 4. valor que não é string passa direto, sem quebrar ---")
    conferir(sheets_client._neutralizar_formula(42) == 42,
             "número inteiro não é mexido")
    conferir(sheets_client._neutralizar_formula(None) is None,
             "None não é mexido")

    print()
    print("--- 5. as duas funções de escrita usam a trava ---")
    with open(os.path.join(BASE, "_drive_credenciais", "sheets_client.py"),
              encoding="utf-8") as f:
        fonte = f.read()
    conferir("_neutralizar_formula(valor)" in fonte.split("def escrever_lote")[1][:400],
             "escrever_lote passa cada valor pela neutralização")
    conferir("_neutralizar_formula(v) for v in linha" in fonte.split(
             "def adicionar_linhas")[1][:600],
             "adicionar_linhas neutraliza célula por célula, linha por linha")

    print()
    print("--- 6. o terceiro caminho de escrita (fora do sheets_client) também ---")
    # registrar_na_monitoramento grava direto por values().update(), sem passar
    # por escrever_lote nem adicionar_linhas. É o caminho que grava o @handle e
    # as horas de live DIGITADOS por uma pessoa, então precisa da mesma trava,
    # repetida aqui de propósito.
    with open(os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8") as f:
        fonte_fluxo = f.read()
    trecho = fonte_fluxo.split("def registrar_na_monitoramento")[1].split(
        "def _migrar_cabecalho_do_log")[0]
    conferir("sheets_client._neutralizar_formula(v)" in trecho,
             "registrar_na_monitoramento neutraliza a linha antes de gravar",
             "sem isso, o @handle e as horas de live digitados por uma pessoa "
             "iriam direto para o Sheets sem passar pela trava")


if __name__ == "__main__":
    print("=" * 74)
    print("  Nenhuma escrita no Sheets deixa passar texto que vira fórmula")
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
