# -*- coding: utf-8 -*-
r"""
O que existe no Drive: árvore, ou contagem de nomes de pasta por nível.

SOMENTE LEITURA. Zero chamada ao Instagram.

    py ferramentas\ver_drive.py arvore                     árvore do Drive de teste
    py ferramentas\ver_drive.py arvore @maumauzk           só as pastas dele
    py ferramentas\ver_drive.py grafias                    conta nomes de pasta, ATIVOS
    py ferramentas\ver_drive.py grafias todos              inclui quem saiu da casa
    py ferramentas\ver_drive.py procurar story             onde há pasta com esse nome

O MODO `grafias` É O QUE DECIDE NOME DE PASTA, e ele existe porque nome de pasta
neste projeto sai de medição e não de escolha. Em 01/09/2026 ele mostrou que o
padrão do Marketing é "story", minúsculo e no singular (411 contra 133 de
"stories"), derrubando um rascunho que usava "Link" e "Orgânico".

QUAL DRIVE ELE OLHA: o que estiver configurado. No layout de teste, a nossa raiz;
no do Marketing, a deles. O modo `grafias` só faz sentido no do Marketing, então
ele avisa quando está olhando o de teste.
"""
import re
import sys
from collections import Counter

from _base import (cabecalho, conteudo_por_leitura, contagem, handles_do_cadastro,
                   linha, pedir_argumento, secao, subpastas_por_leitura,
                   PASTA_MIME, RAIZ_MARKETING)

import fluxo_downloads as fluxo

E_DATA = re.compile(r"^\s*\d{2}[/.\-]\d{2}")


def raiz_em_uso():
    import drive_client
    raiz = fluxo._pasta_raiz_drive()
    try:
        info = drive_client._com_retentativas(
            lambda: drive_client.get_service().files().get(
                fileId=raiz, fields="name", supportsAllDrives=True).execute())
        return raiz, info.get("name") or "(sem nome)"
    except Exception as e:
        return raiz, f"(não li o nome: {str(e)[:50]})"


def desenhar(id_pasta, nome, recuo=0, limite=8):
    print("   " + "   " * recuo + nome + "/")
    if recuo >= limite:
        print("   " + "   " * (recuo + 1) + "...")
        return
    itens = conteudo_por_leitura(id_pasta)
    pastas = sorted((i for i in itens if i.get("mimeType") == PASTA_MIME),
                    key=lambda x: x.get("name", ""))
    arquivos = sorted((i for i in itens if i.get("mimeType") != PASTA_MIME),
                      key=lambda x: x.get("name", ""))
    for p in pastas:
        desenhar(p["id"], p["name"], recuo + 1, limite)
    for a in arquivos:
        print("   " + "   " * (recuo + 1) + a["name"])


def modo_arvore(alvo=None):
    raiz, nome = raiz_em_uso()
    cabecalho("Árvore do Drive", f"{nome}   (layout: {fluxo.LAYOUT_PASTAS})")
    if not alvo:
        desenhar(raiz, "(raiz)")
        return

    procurado = fluxo.chave_de_pasta(alvo)
    achadas = []

    def procurar(id_pasta, caminho, resta=7):
        for p in subpastas_por_leitura(id_pasta):
            novo = caminho + [p["name"]]
            if fluxo.chave_de_pasta(p["name"]) == procurado:
                achadas.append((" / ".join(novo), p["id"]))
            elif resta > 0:
                procurar(p["id"], novo, resta - 1)

    procurar(raiz, [])
    linha("pastas encontradas", len(achadas))
    if not achadas:
        print()
        print("   Nenhuma. Se era esperada, confira o @ e o layout em uso.")
        return
    for caminho, ident in achadas:
        print()
        print(f"   em: {caminho}")
        desenhar(ident, "@" + procurado)


