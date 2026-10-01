# -*- coding: utf-8 -*-
r"""
Peças comuns das ferramentas de conferência.

POR QUE ESTA PASTA EXISTE (02/09/2026)

Num único dia de trabalho foram escritos cerca de quinze scripts descartáveis
para responder perguntas de conferência: o que existe no Drive, o que a análise
decidiu e por quê, o que há na fila e no log, o que o OCR leu num arquivo,
quantas peças citam tal termo.

Metade delas são perguntas que voltam. Reescrever o script a cada vez custa
minutos que somam, e pior: cada versão nova pode medir uma coisa ligeiramente
diferente da anterior, o que já aconteceu. Duas medições do mesmo Drive no mesmo
dia deram números diferentes porque uma contava influenciador que saiu da casa e
a outra não.

Ferramenta versionada resolve os dois: responde em segundos e responde SEMPRE a
mesma pergunta, com o recorte escrito no código e não na memória de quem rodou.

REGRA DESTA PASTA: tudo aqui é SOMENTE LEITURA, com uma exceção que está no nome
e no cabeçalho dela (limpar_teste.py). Ferramenta de conferência que escreve por
acidente é pior que ferramenta nenhuma.

E NENHUMA delas fala com o Instagram. A chamada ao Instagram é o recurso escasso
do programa, e conferência não pode gastá-lo.
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "_drive_credenciais"))

PASTA_MIME = "application/vnd.google-apps.folder"

# A raiz do Drive do Marketing, escrita aqui para poder ser RECUSADA quando uma
# ferramenta que escreve for apontada para ela por engano.
RAIZ_MARKETING = "1_tKB4uZsscPdzhKH8Oi9SNb1hiriwEt0"


def cabecalho(titulo, detalhe=""):
    print("=" * 74)
    print(f"  {titulo}")
    if detalhe:
        print(f"  {detalhe}")
    print("=" * 74)
    print()


def secao(titulo):
    print()
    print(f"--- {titulo} ---")


def linha(rotulo, valor, recuo=3):
    print(" " * recuo + f"{rotulo}: {valor}")


def contagem(titulo, contador, limite=20, recuo=3):
    """Imprime um Counter em ordem, com o total."""
    total = sum(contador.values())
    print(" " * recuo + f"{titulo} (total {total}):")
    for chave, quantas in contador.most_common(limite):
        print(" " * (recuo + 3) + f"{quantas:>5}x  {chave}")
    if len(contador) > limite:
        print(" " * (recuo + 3) + f"... e mais {len(contador) - limite} valores")


def pedir_argumento(indice, padrao=None, nome="argumento"):
    """Argumento da linha de comando, com padrão. Vazio devolve o padrão."""
    if len(sys.argv) > indice and str(sys.argv[indice]).strip():
        return sys.argv[indice].strip()
    if padrao is None:
        raise SystemExit(f"Falta o {nome}. Veja o cabeçalho deste arquivo.")
    return padrao


def confirmar_drive_de_teste():
    """Devolve (id_da_raiz, nome). Interrompe se não for o Drive de teste.

    Confere TRÊS coisas, e cada uma pega um erro diferente: o layout em uso, o
    identificador da raiz, e o NOME dela. Só o identificador não basta, porque
    apontar o arquivo de configuração para outro lugar é uma linha de texto."""
    import drive_client
    import fluxo_downloads as fluxo

    if fluxo.LAYOUT_PASTAS == fluxo.LAYOUT_MARKETING:
        raise SystemExit("RECUSADO: o layout em uso é o do MARKETING.")
    raiz = fluxo._pasta_raiz_drive()
    if raiz == RAIZ_MARKETING:
        raise SystemExit("RECUSADO: a raiz configurada é a do Marketing.")
    try:
        info = drive_client._com_retentativas(
            lambda: drive_client.get_service().files().get(
                fileId=raiz, fields="name", supportsAllDrives=True).execute())
        nome = info.get("name") or ""
    except Exception as e:
        raise SystemExit(f"RECUSADO: não confirmei o nome da raiz: {str(e)[:120]}")
    if "TESTE" not in nome.upper():
        raise SystemExit(f"RECUSADO: a raiz {nome!r} não tem TESTE no nome.")
    return raiz, nome


def subpastas_por_leitura(id_pai):
    """Subpastas usando o token de LEITURA, que vê o Drive inteiro.

    Existe porque o token de escrita é do escopo drive.file e só vê o que o
    próprio programa criou. Para CONFERIR o que existe de verdade, a leitura é a
    fonte certa; foi ela que provou, em 02/09/2026, que cinco pastas que o
    programa não conseguia remover estavam realmente vazias."""
    import drive_client
    itens, token = [], None
    while True:
        resp = drive_client._com_retentativas(
            lambda: drive_client.get_service().files().list(
                q=f"'{id_pai}' in parents and trashed = false and "
                  f"mimeType = '{PASTA_MIME}'",
                fields="nextPageToken, files(id,name)",
                pageSize=200, supportsAllDrives=True,
                includeItemsFromAllDrives=True, pageToken=token,
            ).execute())
        itens.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            break
    return itens


def conteudo_por_leitura(id_pai):
    """Tudo (arquivo e pasta) usando o token de leitura."""
    import drive_client
    itens, token = [], None
    while True:
        resp = drive_client._com_retentativas(
            lambda: drive_client.get_service().files().list(
                q=f"'{id_pai}' in parents and trashed = false",
                fields="nextPageToken, files(id,name,mimeType,size)",
                pageSize=200, supportsAllDrives=True,
                includeItemsFromAllDrives=True, pageToken=token,
            ).execute())
        itens.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            break
    return itens


def handles_do_cadastro(so_ativos=True):
    """@ do cadastro do Marketing. (conjunto, total_no_cadastro).

    O RECORTE PADRÃO É SÓ OS ATIVOS, e isso vem de um erro real: a primeira
    varredura do Drive, em 01/09/2026, contou os 120 primeiros influenciadores
    que apareceram nas pastas de 2026, e o auditor apontou que muita gente ali
    não pertence mais à casa. Pasta de quem saiu registra a grafia de outra
    época. Com o recorte nos ativos os números mudaram de verdade: "stories"
    passou de 2 para 93.

    LIMITAÇÃO CONHECIDA, registrada para o número não ser usado como se fosse
    exato: a coluna STATUS dizia 79 ATIVO em 31/08/2026 e o auditor informou que
    a operação trabalha com 45. Nenhum recorte da planilha dá 45."""
    import fluxo_downloads as fluxo
    import sheets_client

    planilha = fluxo.ler_identificador(fluxo.ARQUIVO_CADASTRO_ID)
    if not planilha:
        return None, 0
    valores = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha, range=f"'{fluxo.ABA_CADASTRO}'!A1:T",
        ).execute()).get("values", [])
    if not valores:
        return None, 0
    cab = [str(c).strip().upper() for c in valores[0]]
    i_influ = cab.index("INFLU") if "INFLU" in cab else None
    i_status = cab.index("STATUS") if "STATUS" in cab else None
    if i_influ is None:
        return None, 0

    achados, total = set(), 0
    for linha_ in valores[1:]:
        def campo(i):
            return str(linha_[i]).strip() if i is not None and len(linha_) > i else ""
        chave = fluxo.chave_de_pasta(campo(i_influ))
        if not chave:
            continue
        total += 1
        if not so_ativos or campo(i_status).upper() == "ATIVO":
            achados.add(chave)
    return achados, total
