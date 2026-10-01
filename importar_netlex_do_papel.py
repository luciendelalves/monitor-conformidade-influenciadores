# -*- coding: utf-8 -*-
r"""
Traz o Nº Contrato Netlex do papel de trabalho da auditoria para o registro
local, para a tela de Cadastro deixar de mostrar a coluna vazia para todos.

DE ONDE VEM (indicado pelo auditor em 03/09/2026, e conferido no Drive)

    pasta   12 - AUDITORIA INFLUENCIADORES / PAPEL DE TRABALHO
    arquivo Auditoria_Influenciadores_Pagamentos_e_Comissoes_ULTIMA_VERSAO.xlsx
    aba     Achado02_InconformidadeDatas, cabeçalho na linha 4
    colunas "Nº Contrato Netlex" e "Influenciador/Interveniente"

O QUE FOI MEDIDO ANTES DE IMPORTAR, em 996 linhas de pagamento:

    147 linhas com número de verdade, de 53 influenciadores, 54 números
    238 linhas com o texto "Não vinculado no Sankhya"
    611 linhas vazias

"NÃO VINCULADO NO SANKHYA" NÃO É NÚMERO, e não é importado como se fosse. Ele é
a constatação da própria auditoria de que o vínculo não existe no sistema, e
tratá-lo como número encheria a coluna de texto que não é contrato. Fica de
fora, e a contagem do que ficou de fora aparece no fim.

A JANELA FICA VAZIA, e isso é limitação da fonte, não descuido. A planilha do
papel de trabalho guarda datas de PAGAMENTO, não a vigência do contrato, então
não há de onde tirar início e fim. O número importado vale para o
influenciador, e a tela diz isso em vez de fingir que ele é de uma janela.

SÓ LEITURA NO DRIVE. Este arquivo baixa a planilha para uma pasta temporária e
escreve apenas no registro local. Nada é alterado no Drive.

RODAR DE NOVO É SEGURO: antes de gravar, ele confere o que já está registrado
com a mesma origem e o mesmo número, e não duplica.

    py importar_netlex_do_papel.py            confere e mostra o que faria
    py importar_netlex_do_papel.py --gravar   grava de verdade
"""
import collections
import os
import re
import sys
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import contratos_netlex

# Identificador do arquivo no Drive. Fica aqui, e não em arquivo de
# configuração, porque é a planilha FINAL de uma auditoria específica, não um
# endereço que se troca: apontar para outra planilha é outro trabalho.
ARQUIVO_NO_DRIVE = "188RcSzMMjZJhX7yMIzi0a2BmOp_-d1Uu"
ABA = "Achado02_InconformidadeDatas"
LINHA_DO_CABECALHO = 4
TITULO_NUMERO = "Nº Contrato Netlex"
TITULO_INFLUENCIADOR = "Influenciador/Interveniente"

# O que a fonte escreve quando o vínculo não existe. Não é número.
NAO_E_NUMERO = "não vinculado"


def _numero_limpo(valor):
    """Só dígitos contam. Devolve vazio para qualquer outra coisa."""
    texto = str(valor or "").strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto if re.fullmatch(r"\d+", texto) else ""


def ler_do_papel(caminho_xlsx):
    """Devolve {handle: [números]} e a contagem do que ficou de fora."""
    import openpyxl

    livro = openpyxl.load_workbook(caminho_xlsx, read_only=True, data_only=True)
    try:
        pagina = livro[ABA]
        linhas = [list(l) for l in pagina.iter_rows(values_only=True)]
    finally:
        livro.close()

    titulos = [str(c).strip() if c is not None else ""
               for c in linhas[LINHA_DO_CABECALHO - 1]]
    # CONFERE OS TÍTULOS ANTES DE LER, e desiste se não achar. Ler por posição
    # fixa numa planilha de terceiro é o que faz o programa importar a coluna
    # errada em silêncio quando alguém insere uma coluna.
    if TITULO_NUMERO not in titulos or TITULO_INFLUENCIADOR not in titulos:
        raise ValueError(
            "não achei as colunas esperadas na linha %d da aba %s. "
            "Títulos lidos: %s" % (LINHA_DO_CABECALHO, ABA, titulos[:8]))
    i_numero = titulos.index(TITULO_NUMERO)
    i_handle = titulos.index(TITULO_INFLUENCIADOR)

    por_handle = collections.defaultdict(list)
    fora = collections.Counter()
    for linha in linhas[LINHA_DO_CABECALHO:]:
        bruto = (str(linha[i_numero]).strip()
                 if i_numero < len(linha) and linha[i_numero] is not None else "")
        handle = (str(linha[i_handle]).strip()
                  if i_handle < len(linha) and linha[i_handle] is not None else "")
        if not handle:
            # CONTADO, e não descartado em silêncio: quem lê o relatório precisa
            # saber que a soma não fecha com o total de linhas da aba.
            fora["linha sem influenciador na aba"] += 1
            continue
        numero = _numero_limpo(bruto)
        if not numero:
            if NAO_E_NUMERO in bruto.lower():
                fora["não vinculado no Sankhya"] += 1
            elif bruto:
                fora["texto que não é número: %s" % bruto[:40]] += 1
            else:
                fora["coluna vazia"] += 1
            continue
        chave = contratos_netlex.normalizar_handle(handle)
        if numero not in por_handle[chave]:
            por_handle[chave].append(numero)
    return dict(por_handle), fora


