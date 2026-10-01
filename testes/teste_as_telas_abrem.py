# -*- coding: utf-8 -*-
"""
As quatro telas abrem sem estourar erro.

POR QUE ESTE ARQUIVO EXISTE (07/09/2026)

Os outros 51 testes cobrem a LOGICA, e nao a tela. Medido: 11.185 linhas de
modulo puro contra 4.361 de tela, e 50 dos 51 testes rodam sem importar o
Streamlit. Isso e bom para a arquitetura e deixa um buraco: uma pagina podia
quebrar ao desenhar e passar por toda a bateria.

O buraco nao era teorico. No mesmo dia foram achados dois defeitos que viviam
exatamente ali:

  - o atalho iniciar_validacao_influenciadores.bat subia UMA das cinco telas,
    e nao o painel.py. Ninguem notou por semanas
  - textos obsoletos citando a tela "Cronograma e Pagamento", que foi apagada

Nenhum teste podia pegar os dois, porque nenhum teste abria tela.

COMO ELE PASSA PELA BARREIRA DE LOGIN: `acesso.exigir_login()` deixa passar
quando o login NAO esta configurado e o programa escuta so a propria maquina.
Essa e uma configuracao real e suportada (esta no INSTALAR.md, item 6.4), nao um
truque de teste. O teste forca esses dois estados e roda a pagina.

O QUE ELE NAO PROVA: que a tela esta CERTA. Ele prova que ela desenha sem
estourar. E o degrau mais baixo, e mesmo assim e o degrau que faltava.

CUSTO: as paginas leem as planilhas de verdade ao abrir, entao este teste faz
chamada ao Google Sheets. NAO faz chamada ao Instagram, que e o recurso escasso.

Rodar:

    py testes\teste_as_telas_abrem.py
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

falhas = []

# As quatro telas, com o titulo que painel.py declara para cada uma. Ate
# 14/09/2026 existia uma quinta, "Validacao Regulatoria", fora de pages/ (por
# isso o teste 1 ainda confere so por conter, nao por listar o diretorio); ela
# saiu do menu e o arquivo foi apagado, com o essencial migrado para dentro do
# Monitoramento.
TELAS = (
    ("pages/1_Downloads_e_Organizacao.py", "Downloads"),
    ("pages/2_Monitoramento.py", "Monitoramento"),
    ("pages/3_Financeiro.py", "Financeiro"),
    ("pages/4_Cadastro_de_Influenciadores.py", "Cadastro"),
)


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    print("--- 1. o painel declara as cinco telas ---")
    with open(os.path.join(BASE, "painel.py"), encoding="utf-8") as f:
        painel = f.read()
    for caminho, rotulo in TELAS:
        conferir(caminho in painel.replace("\\", "/"),
                 f"painel.py declara {caminho}",
                 "tela fora do roteador so abre por caminho direto")
    conferir(painel.count("st.Page(") >= len(TELAS),
             f"sao {len(TELAS)} ou mais st.Page declaradas",
             str(painel.count("st.Page(")))

    print()
    print("--- 2. o atalho sobe o ROTEADOR, e nao uma tela sozinha ---")
    # O defeito de 07/09/2026: o .bat subia app_validacao_influenciadores.py.
    # Quem subia por ali via uma tela so, com a barra lateral automatica do
    # Streamlit mostrando nome de arquivo em vez de titulo.
    with open(os.path.join(BASE, "iniciar_validacao_influenciadores.bat"),
              encoding="utf-8", errors="replace") as f:
        bat = f.read()
    conferir("painel.py" in bat, "o atalho aponta para painel.py")
    conferir("run app_validacao_influenciadores.py" not in bat,
             "e nao sobe mais uma pagina isolada")

    print()
    print("--- 3. cada tela DESENHA sem estourar erro ---")
    import acesso
    # Configuracao real e suportada: maquina local, sem login. Ver INSTALAR.md
    # item 6.4. Nao e contorno de teste.
    acesso.login_configurado = lambda: False
    acesso.escuta_a_rede = lambda: False

    from streamlit.testing.v1 import AppTest
    for caminho, rotulo in TELAS:
        try:
            at = AppTest.from_file(caminho, default_timeout=300)
            at.run()
        except Exception as e:
            conferir(False, f"{rotulo} desenhou", f"{type(e).__name__}: {str(e)[:180]}")
            continue
        if at.exception:
            primeira = str(at.exception[0].value)[:200]
            conferir(False, f"{rotulo} desenhou sem excecao", primeira)
        else:
            desenhou = len(at.markdown) + len(at.caption) + len(at.title) \
                + len(at.subheader) + len(at.error) + len(at.warning) \
                + len(at.info) + len(at.success)
            conferir(desenhou > 0,
                     f"{rotulo} desenhou sem excecao ({desenhou} elementos)",
                     "rodou sem erro mas nao desenhou nada")

    print()
    print("--- 4. nenhuma tela usa API do Streamlit marcada para remocao ---")
    # use_container_width foi anunciado para remocao em 31/12/2025, data que JA
    # passou. Ainda funciona no streamlit 1.59.2 instalado, mas o proprio
    # Streamlit imprime o aviso a cada desenho, e uma atualizacao quebra a tela.
    # Este teste nao exige a correcao, ele CONTA, para a divida ficar visivel e
    # nao crescer sem ninguem ver.
    arquivos = [os.path.join(BASE, c) for c, _ in TELAS]
    arquivos += [os.path.join(BASE, x) for x in
                 ("acesso.py", "painel_trabalhador.py", "painel.py", "estilo.py")]
    total = 0
    for p in arquivos:
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            total += f.read().count("use_container_width")
    # O numero medido em 07/09/2026 e 28. O teste falha se CRESCER, e avisa para
    # baixar o teto quando alguem corrigir parte dele.
    TETO = 28
    conferir(total <= TETO,
             f"use_container_width nao aumentou (tem {total}, teto {TETO})",
             "codigo novo nao deve usar API marcada para remocao; "
             "troque por width='stretch' ou width='content'")
    if total < TETO:
        print(f"         [ nota ] caiu para {total}. Baixe o TETO neste arquivo.")

    print()
    print("--- 5. e nao voltou API que o Streamlit JA removeu ---")
    for p in arquivos:
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            texto = f.read()
        nome = os.path.basename(p)
        # st.cache puro foi removido; st.cache_data e st.cache_resource sao as
        # atuais. A busca precisa distinguir, senao acusa o uso correto.
        import re
        conferir(not re.search(r"st\.cache\s*\(", texto),
                 f"{nome} nao usa st.cache (removido)")
        conferir("use_column_width" not in texto,
                 f"{nome} nao usa use_column_width (removido)")


if __name__ == "__main__":
    print("=" * 74)
    print("  As quatro telas abrem sem estourar erro")
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
