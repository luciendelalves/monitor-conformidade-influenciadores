# -*- coding: utf-8 -*-
"""
Cria uma cópia VAZIA da planilha "Marketing de Influência" do Marketing, com a
mesma cara mas sem nenhum dado, pra servir de campo de testes da automação sem
encostar na planilha real deles.

Como funciona: parte do arquivo original e APAGA as linhas de dado, em vez de
montar uma planilha nova do zero. Foi assim que passou a ser feito depois que
a primeira versão, que remontava tudo à mão, perdeu cores e formatação. Copiar
e esvaziar preserva tudo de graça: cores, bordas, colunas escondidas, listas
de seleção, formatação condicional e largura de coluna.

O que NÃO é copiado: nenhuma linha de dado. A planilha real tem dados de
influenciadores, e o objetivo aqui é justamente ter onde testar sem tocar
neles.

Uso:
    py criar_modelo_vazio_marketing.py                 (usa o arquivo em Downloads)
    py criar_modelo_vazio_marketing.py "caminho.xlsx"  (usa outro arquivo de origem)
"""
import io
import os
import sys
import warnings

import openpyxl

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

ORIGEM_PADRAO = os.path.join(os.environ["USERPROFILE"], "Downloads",
                             "Marketing de Influência.xlsx")
DESTINO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "TESTE - Marketing de Influência (modelo vazio).xlsx")

# Abas com dado de verdade, e a linha do cabeçalho de cada uma.
ABAS_COM_DADOS = {"Monitoramento": 1, "Dados_influ": 1}

# Quantas linhas vazias deixar abaixo do cabeçalho. Elas mantêm a formatação
# e as listas de seleção prontas pra quem for preencher, sem carregar as 23 mil
# linhas da original.
LINHAS_VAZIAS = 500


def esvazia(ws, linha_cab):
    """Apaga o conteúdo das linhas de dado, preservando a formatação delas.

    Limpa também o hiperlink da célula, e não só o texto: sem isso, links reais
    de afiliado e de pastas do Drive dos influenciadores voltavam a aparecer no
    arquivo salvo, porque o hiperlink fica guardado à parte do valor."""
    ultima = ws.max_row or linha_cab
    apagadas = 0
    for linha in ws.iter_rows(min_row=linha_cab + 1, max_row=ultima):
        for celula in linha:
            if celula.value is not None or celula.hyperlink is not None:
                celula.value = None
                celula.hyperlink = None
                apagadas += 1
    # tira o excesso de linhas, deixando só um espaço de trabalho
    limite = linha_cab + LINHAS_VAZIAS
    if ultima > limite:
        ws.delete_rows(limite + 1, ultima - limite)
    return apagadas, ultima - linha_cab


def main():
    origem = sys.argv[1] if len(sys.argv) > 1 else ORIGEM_PADRAO
    if not os.path.exists(origem):
        raise SystemExit(f"Não achei o arquivo de origem: {origem}")

    print(f"Origem : {origem}")
    print("Abrindo (a original é grande, isso demora um pouco)...")
    wb = openpyxl.load_workbook(origem)

    for nome in wb.sheetnames:
        ws = wb[nome]
        linha_cab = ABAS_COM_DADOS.get(nome)
        if linha_cab:
            celulas, linhas = esvazia(ws, linha_cab)
            print(f"  {nome:16} {linhas} linhas de dado esvaziadas ({celulas} células)")
        else:
            print(f"  {nome:16} mantida como está (não tem dado de influenciador)")

    print("\nSalvando...")
    wb.save(DESTINO)
    print(f"Salvo em: {DESTINO}")

    print("\nConferindo o arquivo salvo...")
    conf = openpyxl.load_workbook(DESTINO)
    for nome, linha_cab in ABAS_COM_DADOS.items():
        ws = conf[nome]
        com_dado = [r for r in range(linha_cab + 1, (ws.max_row or 0) + 1)
                    if any(ws.cell(row=r, column=c).value is not None
                           or ws.cell(row=r, column=c).hyperlink is not None
                           for c in range(1, (ws.max_column or 0) + 1))]
        if com_dado:
            raise SystemExit(f"[erro] sobrou dado em {nome}, linhas {com_dado[:5]}")
        cab = ws.cell(row=linha_cab, column=2)
        preenchido = cab.fill.fgColor.rgb if cab.fill.patternType == "solid" else "sem cor"
        listas = len(list(ws.data_validations.dataValidation))
        escondidas = [k for k, v in ws.column_dimensions.items() if v.hidden]
        print(f"  {nome:16} 0 linhas de dado | cor do cabeçalho: {preenchido} | "
              f"{listas} lista(s) | colunas escondidas: {escondidas or 'nenhuma'}")


if __name__ == "__main__":
    main()
