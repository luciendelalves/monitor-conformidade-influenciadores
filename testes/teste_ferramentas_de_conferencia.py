# -*- coding: utf-8 -*-
r"""
Prova as regras da pasta de ferramentas de conferência.

POR QUE ESTE TESTE EXISTE (02/09/2026)

As ferramentas nasceram para responder perguntas de conferência em segundos, e
elas têm duas propriedades que, se quebrarem, transformam a ferramenta em
armadilha. Nenhuma das duas quebra com erro na tela.

1. SÓ UMA DELAS PODE ESCREVER. Ferramenta de conferência que escreve por
   acidente é pior que ferramenta nenhuma: quem roda espera olhar, não alterar.

2. O CABEÇALHO PRECISA SER TEXTO LITERAL. Os textos de ajuda têm caminho do
   Windows dentro, como `ferramentas\ver_drive.py`. Em texto normal do Python o
   `\v` é TABULAÇÃO VERTICAL e o `\l` é escape inválido. A primeira versão destes
   arquivos teve o texto corrompido em silêncio: o `\v` comeu a letra e o uso
   virou `ferramentas\x0ber_drive.py`. Nenhum erro, nenhum aviso para o `\v`.

E uma terceira, que vale para todas: NENHUMA fala com o Instagram. A chamada ao
Instagram é o recurso escasso do programa, e conferência não pode gastá-lo.

    py testes\teste_ferramentas_de_conferencia.py
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(BASE, "ferramentas")
sys.path.insert(0, BASE)

falhas = []

# A única que pode escrever, e o nome dela diz isso.
QUE_ESCREVE = "limpar_teste.py"

# Nomes de função que ESCREVEM em algum lugar. Se aparecerem numa ferramenta de
# leitura, ela deixou de ser de leitura.
ESCREVEM = (
    "mandar_para_lixeira", "apagar_linhas", "escrever_lote", "adicionar_linhas",
    "limpar_fila", "enviar_arquivo", "obter_ou_criar_pasta",
    "remover_material_de_teste", "gravar_veredito", "marcar_fora_da_analise",
    "registrar_na_monitoramento", "guardar_userid", "gravar_log",
)

# Nomes que gastam chamada ao Instagram.
FALAM_COM_INSTAGRAM = (
    "baixar_video", "baixar_story", "userid_por_link_de_post",
    "instaloader", "yt_dlp", "processar_fila",
)


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def arquivos_de_ferramenta():
    return sorted(f for f in os.listdir(PASTA)
                  if f.endswith(".py") and not f.startswith("__"))


def corpo_sem_texto(fonte):
    """Tira o cabeçalho entre três aspas, para sobrar só o que executa."""
    partes = re.split(r'r?"""', fonte)
    if len(partes) >= 3:
        return partes[0] + "".join(partes[2:])
    return fonte