def baixar():
    """Baixa a planilha final para uma pasta temporária. Só leitura no Drive."""
    import drive_client

    destino = os.path.join(tempfile.gettempdir(),
                           "netlex_papel_de_trabalho.xlsx")
    if not os.path.exists(destino):
        drive_client.download_file(ARQUIVO_NO_DRIVE, destino)
    return destino


def importar(por_handle, quem, gravar=False):
    """Grava o que ainda não está registrado. Devolve (gravados, já tinha)."""
    ja_registrados = set()
    for registro in contratos_netlex.ler():
        ja_registrados.add((
            contratos_netlex.normalizar_handle(registro.get("handle")),
            str(registro.get("numero_netlex") or "").strip()))

    gravados, repetidos = [], []
    for handle, numeros in sorted(por_handle.items()):
        for numero in numeros:
            if (handle, numero) in ja_registrados:
                repetidos.append((handle, numero))
                continue
            if gravar:
                contratos_netlex.gravar(
                    handle, "", "", numero, quem,
                    observacao="importado da aba %s da planilha final da "
                               "auditoria; a janela do contrato não consta lá"
                               % ABA,
                    origem=contratos_netlex.ORIGEM_PAPEL_DE_TRABALHO)
            gravados.append((handle, numero))
            ja_registrados.add((handle, numero))
    return gravados, repetidos


def main():
    de_verdade = "--gravar" in sys.argv
    caminho = baixar()
    por_handle, fora = ler_do_papel(caminho)

    # Pares, e não números: dois números aparecem em dois @ cada, então contar
    # números daria um total menor do que o de registros a gravar.
    pares = sum(len(v) for v in por_handle.values())
    numeros_distintos = len({n for v in por_handle.values() for n in v})
    print("=" * 74)
    print("  Nº Contrato Netlex, do papel de trabalho para o registro local")
    print("=" * 74)
    print()
    print("Fonte: %s, aba %s, cabeçalho na linha %d."
          % ("planilha final da auditoria", ABA, LINHA_DO_CABECALHO))
    print()
    print("  influenciadores com número:    %d" % len(por_handle))
    print("  números de contrato distintos: %d" % numeros_distintos)
    print("  pares influenciador + número:  %d" % pares)
    print()
    print("  O QUE FICOU DE FORA, e por quê:")
    for motivo, quantas in fora.most_common():
        print("     %5d  %s" % (quantas, motivo))
    print()

    # MAIS DE UM CONTRATO PARA O MESMO @ é o caso da renovação, e ele é
    # mostrado em vez de resolvido: qual contrato vale é leitura de contrato.
    varios = {h: n for h, n in por_handle.items() if len(n) > 1}
    if varios:
        print("  MAIS DE UM CONTRATO PARA O MESMO INFLUENCIADOR (%d):" % len(varios))
        for handle, numeros in sorted(varios.items()):
            print("     @%-26s %s" % (handle, ", ".join(numeros)))
        print("     Os dois ficam registrados. O programa não escolhe qual vale.")
        print()

    # O MESMO NÚMERO EM DOIS @ costuma ser erro de digitação no handle, e vale
    # avisar porque quem corrige é o Marketing, não o programa.
    de_quem = collections.defaultdict(list)
    for handle, numeros in por_handle.items():
        for numero in numeros:
            de_quem[numero].append(handle)
    compartilhados = {n: h for n, h in de_quem.items() if len(h) > 1}
    if compartilhados:
        print("  MESMO NÚMERO EM MAIS DE UM @ (%d), vale conferir a grafia:"
              % len(compartilhados))
        for numero, handles in sorted(compartilhados.items()):
            print("     %-8s %s" % (numero, ", ".join("@" + h for h in sorted(handles))))
        print()

    quem = "importação do papel de trabalho"
    gravados, repetidos = importar(por_handle, quem, gravar=de_verdade)
    if de_verdade:
        print("  GRAVADOS: %d registro(s). Já estavam: %d."
              % (len(gravados), len(repetidos)))
        print("  Arquivo: %s" % contratos_netlex.ARQUIVO)
    else:
        print("  ENSAIO, nada foi gravado. Gravaria %d registro(s), e %d já "
              "estão lá." % (len(gravados), len(repetidos)))
        print("  Para gravar: py importar_netlex_do_papel.py --gravar")
    print()


if __name__ == "__main__":
    main()
