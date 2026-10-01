# -*- coding: utf-8 -*-
r"""
Prova que peça orgânica não passa pela régua regulatória, e que ela NÃO fecha
como NÃO CONFORME nem como REQUER ANÁLISE HUMANA.

A DECISÃO É DO AUDITOR, em 02 e 03/09/2026, e ele deu o motivo antes de pedir:

    "orgânico não é fazendo propaganda, logo, ele não precisa colocar os avisos
    regulatórios pq ele ta so mostrando o patrocinio"

    "organico realmente não precisa de análise regulatória"

    "se for organico, no monitoramento, pode constar como POST ORGÂNICO, NÃO
    VALIDADO ou algo nesse sentido, pra não fechar como NÃO CONFORME ou REQUER
    ANALISE HUMANA"

O QUE ISSO CONSERTA, e é achado falso e não teoria: a régua reprovava peça
orgânica POR CONSTRUÇÃO. O nome da marca entra em REGEX_CONTEUDO_APOSTA
("lottu", "esportes da sorte", "eds", "onabet"), então uma garrafa com a logo
legível é lida como conteúdo de aposta; os quatro avisos não estão numa peça que
não anuncia; e o veredito saía NÃO CONFORME. Numa planilha que outras áreas leem,
isso é acusação de descumprimento sem fato.

POR QUE UM RÓTULO PRÓPRIO, e não CONFORME: dizer CONFORME afirmaria que a peça
atende à régua, e ela nem foi medida por ela.

E POR QUE ELA NEM É ANALISADA: a análise leva perto de 110 segundos por vídeo
nesta máquina, e 81% disso é a IA de visão. Peça que não vai ser julgada pela
régua não precisa pagar esse tempo, e numa fila com material orgânico junto isso
libera a vez para o que precisa.

    py testes\teste_regua_do_organico.py
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
    import fluxo_downloads as fluxo
    import pipeline_influenciadores as pipeline

    print("--- 1. o que conta como linha orgânica ---")
    # Passa pela leitura da célula, e não por igualdade de texto: a coluna tem
    # "SIM" nas linhas gravadas até 02/09/2026 e "ORGANICO" nas novas.
    for valor in ("ORGANICO", "organico", "orgânico", "SIM", "sim"):
        conferir(pipeline.e_linha_organica({"marcacao": valor}),
                 f"{valor!r} é linha orgânica")
    for valor in ("LINK", "link", "", None, "qualquer coisa"):
        conferir(not pipeline.e_linha_organica({"marcacao": valor}),
                 f"{valor!r} NÃO é linha orgânica")
    conferir(not pipeline.e_linha_organica({}),
             "linha sem a coluna também não é",
             "vazio cai em link, que é a peça publicitária comum")

    print()
    print("--- 2. o veredito da peça orgânica ---")
    resultado = pipeline.processar_organico({"excel_row": 4, "link": "algum"})
    conferir(resultado["classificacao"] == pipeline.CLASSIFICACAO_ORGANICO,
             "a classificação é própria, e não uma das três da régua",
             str(resultado["classificacao"]))
    rotulo = pipeline.formatar_para_planilha(resultado)
    print(f"       rótulo na planilha: {rotulo!r}")
    conferir(rotulo == pipeline.ROTULO_ORGANICO,
             "o rótulo é o que o auditor pediu", str(rotulo))
    conferir("ORGÂNICO" in rotulo and "NÃO VALIDADO" in rotulo,
             "diz que é orgânico E que não foi validado")
    # As duas coisas que ele pediu para NÃO acontecer.
    conferir("NÃO CONFORME" not in rotulo and "NAO CONFORME" not in rotulo,
             "não fecha como NÃO CONFORME",
             "a régua nem foi aplicada, então não há o que reprovar")
    conferir("REQUER" not in rotulo,
             "e não fecha como REQUER ANÁLISE HUMANA",
             "pediria conferência de um item que não se aplica")
    conferir(resultado["motivo"],
             "e o motivo explica por que ela ficou fora da régua")
    conferir("orgânica" in resultado["motivo"],
             "citando a marcação, que é de onde a decisão vem")

    print()
    print("--- 3. a peça orgânica NÃO é analisada ---")
    # A prova é que a rota protegida devolve o resultado de orgânico sem chamar
    # processar_linha, que é quem baixa o arquivo e roda OCR, visão e áudio.
    guardado = pipeline.processar_linha
    chamou = []
    try:
        def _nao_deveria(linha):
            chamou.append(linha)
            raise AssertionError("analisou uma peça orgânica")
        pipeline.processar_linha = _nao_deveria
        r = pipeline.processar_linha_protegida({"marcacao": "ORGANICO",
                                                "excel_row": 4})
        conferir(not chamou, "processar_linha não é chamada", str(chamou))
        conferir(r["classificacao"] == pipeline.CLASSIFICACAO_ORGANICO,
                 "e o resultado é o de orgânico", str(r.get("classificacao")))
        # E o caminho normal continua passando pela análise.
        chamou.clear()
        pipeline.processar_linha = lambda linha: {**linha, "classificacao": "Conforme"}
        r = pipeline.processar_linha_protegida({"marcacao": "LINK", "excel_row": 5})
        conferir(r["classificacao"] == "Conforme",
                 "peça com link continua sendo analisada normalmente")
    finally:
        pipeline.processar_linha = guardado

    print()
    print("--- 4. o trabalhador resolve na entrega, sem acionar a equipe ---")
    import inspect
    fonte = inspect.getsource(
        __import__("trabalhador").entregar_analise)
    conferir("e_linha_organica" in fonte,
             "a entrega confere a marcação")
    conferir("processar_organico" in fonte,
             "e resolve na hora, com o resultado de orgânico")
    # A ordem importa: o cache vem antes, senão linha que já tem análise
    # guardada deixaria de aproveitar o que existe.
    posicao_cache = fonte.find("carregar_cache")
    posicao_organico = fonte.find("e_linha_organica")
    conferir(0 < posicao_cache < posicao_organico,
             "e o cache continua sendo consultado ANTES",
             "senão linha já analisada perderia o resultado guardado")
    conferir("equipe.submit" in fonte and fonte.find("equipe.submit") > posicao_organico,
             "a equipe de análise só é acionada depois das duas saídas")

    print()
    print("--- 5. a situação da linha não diz VALIDADO ---")
    # Escrever VALIDADO ao lado de um veredito que diz "NÃO VALIDADO" seria a
    # planilha se contradizendo em duas colunas vizinhas.
    conferir(pipeline.SITUACAO_ORGANICO != fluxo.VALIDADO,
             "a situação da peça orgânica é própria",
             pipeline.SITUACAO_ORGANICO)
    conferir("ORGÂNICO" in pipeline.SITUACAO_ORGANICO.upper(),
             "e diz que é por ser orgânica")
    fonte_escrita = inspect.getsource(pipeline.gravar_veredito)
    conferir("SITUACAO_ORGANICO if e_organico else fluxo.VALIDADO" in fonte_escrita,
             "a escrita escolhe entre as duas pela classificação",
             str([l for l in fonte_escrita.splitlines() if "situacao" in l]))

    print()
    print("--- 6. a tela de Monitoramento reconhece o veredito novo ---")
    with open(os.path.join(BASE, "pages", "2_Monitoramento.py"),
              encoding="utf-8-sig") as f:
        tela = f.read()
    conferir("Orgânico (fora da régua)" in tela,
             "existe categoria própria no filtro de validação",
             "sem ela o veredito cairia em \"Outro texto\", que é o que ninguém "
             "reconhece")
    # A ordem da comparação importa: o rótulo contém "NÃO".
    posicao_org = tela.find('if "ORGÂNICO" in t or "ORGANICO" in t')
    posicao_nao = tela.find('if "NÃO CONFORME" in t')
    conferir(0 < posicao_org < posicao_nao,
             "e ela é testada ANTES de NÃO CONFORME",
             "o rótulo tem \"NÃO\" dentro dele")


if __name__ == "__main__":
    print("=" * 74)
    print("  Peça orgânica fica fora da régua regulatória")
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
