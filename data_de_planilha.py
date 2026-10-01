# -*- coding: utf-8 -*-
"""
Ler DATA de célula de planilha, em vez de comparar texto.

POR QUE ESTE MÓDULO EXISTE (07/09/2026)

O auditor baixou duas telas do mesmo story, no mesmo dia, e elas saíram como
POST 1 e POST 2: "cada pacote de story conta como 1 post, ou seja, aqui era para
estar post 1 e 1". Ele estava certo, e o efeito é grave: a cota do contrato é
contada em POSTS, então duas telas do mesmo dia viravam duas entregas onde houve
uma, inflando a conferência de cota sem ninguém perceber.

A REGRA ESTAVA CERTA, A COMPARAÇÃO ESTAVA ERRADA. O programa grava "06/09/2026".
O Google Sheets reconhece aquilo como DATA, guarda como número de série e, na
leitura, devolve no formato de exibição da coluna: "06/09/26". Então
"06/09/26" != "06/09/2026", cada tela parecia um dia diferente, e o número
incrementava.

NUNCA COMPARAR DATA COMO TEXTO quando a planilha é a camada de guarda: o formato
de exibição é do Marketing, muda quando eles quiserem, e não é contrato de dado.

POR QUE VIROU MÓDULO SEPARADO, e não uma função dentro do fluxo de downloads:
a revisão de 07/09/2026 mostrou que a correção tinha ficado pela metade em dois
outros lugares, e um deles é o `escopo_e_entrega.py`, que é módulo PURO, importa
só `re` e é onde mora a contagem da cota. Importar o fluxo de downloads lá
dentro traria 5.339 linhas e as bibliotecas do Google para dentro do motor da
auditoria. Escrever uma segunda cópia da leitura seria pior: duas
implementações da mesma regra divergem na primeira mudança. Então a regra mora
aqui, sozinha, importando só o `datetime`.
"""
from datetime import date, datetime, timedelta

FORMATOS = ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y")

# O PISO DO NÚMERO DE SÉRIE, E POR QUE ELE NÃO É 1 (07/09/2026)
#
# A versão anterior aceitava qualquer número de 1 a 100000 como número de série
# do Sheets. A revisão pegou a consequência: um "6" digitado sozinho na coluna
# de data virava 05/01/1900, e "2026" virava 18/07/1905. Não caía no ramo de
# "data ilegível" que existe justamente para avisar, entrava como data válida,
# ordenava antes de todas as outras e ia para o texto que a pessoa cola no
# WhatsApp do Financeiro.
#
# 36526 é 01/01/2000 na convenção do Sheets. Número menor que isso, numa coluna
# de data desta auditoria, é dígito digitado por engano e não data: a auditoria
# cobre 2024 a 2026. Fica ILEGÍVEL de propósito, para o programa dizer que não
# sabe em vez de inventar 1900.
SERIAL_MINIMO = 36526          # 01/01/2000
SERIAL_MAXIMO = 73415          # 01/01/2101, teto de sanidade


def data_de_celula(valor):
    """A data que uma célula representa, ou None se não representa nenhuma.

    Aceita as grafias que aparecem no dado real (dois e quatro dígitos de ano,
    barra, hífen e ponto) e o número de série do Sheets, que é o que vem quando
    a leitura é feita sem formatação."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if not texto:
        return None
    for formato in FORMATOS:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    # NÚMERO DE SÉRIE DO SHEETS: dia 1 é 31/12/1899 na convenção deles.
    try:
        serial = float(texto.replace(",", "."))
    except ValueError:
        return None
    if SERIAL_MINIMO <= serial <= SERIAL_MAXIMO:
        return date(1899, 12, 30) + timedelta(days=int(serial))
    return None


def mesmo_dia(a, b):
    """Se duas células representam o mesmo dia. Falso quando alguma não é data.

    Falha para FALSO quando não dá para ler, e não para verdadeiro: dizer
    "mesmo dia" sem saber juntaria posts de dias diferentes num só número, que é
    o erro contrário e igualmente ruim."""
    da, db = data_de_celula(a), data_de_celula(b)
    return bool(da and db and da == db)


def chave_de_dia(valor):
    """O dia como chave estável, para agrupar e para deduplicar.

    Devolve "AAAA-MM-DD" quando a célula é data, e o TEXTO CRU quando não é.

    POR QUE CAI NO TEXTO CRU EM VEZ DE DEVOLVER None: quem chama usa isto como
    parte de chave de dedução. Devolver None para tudo o que é ilegível juntaria
    numa só chave linhas que não têm nada a ver, e aí o erro passa de contar
    duas vezes para contar uma vez de menos. O texto cru mantém cada célula
    estranha separada, que é o comportamento seguro: no pior caso conta igual ao
    que contava antes desta correção, nunca pior."""
    d = data_de_celula(valor)
    return d.isoformat() if d else str(valor or "").strip()
