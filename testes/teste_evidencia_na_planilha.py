# -*- coding: utf-8 -*-
"""
Prova que a coluna EVIDENCIA não vira #ERROR! na planilha.

O DEFEITO (achado pelo auditor em 02/09/2026)

Ele mandou print da Monitoramento com SEIS linhas seguidas mostrando `#ERROR!`
na coluna EVIDENCIA. Lendo a fórmula crua da planilha:

    =HYPERLINK("https://drive.google.com/...";"@cassinha.161 Tela 1.mp4") |
    [@cassinha.161 Tela 1.mp4] aviso incompleto mesmo após os motores...

Célula do Sheets é fórmula OU texto, nunca as duas. `=HYPERLINK(...) | resto`
não é fórmula válida, então a célula inteira vira #ERROR! e a evidência que
sustenta o veredito desaparece da vista de quem lê a planilha.

POR QUE SÓ APARECEU AGORA: `formatar_video_problema` só monta a fórmula quando o
arquivo TEM link. As linhas antigas escapavam por acidente, porque nelas o link
não existia e a função devolvia texto puro.

O QUE NÃO ERA O DEFEITO, e quase virou o "conserto": o ponto e vírgula. O
separador de argumentos de fórmula segue o IDIOMA DA PLANILHA, e as quatro
planilhas deste projeto são pt_BR, onde o separador é `;`. Medido em 02/09/2026
lendo `properties.locale` de cada uma, e a planilha da auditoria tem 171
fórmulas com `;` funcionando. Trocar por vírgula quebraria as 171.

    py testes\teste_evidencia_na_planilha.py
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


# O caso real da linha 43 da Monitoramento de teste.
RESULTADO = {
    "arquivo": "@cassinha.161 Tela 1.mp4",
    "link_video_problema": "https://drive.google.com/file/d/15pznZw8UNhBLFHa71tzpEdKevYj8Hit4/view",
    "evidencia": "[@cassinha.161 Tela 1.mp4] aviso incompleto mesmo após os motores "
                 "reforçados de OCR (RapidOCR e EasyOCR)",
    "alerta_audio": "",
}


def rodar():
    import pipeline_influenciadores as pipeline

    print("--- 1. a célula da EVIDENCIA não pode começar com = ---")
    # É a regra inteira, em uma linha: se começa com "=", o Sheets tenta
    # interpretar a célula como fórmula, e qualquer texto solto ali derruba tudo.
    celula = pipeline._evidencia_para_planilha(RESULTADO)
    print(f"       {celula[:120]}")
    conferir(not celula.startswith("="),
             "não começa com \"=\", então o Sheets trata como texto",
             celula[:80])
    conferir("#ERROR" not in celula, "e não carrega erro dentro")

    print()
    print("--- 2. mas o link continua ali, para quem for conferir ---")
    # A evidência existe para quem contesta o veredito ir olhar o arquivo. Sem o
    # endereço, ela deixa de servir para isso.
    conferir(RESULTADO["link_video_problema"] in celula,
             "o endereço do arquivo aparece na célula")
    conferir(RESULTADO["arquivo"] in celula, "e o nome do arquivo também")
    conferir("aviso incompleto" in celula, "e a evidência de texto também")

    print()
    print("--- 3. a fórmula continua existindo, para quem a usa SOZINHA ---")
    # A coluna da planilha da auditoria recebe só isto, então lá a fórmula é
    # válida e é o que deixa o link clicável. Tirar a fórmula do programa inteiro
    # quebraria aquela coluna.
    formula = pipeline.formatar_video_problema(RESULTADO)
    conferir(formula.startswith("=HYPERLINK("),
             "com como_formula (padrão), devolve a fórmula")
    conferir(formula.count("|") == 0,
             "e ela vem sozinha, sem texto colado",
             "fórmula com texto colado é exatamente o defeito")

    print()
    print("--- 4. o separador é ponto e vírgula, e isso está CERTO ---")
    # Está no teste para ninguém "consertar": as quatro planilhas são pt_BR.
    conferir('";"' in formula or ';"' in formula,
             "a fórmula usa \";\", que é o separador de planilha pt_BR",
             "trocar por vírgula quebraria as 171 fórmulas que funcionam hoje")

    print()
    print("--- 5. sem link, devolve texto nos dois modos ---")
    sem_link = dict(RESULTADO, link_video_problema="")
    for como_formula in (True, False):
        saida = pipeline.formatar_video_problema(sem_link, como_formula=como_formula)
        conferir(not saida.startswith("="),
                 f"como_formula={como_formula}: sem link não há fórmula", saida[:60])

    print()
    print("--- 6. sem arquivo nenhum, não inventa conteúdo ---")
    vazio = pipeline.formatar_video_problema({}, como_formula=False)
    conferir(vazio == "", "devolve vazio", repr(vazio))
    com_nota = pipeline.formatar_video_problema({}, nota_extra="link duplicado")
    conferir(com_nota == "(link duplicado)",
             "e com nota, devolve só a nota entre parênteses", repr(com_nota))

    print()
    print("--- 7. aspas no nome do arquivo não quebram a fórmula ---")
    # Nome de arquivo com aspas viria do nome do post, que é texto de terceiro.
    aspas = dict(RESULTADO, arquivo='ele disse "oi".mp4')
    formula_aspas = pipeline.formatar_video_problema(aspas)
    conferir('""oi""' in formula_aspas,
             "as aspas são dobradas, como o Sheets exige", formula_aspas[:110])


if __name__ == "__main__":
    print("=" * 74)
    print("  Coluna EVIDENCIA: texto, e nunca fórmula colada com texto")
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
