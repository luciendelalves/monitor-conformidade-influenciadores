# -*- coding: utf-8 -*-
"""
O disfarce de navegador para de recuar por certificado, sem coletar
certificado à mão em cada máquina.

POR QUE ESTE TESTE EXISTE (21/09/2026)

Medido em 21/09/2026, ao investigar o aviso do Instagram na máquina da
Responsável A: o certificado do antivírus corporativo (Kaspersky Endpoint
Security) que a rede confia é DIFERENTE em cada máquina (número de série
próprio, gerado localmente). O disfarce de navegador do programa
(`opcoes_de_disfarce`) usa a biblioteca `curl_cffi`, que tem sua própria
lista de certificados confiáveis, separada da lista do Windows, e por isso
recusa a conexão numa rede com esse tipo de inspeção.

Em vez de pedir para exportar e colar o certificado de cada máquina nova,
`_ca_bundle_com_repositorio_windows` lê TUDO que o Windows desta própria
máquina já confia e soma à lista pública (certifi), sem precisar saber o
nome do certificado. Isso pega o do Kaspersky sozinho, e continuaria
pegando mesmo se a empresa trocasse de antivírus.

Este teste roda de verdade (não é só estrutural): ler o repositório do
Windows e montar o arquivo não fala com o Instagram nem gasta nenhuma cota,
é só leitura local. O que ele NÃO prova é se o curl_cffi de fato usa esse
arquivo pela variável CURL_CA_BUNDLE nesta versão dele: isso só um teste
contra a rede afetada, de verdade, confirma.

Rodar:

    py testes\\teste_ca_bundle_windows.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fluxo_downloads as fluxo

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    import certifi
    import ssl

    print("--- 1. monta o pacote, sem falar com o Instagram ---")
    fluxo._caminho_ca_bundle = None  # começa do zero, não usa cache de outro teste
    caminho = fluxo._ca_bundle_com_repositorio_windows()

    esta_no_windows = os.name == "nt" and hasattr(ssl, "enum_certificates")
    if not esta_no_windows:
        conferir(caminho is None,
                 "fora do Windows, devolve None em vez de quebrar")
        print("  (fora do Windows, o resto deste teste não se aplica)")
        return

    conferir(caminho is not None, "devolve um caminho de arquivo, nesta máquina Windows")
    conferir(os.path.exists(caminho or ""), "e o arquivo existe de verdade")

    texto_publico = open(certifi.where(), encoding="utf-8").read()
    texto_pacote = open(caminho, encoding="utf-8").read()
    qtd_publicos = texto_publico.count("BEGIN CERTIFICATE")
    qtd_pacote = texto_pacote.count("BEGIN CERTIFICATE")
    conferir(qtd_pacote > qtd_publicos,
             "o pacote tem MAIS certificados do que o certifi sozinho",
             f"certifi {qtd_publicos}, pacote {qtd_pacote}")

    print()
    print("--- 2. os certificados do pacote são válidos, não só texto colado ---")
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        import re
        blocos = re.findall(
            r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
            texto_pacote, re.S)
        conferir(len(blocos) == qtd_pacote,
                 "cada certificado no arquivo é um bloco PEM completo",
                 f"{len(blocos)} blocos contra {qtd_pacote} cabeçalhos")
        validos = 0
        for b in blocos:
            try:
                x509.load_pem_x509_certificate(b.encode(), default_backend())
                validos += 1
            except Exception:
                pass
        conferir(validos == len(blocos),
                 "todos os certificados do pacote são certificados válidos de verdade",
                 f"{validos} de {len(blocos)} validaram")
    except ImportError:
        print("  (biblioteca 'cryptography' não instalada, pulei esta conferência)")

    print()
    print("--- 3. não reconstrói a cada chamada ---")
    caminho2 = fluxo._ca_bundle_com_repositorio_windows()
    conferir(caminho2 == caminho,
             "a segunda chamada devolve o mesmo caminho, sem reconstruir",
             f"{caminho} vs {caminho2}")

    print()
    print("--- 4. o disfarce liga a variável de ambiente ---")
    os.environ.pop("CURL_CA_BUNDLE", None)
    fluxo.opcoes_de_disfarce()
    conferir(os.environ.get("CURL_CA_BUNDLE") == caminho,
             "opcoes_de_disfarce() aponta CURL_CA_BUNDLE para o pacote",
             os.environ.get("CURL_CA_BUNDLE"))


if __name__ == "__main__":
    print("=" * 74)
    print("  Pacote de certificados com o repositório do Windows")
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