def rodar():
    print("--- 1. a pasta existe e tem as ferramentas esperadas ---")
    conferir(os.path.isdir(PASTA), "a pasta ferramentas existe", PASTA)
    arquivos = arquivos_de_ferramenta()
    print(f"       {arquivos}")
    esperadas = ["_base.py", "ler_com_ocr.py", "levantar_termos.py",
                 "limpar_teste.py", "ver_analise.py", "ver_drive.py",
                 "ver_registros.py"]
    for nome in esperadas:
        conferir(nome in arquivos, f"existe {nome}")
    conferir(os.path.exists(os.path.join(PASTA, "README.md")),
             "existe o README que indexa as ferramentas")

    print()
    print("--- 2. o cabeçalho é TEXTO LITERAL em todas ---")
    # É a propriedade que corrompeu em silêncio na primeira versão.
    for nome in arquivos:
        with open(os.path.join(PASTA, nome), encoding="utf-8") as f:
            comeco = f.read(200)
        conferir('r"""' in comeco,
                 f"{nome}: abre o cabeçalho com r\"\"\"",
                 "sem o r, \\v vira tabulação vertical e come a letra seguinte")

    print()
    print("--- 3. e nenhum cabeçalho tem caractere de controle indevido ---")
    # A prova direta: se algum escape passou, ele aparece aqui.
    sys.path.insert(0, PASTA)
    for nome in arquivos:
        modulo = __import__(nome[:-3])
        texto = modulo.__doc__ or ""
        ruins = [c for c in texto if ord(c) < 32 and c not in "\n\t"]
        conferir(not ruins, f"{nome}: cabeçalho sem caractere de controle",
                 str([hex(ord(c)) for c in ruins]))

    print()
    print("--- 4. SÓ a de limpeza escreve ---")
    for nome in arquivos:
        if nome == QUE_ESCREVE:
            continue
        with open(os.path.join(PASTA, nome), encoding="utf-8") as f:
            corpo = corpo_sem_texto(f.read())
        usados = [p for p in ESCREVEM if p in corpo]
        conferir(not usados, f"{nome}: não chama nada que escreve", str(usados))

    print()
    print("--- 5. a de limpeza declara isso no nome e no cabeçalho ---")
    with open(os.path.join(PASTA, QUE_ESCREVE), encoding="utf-8") as f:
        fonte_limpeza = f.read()
    conferir("ESCREVE" in fonte_limpeza.upper()[:900],
             "o cabeçalho avisa que ela escreve")
    conferir("mandar_para_lixeira" in fonte_limpeza,
             "e ela usa a LIXEIRA do Drive")
    conferir("files().delete" not in fonte_limpeza and "delete(" not in fonte_limpeza,
             "e nunca apaga em definitivo",
             "regra do projeto: sempre a lixeira")
    conferir("situacao_da_conta" in fonte_limpeza,
             "ela mostra a contagem do Instagram que NÃO apaga")
    conferir("_ler_userids" in fonte_limpeza,
             "e o mapa de perfis que NÃO apaga")
    conferir("trabalhador_ativo" in fonte_limpeza,
             "e confere se o trabalhador está trabalhando antes de limpar",
             "com ele de pé, o próximo download sobe para dentro da lixeira")

    print()
    print("--- 6. NENHUMA fala com o Instagram ---")
    for nome in arquivos:
        with open(os.path.join(PASTA, nome), encoding="utf-8") as f:
            corpo = corpo_sem_texto(f.read())
        usados = [p for p in FALAM_COM_INSTAGRAM if p in corpo]
        conferir(not usados, f"{nome}: não gasta chamada ao Instagram", str(usados))

    print()
    print("--- 7. as que mexem no Drive de teste confirmam que é o de teste ---")
    # A confirmação olha layout, identificador E nome da raiz. Só o
    # identificador não basta: apontar o arquivo de configuração para outro
    # lugar é uma linha de texto.
    with open(os.path.join(PASTA, "_base.py"), encoding="utf-8") as f:
        base = f.read()
    conferir("def confirmar_drive_de_teste" in base,
             "existe a confirmação compartilhada")
    for exigido in ("LAYOUT_MARKETING", "RAIZ_MARKETING", '"TESTE" not in'):
        conferir(exigido in base, f"a confirmação checa {exigido}")
    conferir("confirmar_drive_de_teste" in fonte_limpeza,
             "a de limpeza usa a confirmação")

    print()
    print("--- 8. todas rodam sem argumento, sem estourar ---")
    # Não é teste de saída, é teste de que a ferramenta não quebra ao ser
    # chamada errado: ela tem que explicar o uso, não dar traceback.
    import subprocess

    def rodar_ferramenta(nome, *argumentos):
        # encoding e errors EXPLÍCITOS: sem eles o Python lê a saída na página de
        # código do Windows (cp1252) e estoura com UnicodeDecodeError no primeiro
        # acento. Aconteceu na primeira versão deste teste, e o erro vinha de uma
        # thread interna do subprocess, o que atrapalha mais do que ajuda.
        return subprocess.run(
            [sys.executable, os.path.join("ferramentas", nome), *argumentos],
            cwd=BASE, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=900)

    for nome in ("ver_registros.py", "ver_analise.py", "ver_drive.py"):
        r = rodar_ferramenta(nome)
        conferir("Traceback" not in (r.stderr or ""),
                 f"{nome}: roda sem traceback",
                 (r.stderr or "")[-160:])
    for nome in ("ler_com_ocr.py", "levantar_termos.py"):
        r = rodar_ferramenta(nome, "--")
        conferir("Traceback" not in (r.stderr or ""),
                 f"{nome}: argumento estranho não dá traceback",
                 (r.stderr or "")[-160:])
    # E a de limpeza no modo conferir, que é o unico dela que nao escreve.
    r = rodar_ferramenta("limpar_teste.py", "conferir")
    conferir("Traceback" not in (r.stderr or ""),
             "limpar_teste.py conferir: roda sem traceback",
             (r.stderr or "")[-160:])


if __name__ == "__main__":
    print("=" * 74)
    print("  Ferramentas de conferência: leitura, e uma só escreve")
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
