# -*- coding: utf-8 -*-
"""
Prova que a frase do veredito começa pelo que NÃO foi confirmado.

O CASO QUE ORIGINOU ISTO (02/09/2026)

O auditor olhou o resultado do `@andersonneiff Tela 1.mp4`, leu o motivo, e
concluiu "achei bem ok". Depois, olhando o próprio vídeo, percebeu por conta
própria: faltava o #publi. A frase que ele leu começava assim:

    "IA de visão local sugere presença de identificação de publicidade (#publi)
     (texto pequeno/baixo contraste), mas sem confirmação por OCR..."

Ou seja: a frase escondeu o achado de quem escreveu a ferramenta. Quem lê linha
de planilha lê o começo, e o começo dizia a parte tranquilizadora. A ressalva
vinha depois de uma vírgula, num texto longo, numa célula estreita.

Isso não é questão de estilo. Numa auditoria, a ordem das frases decide o que a
pessoa entende, e entender errado aqui significa deixar passar peça sem
identificação de publicidade.

O QUE **NÃO** MUDOU, E POR QUÊ

A CLASSIFICAÇÃO. Item que a IA de visão sugere não conta como ausência
confirmada, e o post vai para Requer Verificação em vez de Não Conforme. Isso
está certo e foi conferido no código antes de mexer:

  - a sugestão da visão NUNCA produz Conforme (ver a condição
    `if itens_ambiguos and not faltando_nao_ambiguo`, que devolve Requer
    Verificação)
  - um item confirmadamente ausente por OCR já produz Não Conforme, independente
    da ambiguidade dos outros

E há caso real nas duas direções, os dois registrados no código: a visão já
confirmou um "18+" numa imagem que era print de conversa (alucinação), e já
acertou selo "18+" e #publi de baixo contraste que o OCR não leu. Com casos nos
dois sentidos, cravar ausência seria a ferramenta afirmando mais do que sabe.

    py testes\teste_ordem_da_frase_do_veredito.py
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

ARQUIVO = os.path.join(BASE, "validar_avisos_portaria136.py")

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    with open(ARQUIVO, encoding="utf-8") as f:
        fonte = f.read()

    print("--- 1. a frase lidera pela NÃO confirmação ---")
    # As cinco frases (uma por item obrigatório) saem de uma função só,
    # _frase_ambigua, desde a segunda correção de 02/09/2026. A ordem é a
    # propriedade sob teste: "NÃO CONFIRMADO" tem que vir ANTES de "IA de visão".
    # Pega a função INTEIRA, incluindo a linha do return: a versão anterior
    # deste teste parava em "return frase" e por isso não via o fim da frase,
    # que é justamente onde está a pergunta que a régua pede.
    #
    # A ASSINATURA DEIXOU DE SER FIXA (08/09/2026). Este teste casava
    # `def _frase_ambigua(rotulo):` literalmente, e reprovou inteiro quando a
    # função ganhou um segundo parâmetro para saber QUAL dos dois casos de
    # dúvida escrever. Agora aceita qualquer assinatura: o que está sob teste é
    # a ordem e o conteúdo da frase, não a lista de parâmetros.
    modelo = re.search(
        r"def _frase_ambigua\([^)]*\):(.*?)\n\s*if achou_18_ambiguo_visao:",
        fonte, re.DOTALL)
    conferir(modelo is not None, "a função que monta a frase existe")
    texto = " ".join(re.findall(r'[f]?"([^"]*)"', modelo.group(1))) if modelo else ""
    pos_nao = texto.upper().find("NÃO CONFIRMADO")
    pos_visao = texto.find("IA de visão")
    conferir(pos_nao >= 0, "a frase diz que NÃO foi confirmado", texto[:70])
    conferir(pos_visao < 0 or pos_nao < pos_visao,
             "e diz isso ANTES de citar a sugestão da visão",
             f"nao={pos_nao} visao={pos_visao}")

    # E os cinco itens têm que usar a função, senão um deles fica com texto
    # próprio e sai do padrão sem ninguém notar.
    for item in ("18", "publi", "portaria", "extra", "mf"):
        usa = re.search(rf"if achou_{item}_ambiguo_visao:\s*\n\s*evidencia_partes"
                        rf"\.append\(\s*\n?\s*_frase_ambigua", fonte)
        conferir(usa is not None, f"{item} usa a mesma função")

    print()
    print("--- 2. a frase NÃO AFIRMA a causa de não ter lido ---")
    # SEGUNDA CORREÇÃO DO MESMO TRECHO NO MESMO DIA, e a primeira foi minha.
    # A versão da manhã dizia "(texto pequeno ou baixo contraste)" como
    # explicação. O auditor derrubou com o caso concreto: no @andersonneiff o
    # rodapé estava "consideravelmente legível" e o OCR leu CINCO itens naquele
    # clipe. O publi não foi lido porque não estava lá.
    #
    # Ou seja, a correção da manhã trocou uma frase que ESCONDIA o achado por
    # outra que AFIRMAVA causa desconhecida. Mesmo defeito de fundo.
    conferir("NÃO sabe a causa" in texto,
             "a frase diz que o programa não sabe a causa",
             "afirmar causa é dizer mais do que se sabe")
    conferir("texto pequeno" not in texto and "baixo contraste" not in texto,
             "e não oferece \"texto pequeno\" nem \"baixo contraste\" como causa",
             texto[:90])

    print()
    print("--- 3. a frase diz o que o OCR LEU no mesmo clipe ---")
    # É o que permite a quem confere julgar sozinho: se o OCR leu cinco itens
    # ali, "não deu para ler" perde força como explicação.
    conferir("lidos_no_clipe" in fonte,
             "o programa junta os itens que o OCR leu naquele clipe")
    conferir("Neste mesmo clipe o OCR leu" in texto,
             "e a frase informa isso a quem vai conferir")
    conferir("não leu nenhum outro item" in texto,
             "e diz também quando o OCR não leu nada, que é o caso oposto")

    print()
    print("--- 4. a frase termina com a pergunta que a régua pede ---")
    # A régua do auditor é presença: "se estiver na tela, ainda que pequeno, É
    # OK". Então a pergunta para o humano é uma só, e é essa.
    conferir("está na tela?" in texto,
             "a frase termina perguntando \"está na tela?\"")
    conferir("publi (identificação de publicidade)" in fonte,
             "e o publi é nomeado por extenso, não só pela abreviação",
             "\"publi\" sozinho não diz nada para quem não é da área")

    print()
    print("--- 5. o motivo do post começa pelo que precisa ser conferido ---")
    conferir("CONFERIR NA PEÇA:" in fonte,
             "o motivo começa com \"CONFERIR NA PEÇA\"",
             "antes começava com \"IA de visão local sugere presença de\"")
    antigo = "motivo_extra\": f\"IA de visão local sugere presença de"
    conferir(antigo not in fonte,
             "e não começa mais pela sugestão da visão")

    print()
    print("--- 6. A CLASSIFICAÇÃO NÃO MUDOU, e isto é o ponto ---")
    # Se algum dia alguém "endurecer" isto, vai ser aqui, e o teste tem que
    # falhar para a mudança ser deliberada e não acidental.
    trecho = re.search(
        r"if itens_ambiguos and not faltando_nao_ambiguo:(.*?)continue",
        fonte, re.DOTALL)
    conferir(trecho is not None, "o ramo de \"todos os faltantes são ambíguos\" existe")
    if trecho:
        corpo = trecho.group(1)
        conferir('"Requer Verificação"' in corpo,
                 "e ele continua devolvendo Requer Verificação")
        conferir('"Não Conforme"' not in corpo,
                 "não crava Não Conforme sobre ausência não confirmada",
                 "seria a ferramenta afirmando mais do que sabe")
        conferir('"Conforme"' not in corpo.replace('"Requer Verificação"', ""),
                 "e não crava Conforme por sugestão da visão")

    print()
    print("--- 7. o áudio continua fora dos itens do aviso ---")
    # Regra de ouro, conferida junto porque é da mesma família: o aviso 18+
    # precisa estar ESCRITO, e o falado é reforço facultativo.
    conferir("o áudio NUNCA alimenta achou_18" in fonte
             or "áudio NUNCA alimenta" in fonte,
             "o áudio nunca alimenta os itens do aviso")


if __name__ == "__main__":
    print("=" * 74)
    print("  A frase do veredito começa pelo que não foi confirmado")
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