def modo_grafias(recorte="ativos"):
    raiz, nome = raiz_em_uso()
    cabecalho("Nomes de pasta, por nível",
              f"{nome}   recorte: {recorte}")
    if raiz != RAIZ_MARKETING:
        print("   AVISO: esta não é a raiz do Marketing. As grafias que")
        print("   interessam são as DELES; aqui você vai contar as nossas.")
        print()

    filtro = None
    if recorte == "ativos":
        filtro, total = handles_do_cadastro(so_ativos=True)
        if filtro is None:
            print("   Não consegui ler o cadastro. Rodando sem recorte.")
        else:
            linha("influenciadores ATIVOS no cadastro", f"{len(filtro)} de {total}")
            print("   LIMITAÇÃO: a coluna STATUS diz 79 ATIVO e a operação")
            print("   trabalha com 45. Nenhum recorte da planilha dá 45.")
            print()

    nivel_influ = Counter()
    nivel_data = Counter()
    nivel_tipo = Counter()
    vistos, ignorados = set(), set()

    for bet in subpastas_por_leitura(raiz):
        for ano in subpastas_por_leitura(bet["id"]):
            for mes in subpastas_por_leitura(ano["id"]):
                for influ in subpastas_por_leitura(mes["id"]):
                    chave = fluxo.chave_de_pasta(influ["name"])
                    if filtro is not None and chave not in filtro:
                        ignorados.add(chave)
                        continue
                    vistos.add(chave)
                    nivel_influ[influ["name"].strip()] += 1
                    for dentro in subpastas_por_leitura(influ["id"]):
                        nivel_data[dentro["name"].strip()] += 1
                        for fundo in subpastas_por_leitura(dentro["id"]):
                            nivel_tipo[fundo["name"].strip()] += 1

    secao("influenciadores percorridos")
    linha("com pasta", len(vistos))
    if ignorados:
        linha("ignorados por não estarem ATIVOS", len(ignorados))

    secao("nomes DENTRO do influenciador (nível da data)")
    contagem("nomes", nivel_data, limite=15)

    secao("nomes MAIS FUNDO (dentro da data)")
    contagem("nomes", nivel_tipo, limite=30)

    secao("leitura do resultado")
    palavras = Counter({k: v for k, v in nivel_tipo.items() if not E_DATA.match(k)})
    if palavras:
        mais_usado, quantas = palavras.most_common(1)[0]
        print(f"   nome de pasta mais usado nesse nível: {mais_usado!r} ({quantas}x)")
        print("   é esse que o programa deve CRIAR quando faltar; os outros")
        print("   entram como grafia aceita na hora de PROCURAR.")


def modo_procurar(alvo):
    raiz, nome = raiz_em_uso()
    cabecalho(f"Onde existe pasta chamada {alvo!r}", nome)
    procurado = fluxo.chave_de_pasta(alvo)
    achadas = []

    def procurar(id_pasta, caminho, resta=8):
        for p in subpastas_por_leitura(id_pasta):
            novo = caminho + [p["name"]]
            if fluxo.chave_de_pasta(p["name"]) == procurado:
                achadas.append(" / ".join(novo))
            if resta > 0:
                procurar(p["id"], novo, resta - 1)

    procurar(raiz, [])
    linha("encontradas", len(achadas))
    for caminho in achadas[:60]:
        print(f"      {caminho}")
    if len(achadas) > 60:
        print(f"      ... e mais {len(achadas) - 60}")


if __name__ == "__main__":
    modo = pedir_argumento(1, "arvore", "modo (arvore, grafias, procurar)")
    if modo == "arvore":
        modo_arvore(sys.argv[2] if len(sys.argv) > 2 else None)
    elif modo == "grafias":
        modo_grafias(pedir_argumento(2, "ativos"))
    elif modo == "procurar":
        modo_procurar(pedir_argumento(2, None, "nome da pasta"))
    else:
        raise SystemExit(f"Modo desconhecido: {modo!r}. "
                         f"Use arvore, grafias ou procurar.")
