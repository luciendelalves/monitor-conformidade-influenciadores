# -*- coding: utf-8 -*-
"""
Rotulo de botao nao carrega emoji, e nome de icone existe de verdade.

POR QUE ESTE TESTE EXISTE (08/09/2026)

Na reforma visual a decisao foi trocar emoji por icone do Streamlit
(`icon=":material/nome:"`). Emoji e desenhado pela fonte do sistema
operacional de quem olha: muda de forma e de cor entre Windows, telefone e
navegador, vem quase sempre em cor cheia que briga com a paleta, e nao alinha
com a linha de base do texto do botao.

A troca foi feita TRES vezes e ficou incompleta as tres:

1. Um script com `count=1` trocou so a primeira ocorrencia de cada arquivo, e
   deixou passar o segundo ramo de um ternario.
2. A varredura seguinte usava lista de emoji escrita a mao. O 📂 (U+1F4C2, pasta
   aberta) nao estava nela, porque a lista tinha 📁 (U+1F4C1, pasta fechada). O
   auditor viu na tela o que a varredura jurava nao existir.
3. A terceira usava faixa de codigo (0x1F300-0x1FAFF etc). O ↩ e U+21A9, fora
   de qualquer faixa de emoji, e passou tambem.

O erro comum as tres e o mesmo: tentar ENUMERAR o que e emoji. Aqui a pergunta
e virada. A regra passa a ser a categoria Unicode `So` ("Symbol, other"), que e
o que o proprio Unicode diz ser simbolo, mais o seletor de variacao U+FE0F.
Nada de lista.

E a mira e o ROTULO DE WIDGET, nao o arquivo inteiro. As duas primeiras versoes
deste teste liam o texto todo e reprovavam por causa de prosa: comentario de
Python, comentario de CSS dentro do bloco de estilo, e o vocabulario ✅/🚫 da
tela do Financeiro, que e copiado de proposito do papel de trabalho entregue
(quem le o papel e quem le a tela tem de ver a mesma coisa) e portanto NAO e
defeito. Rotulo de widget nao tem essa ambiguidade.

A segunda conferencia e sobre o remedio, nao sobre o defeito: nome de icone
invalido explode so na hora em que aquele botao aparece na tela. Botao raro
(o de devolver peca para a analise, por exemplo) so aparece em situacao rara,
entao quem descobriria o erro de digitacao seria o analista, no meio do
trabalho. O Streamlit publica a lista dos 4.262 nomes validos; conferir contra
ela custa um teste.

    py testes\teste_telas_sem_emoji_em_botao.py
"""
import ast
import glob
import os
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

# Widgets cujo primeiro argumento e o rotulo que a pessoa le, e que aceitam
# `icon=` no Streamlit 1.59.2 (conferido por inspect.signature).
WIDGETS_COM_ROTULO = {
    "button",
    "link_button",
    "form_submit_button",
    "download_button",
    "popover",
    "expander",
    "Page",
}

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}")
        if detalhe:
            for linha in str(detalhe).splitlines():
                print(f"         {linha}")
        falhas.append(descricao)


def simbolos(texto):
    """Devolve os caracteres que o Unicode classifica como simbolo.

    `So` e "Symbol, other", a categoria dos emoji e dos pictogramas. Vem do
    proprio Unicode, entao pega tambem o que for adicionado depois, sem
    ninguem precisar manter lista. U+FE0F entra separado porque e o seletor
    que pede a forma colorida e sozinho tem categoria de marca, nao de
    simbolo."""
    return sorted({c for c in texto if unicodedata.category(c) == "So" or c == "️"})


def texto_do_no(no):
    """Le o rotulo quando ele e escrito na mao no codigo.

    Aceita texto simples e f-string. Na f-string devolve so os trechos
    literais, que e onde emoji e escrito; o que vem de variavel nao da para
    conferir aqui e nao e onde o defeito mora. Devolve None quando o rotulo
    e calculado, porque ai o teste nao tem o que dizer."""
    if isinstance(no, ast.Constant) and isinstance(no.value, str):
        return no.value
    if isinstance(no, ast.JoinedStr):
        pedacos = [p.value for p in no.values
                   if isinstance(p, ast.Constant) and isinstance(p.value, str)]
        return "".join(pedacos) if pedacos else None
    return None


def arquivos_de_tela():
    nomes = ["painel.py", "painel_trabalhador.py"]
    caminhos = [os.path.join(BASE, n) for n in nomes]
    caminhos += sorted(glob.glob(os.path.join(BASE, "pages", "*.py")))
    return [c for c in caminhos if os.path.isfile(c)]


