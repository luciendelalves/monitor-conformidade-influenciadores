# -*- coding: utf-8 -*-
"""
Prova que o rótulo curto da coluna VALIDACAO diz o que a analista precisa saber.

POR QUE ESTA COLUNA É A MAIS IMPORTANTE DAS TRÊS

O auditor descreveu o fluxo real em 02/09/2026, e ele decide o desenho:

  - o registro fica na Monitoramento, que é onde está o link
  - CONFORME: a analista não precisa consultar nada
  - NÃO CONFORME: ela vê o motivo e sinaliza a coordenação ou o gestor da área
  - REQUER ANÁLISE: aí sim ela vai verificar o motivo

Ou seja, a coluna VALIDACAO é a PRIMEIRA e às vezes a ÚNICA coisa que a pessoa
lê. Um rótulo que não diz o que fazer custa o trabalho de abrir o programa, ou
pior, custa a decisão errada.

O DEFEITO QUE ISTO CORRIGE, e ele enganou o próprio auditor

O rótulo era "REQUER ANÁLISE HUMANA (aviso pequeno/baixo contraste)", escolhido
por procurar as palavras "texto pequeno" dentro do motivo. Ele leu isso no caso
do @andersonneiff e concluiu "achei bem ok". Na verdade o publi não estava na
peça, o rodapé estava perfeitamente legível, e o OCR tinha lido cinco itens
naquele clipe. O rótulo afirmava uma causa que o programa não conhecia.

E DEPOIS QUASE PIOROU: ao tirar "texto pequeno" do motivo, mais cedo no mesmo
dia, aquele ramo deixou de casar e o rótulo caiu no genérico "REQUER ANÁLISE
HUMANA", perdendo até a pouca informação que tinha. Regressão introduzida pela
própria correção, e é por isso que este teste existe.

Agora o rótulo nomeia O ITEM a conferir, que é o que a régua do auditor pede:
está na tela?

    py testes\teste_rotulo_da_coluna_validacao.py
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


# MOTIVOS REAIS, copiados do que o motor produz hoje. Não são inventados: o
# primeiro é o texto que o @andersonneiff gerou depois da correção de 02/09.
MOTIVO_AMBIGUO = (
    "Clipe '@andersonneiff Tela 1.mp4' mostra conteúdo de aposta: CONFERIR NA "
    "PEÇA: identificação de publicidade (#publi) está na tela? Nenhum motor de "
    "OCR confirmou, e a IA de visão sugere que está presente, o que não confirma "
    "nem crava ausência. A régua é presença: se estiver na tela, ainda que "
    "pequeno, o item é conforme; se não estiver, é achado"
)
MOTIVO_BANNER = (
    "Clipe '29-08 - @bahiadohype - tela 1.mp4' mostra conteúdo de aposta: "
    "outra(s) linha(s) do mesmo aviso (18, portaria) já foram confirmadas por "
    "OCR neste clipe, mas menção à portaria não foi lido — o texto costuma ser "
    "pequeno/fino e falhar no OCR mesmo quando presente, então é mais provável "
    "falha de leitura do que ausência real — requer conferência manual"
)


def rodar():
    import pipeline_influenciadores as pipeline

    print("--- 1. o rótulo NOMEIA o item a conferir ---")
    rotulo = pipeline.formatar_para_planilha(
        {"classificacao": "Requer Verificação", "motivo": MOTIVO_AMBIGUO})
    print(f"       {rotulo}")
    conferir(rotulo.startswith("REQUER ANÁLISE HUMANA"),
             "continua sendo REQUER ANÁLISE HUMANA", rotulo)
    conferir("conferir na tela" in rotulo,
             "e diz o que fazer: conferir na tela", rotulo)
    conferir("publi" in rotulo,
             "nomeando o item, que é o que a pessoa precisa saber", rotulo)

    print()
    print("--- 2. o rótulo NÃO afirma a causa ---")
    # Era isso que enganava: "aviso pequeno/baixo contraste" como se o programa
    # soubesse por que não leu.
    conferir("pequeno" not in rotulo and "contraste" not in rotulo,
             "não diz \"pequeno\" nem \"contraste\"", rotulo)

    print()
    print("--- 3. o caso do banner do rodapé também nomeia o item ---")
    rotulo_banner = pipeline.formatar_para_planilha(
        {"classificacao": "Requer Verificação", "motivo": MOTIVO_BANNER})
    print(f"       {rotulo_banner}")
    conferir("conferir na tela" in rotulo_banner,
             "diz o que fazer", rotulo_banner)
    conferir("portaria" in rotulo_banner,
             "e nomeia o item não lido", rotulo_banner)

    print()
    print("--- 4. os outros rótulos de Requer Verificação continuam iguais ---")
    # Estes não são dúvida sobre item do aviso, são problema de acesso ou de
    # escopo, e cada um leva a uma ação diferente da analista.
    casos = [
        ("Pasta sem arquivo de mídia (vazia ou inacessível)", "PASTA VAZIA"),
        ("Falha ao acessar material: 404", "SEM ACESSO À PASTA"),
        ("Link de rede social ao vivo — fora do escopo automático (Instagram)",
         "NÃO FOI POSSÍVEL ANALISAR (LINK DE REDE SOCIAL)"),
        ("exige análise manual — encontrado fragmento do aviso",
         "REQUER ANÁLISE HUMANA"),
        ("Nenhum arquivo do post parece conter conteúdo de aposta",
         "REQUER ANÁLISE HUMANA"),
    ]
    for motivo, esperado in casos:
        veio = pipeline.formatar_para_planilha(
            {"classificacao": "Requer Verificação", "motivo": motivo})
        conferir(veio == esperado, f"{esperado}", f"veio {veio!r}")

    print()
    print("--- 5. CONFORME e NÃO CONFORME não mudaram ---")
    # O Não Conforme já nomeava o que falta, e é o que sustenta a sinalização
    # para a coordenação no fluxo que o auditor descreveu.
    conferir(pipeline.formatar_para_planilha({"classificacao": "Conforme"})
             == "CONFORME", "CONFORME segue curto e sem observação")
    nc = pipeline.formatar_para_planilha(
        {"classificacao": "Não Conforme", "faltando": ["18", "publi"]})
    print(f"       {nc}")
    # O QUE ESTA CONFERÊNCIA GUARDA é que o rótulo NOMEIA o item, e que o
    # prefixo continua "NÃO CONFORME (" (é o prefixo que o motor de escopo e a
    # tela de Monitoramento leem, ambos por startswith/substring).
    #
    # NÃO guarda mais a palavra "Falta", que saiu em 09/09/2026: o aviso pode
    # estar na peça e não ter sido lido (caso real: escrito na vertical, que
    # nenhum OCR lê), e aí "falta" afirma uma ausência que o programa não
    # verificou. Ver o comentário em pipeline._rotulo_base.
    conferir(nc.startswith("NÃO CONFORME ("),
             "NÃO CONFORME mantém o prefixo que os outros módulos leem", nc)
    conferir("18+" in nc and "publi" in nc.lower(),
             "e nomeia os itens que não foram encontrados", nc)
    conferir("falta" not in nc.lower(),
             "sem afirmar ausência do que só não foi lido", nc)
    sem_lista = pipeline.formatar_para_planilha(
        {"classificacao": "Não Conforme", "faltando": []})
    conferir(sem_lista == "NÃO CONFORME",
             "e sem lista, não inventa observação", sem_lista)


if __name__ == "__main__":
    print("=" * 74)
    print("  Rótulo da coluna VALIDACAO: diz o que a analista precisa fazer")
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