def rotulos_e_icones(caminho):
    """Devolve (rotulos, icones) achados nas chamadas de widget do arquivo."""
    arvore = ast.parse(open(caminho, encoding="utf-8").read())
    rotulos, icones = [], []
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        alvo = no.func
        nome = alvo.attr if isinstance(alvo, ast.Attribute) else (
            alvo.id if isinstance(alvo, ast.Name) else None)

        # `atalhos` e um ajudante da tela de Downloads que recebe tuplas
        # (rotulo, url, icone) e monta um link_button por tupla. O rotulo dele
        # nao aparece como argumento de widget, entao ficaria fora da
        # conferencia, e foi exatamente ali que tres dos 📂 sobreviveram.
        if nome == "atalhos":
            for arg in no.args:
                if not isinstance(arg, ast.Tuple) or not arg.elts:
                    continue
                texto = texto_do_no(arg.elts[0])
                if texto is not None:
                    rotulos.append((arg.lineno, "atalhos", texto))
                if len(arg.elts) > 2:
                    valor = texto_do_no(arg.elts[2])
                    if valor:
                        icones.append((arg.lineno, valor))
            continue

        if nome not in WIDGETS_COM_ROTULO:
            continue

        rotulo = None
        if no.args:
            rotulo = texto_do_no(no.args[0])
        for palavra in no.keywords:
            if palavra.arg in ("label", "title"):
                rotulo = texto_do_no(palavra.value) or rotulo
            if palavra.arg in ("icon", "page_icon"):
                valor = texto_do_no(palavra.value)
                if valor:
                    icones.append((no.lineno, valor))
        if rotulo is not None:
            rotulos.append((no.lineno, nome, rotulo))
    return rotulos, icones


def rodar():
    telas = arquivos_de_tela()
    conferir(len(telas) >= 5, f"achei {len(telas)} arquivos de tela para conferir")

    print()
    print("--- 1. nenhum rotulo de widget carrega emoji ---")
    achados, total_rotulos = [], 0
    for caminho in telas:
        curto = os.path.relpath(caminho, BASE)
        rotulos, _ic = rotulos_e_icones(caminho)
        total_rotulos += len(rotulos)
        for linha, widget, rotulo in rotulos:
            simb = simbolos(rotulo)
            if simb:
                codigos = " ".join(hex(ord(c)) for c in simb)
                achados.append(f"{curto}:{linha}  st.{widget}  {codigos}  {rotulo!r}")
    # TETO BAIXADO DE 40 PARA 30 EM 14/09/2026: a limpeza de tela do mesmo dia
    # (Organizado no Drive, Validação Regulatória inteira, Netlex) tirou
    # dezenas de rótulos de verdade, e o número caiu para 39. O piso continua
    # existindo só para pegar a leitura por ast quebrando (0 ou poucos
    # rótulos), não para travar toda vez que uma tela fica mais simples.
    conferir(total_rotulos >= 30,
             f"li {total_rotulos} rotulos escritos na mao",
             "poucos rotulos: a leitura por ast provavelmente parou de achar as "
             "chamadas, e um teste que nao le nada passa sempre")
    conferir(not achados,
             "nenhum rotulo de widget tem simbolo Unicode",
             "\n".join(achados) + ("\n\nTroque por icon=\":material/nome:\"." if achados else ""))

    print()
    print("--- 2. todo nome de icone existe no Streamlit instalado ---")
    from streamlit.material_icon_names import ALL_MATERIAL_ICONS
    validos = set(ALL_MATERIAL_ICONS)
    conferir(len(validos) > 1000, f"a lista do Streamlit tem {len(validos)} nomes")

    ruins, total_icones = [], 0
    for caminho in telas:
        curto = os.path.relpath(caminho, BASE)
        _rot, icones = rotulos_e_icones(caminho)
        for linha, valor in icones:
            if not valor.startswith(":material/"):
                # Emoji tambem e aceito pelo Streamlit em `icon=`, e e
                # exatamente o que a reforma esta tirando da tela.
                ruins.append(f"{curto}:{linha}  icon={valor!r} nao e :material/nome:")
                continue
            total_icones += 1
            nome = valor[len(":material/"):].rstrip(":")
            if nome not in validos:
                ruins.append(f"{curto}:{linha}  :material/{nome}: nao existe na lista")
    conferir(total_icones >= 10, f"achei {total_icones} icones do Streamlit em uso")
    conferir(not ruins, "todo icone usado e um nome valido", "\n".join(ruins))


if __name__ == "__main__":
    print("=" * 74)
    print("  Rotulo de botao sem emoji, e nome de icone que existe")
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
