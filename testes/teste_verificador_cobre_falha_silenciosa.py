# -*- coding: utf-8 -*-
"""
O verificador de ambiente cobre as faltas que NAO dao erro.

POR QUE ESTE ARQUIVO EXISTE (07/09/2026)

O manual de instalacao prometia, no passo da conferencia, que o comando "diz o
que falta". Auditado contra o codigo, ele nao dizia. Faltavam seis itens, e o
que os seis tem em comum e o motivo deste teste: TODOS FALHAM EM SILENCIO.

  falta                              o que acontece            aparecia?
  copia da Monitoramento em Excel    todo video vira            nao
                                     "Ciclo A CONFIRMAR"
  uma das 5 chaves do login          o programa abre SEM        nao
                                     pedir login
  fechamentos_planilha_id.txt        a conclusao fica so        nao
                                     nesta maquina
  netlex_contratos.csv               o Cadastro abre sem        nao
                                     o numero do contrato
  cache de perfis vazio              gasta a chamada mais       nao
                                     limitada do Instagram
  biblioteca de download velha       o download quebra          nao
                                     quando o Instagram mudar

NENHUM DELES DA ERRO NA TELA. Erro que aparece se resolve; falta silenciosa
atravessa a instalacao inteira e cobra depois, no meio de um lote. Enquanto isso
nao era conferido, o manual tinha de pedir que a pessoa olhasse arquivo por
arquivo, e um manual que pede isso e um manual que sera seguido pela metade.

O CASO MAIS PERIGOSO E O DO LOGIN, porque a falha e ao CONTRARIO do esperado:
faltando uma chave, `login_configurado()` devolve falso e o programa abre sem
pedir entrada. Quem montou o arquivo acha que ligou o login. Por isso a lista
das cinco chaves virou constante em acesso.py: duas listas iguais escritas em
dois arquivos divergem na primeira mudanca, e divergindo, o verificador diria
que esta tudo certo.

Rodar:

    py testes\teste_verificador_cobre_falha_silenciosa.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    with open(os.path.join(BASE, "verificar_ambiente.py"),
              encoding="utf-8") as f:
        v = f.read()

    print("--- 1. as cinco chaves do login sao UMA constante ---")
    # Se cada arquivo tiver a sua lista, elas divergem e o verificador passa a
    # aprovar um login que nao vai funcionar.
    import acesso
    conferir(hasattr(acesso, "CHAVES_DO_LOGIN"),
             "acesso.CHAVES_DO_LOGIN existe")
    conferir(len(getattr(acesso, "CHAVES_DO_LOGIN", ())) == 5,
             "e sao cinco chaves",
             str(getattr(acesso, "CHAVES_DO_LOGIN", ())))
    for chave in ("client_id", "client_secret", "server_metadata_url",
                  "redirect_uri", "cookie_secret"):
        conferir(chave in getattr(acesso, "CHAVES_DO_LOGIN", ()),
                 f"{chave} esta na constante")
    conferir("acesso.CHAVES_DO_LOGIN" in v,
             "e o verificador usa a constante, nao uma lista propria",
             "lista repetida divergiria na primeira mudanca")
    # A lista nao pode ter voltado a ser escrita a mao dentro do login.
    with open(os.path.join(BASE, "acesso.py"), encoding="utf-8") as f:
        a = f.read()
    conferir(a.count('"cookie_secret"') == 1,
             "a chave aparece UMA vez em acesso.py, so na constante",
             f"apareceu {a.count(chr(34) + 'cookie_secret' + chr(34))} vezes")

    print()
    print("--- 2. o verificador NAO imprime valor de segredo ---")
    # A saida deste comando existe para ser colada num chat. Imprimir o valor de
    # uma chave de login ali seria vazar credencial pelo caminho de diagnostico.
    bloco = v.split("def conferir_login(")[1].split("\ndef ")[0]
    conferir("auth.get(c)" in bloco and "not auth.get(c)" in bloco,
             "ele testa a chave pela presenca, sem guardar o valor")
    conferir("', '.join(faltando)" in bloco,
             "e imprime apenas o NOME das chaves que faltam")
    for proibido in ("auth[", "print(auth", "str(auth)", "repr(auth)"):
        conferir(proibido not in bloco,
                 f"nao ha {proibido!r} no bloco do login")

    print()
    print("--- 3. os seis itens silenciosos entraram na conferencia ---")
    for rotulo, marca in (
        ("copia da Monitoramento em Excel", "_achar_monitoramento()"),
        ("identificador dos fechamentos", "NOME_DO_ARQUIVO_ID"),
        ("registro de contratos do Netlex", "contratos_netlex.ARQUIVO"),
        ("cache de perfis do Instagram", "ARQUIVO_USERIDS"),
        ("chaves do login", "CHAVES_DO_LOGIN"),
        ("bibliotecas de download", "baixadores.estado()"),
    ):
        conferir(marca in v, f"{rotulo} e conferido ({marca})")

    print()
    print("--- 4. a gravidade de cada um esta certa ---")
    # Nao e detalhe: FALTA para o programa e AVISO para o que so custa dinheiro
    # ou tempo. Marcar tudo como FALTA faria a pessoa parar por causa de cache.
    mon = v.split("cópia da Monitoramento em Excel")[2]
    conferir("FALTA" in mon.split("anotar(")[0] or 'anotar(FALTA' in v.split(
        "não achei; sem ela todo vídeo")[0][-260:],
        "Monitoramento faltando e FALTA, porque estraga o dado do ciclo")
    cache = v.split("cache de perfis do Instagram")[1][:400]
    conferir("FALTA" not in cache,
             "cache vazio NAO e falta: o programa funciona sem ele",
             "numa maquina nova o normal e 0 perfis")
    login = v.split("def conferir_login(")[1].split("\ndef ")[0]
    conferir("anotar(FALTA" not in login,
             "login sem configuracao e AVISO, nao FALTA",
             "desligar o login e uma opcao legitima em maquina local")

    print()
    print("--- 5. o modulo declara as cinco camadas que ele confere ---")
    conferir("conferir_manutencao()" in v.split('if __name__')[1],
             "a camada de manutencao e chamada de verdade",
             "definir a funcao e nao chamar deixaria o teste passar sozinho")
    for nome in ("conferir_pacotes", "conferir_programas", "conferir_servicos",
                 "conferir_configuracao", "conferir_manutencao"):
        conferir(f"{nome}()" in v.split('if __name__')[1],
                 f"{nome} roda")

    print()
    print("--- 6. o verificador continua sem ALTERAR nada ---")
    # E a promessa do proprio docstring dele. Um verificador que escreve deixa
    # de poder ser rodado por qualquer pessoa a qualquer momento.
    for escrita in ('open(caminho, "w"', "os.makedirs", "shutil.copy",
                    ".write("):
        conferir(escrita not in v, f"nao ha {escrita!r} no verificador")
    conferir("Não altera nada" in v, "e o docstring continua declarando isso")

    print()
    print("--- 7. ele roda de verdade e devolve codigo de saida ---")
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(BASE, "verificar_ambiente.py")],
                       capture_output=True, text=True, timeout=300,
                       encoding="utf-8", errors="replace")
    saida = (r.stdout or "") + (r.returncode and (r.stderr or "") or "")
    conferir(r.returncode in (0, 1),
             f"devolve 0 ou 1, para poder virar script (veio {r.returncode})")
    for esperado in ("--- pacotes Python ---", "--- programas externos ---",
                     "--- servi", "--- configura", "--- manuten"):
        conferir(esperado in saida, f"a saida tem o bloco {esperado!r}")
    # Se a maquina tem o secrets.toml completo, a linha tem de dizer isso, e
    # sem revelar chave nenhuma.
    if os.path.exists(os.path.join(BASE, ".streamlit", "secrets.toml")):
        conferir("login do programa" in saida,
                 "e a linha do login aparece")
        conferir("client_secret=" not in saida and "cookie_secret=" not in saida,
                 "sem nenhum valor de segredo na saida")

    print()
    print("--- 8. a copia da Monitoramento e conferida por IDADE, nao so por "
          "presenca ---")
    # POR QUE (07/09/2026). Existir e estar velha sao coisas diferentes, e a
    # velha erra de um jeito pior. Sem a copia, todo video cai em "Ciclo A
    # CONFIRMAR", que e visivel. Com a copia velha, video de data posterior ao
    # ultimo ciclo conhecido recebe o rotulo do CICLO ANTIGO, em silencio, e vai
    # assim para a coluna CICLO da planilha (ver fluxo_downloads.inferir_ciclo).
    conferir("DIAS_ATE_A_COPIA_ENVELHECER" in v,
             "existe um limite de idade declarado como constante")
    import verificar_ambiente
    conferir(isinstance(getattr(verificar_ambiente,
                                "DIAS_ATE_A_COPIA_ENVELHECER", None), int),
             "e ele e um numero")
    conferir("def conferir_idade_da_monitoramento(" in v,
             "existe a funcao que confere a idade")
    # O mesmo cuidado da secao 5: definir e nao chamar deixaria o teste passar
    # sozinho e a conferencia nunca rodaria. Tira o corpo da propria funcao
    # antes de procurar a chamada, para o teste nao depender de ela estar num
    # lugar especifico do arquivo.
    antes, resto = v.split("def conferir_idade_da_monitoramento(", 1)
    fora_da_funcao = antes + resto.split("\ndef ", 1)[-1]
    conferir("conferir_idade_da_monitoramento(" in fora_da_funcao,
             "e ela e CHAMADA de algum lugar",
             "definir sem chamar nao confere nada")
    conferir("idade da cópia da Monitoramento" in saida,
             "a linha da idade aparece na saida de verdade")

    print()
    print("--- 9. os dois pacotes do OpenCV sao travados na MESMA versao ---")
    # OS DOIS SAO OBRIGATORIOS e nao ha como ser diferente: rapidocr-onnxruntime
    # depende de opencv-python e easyocr depende de opencv-python-headless. Os
    # dois gravam na MESMA pasta cv2, entao quem instala por ultimo sobrescreve
    # o outro. Com a mesma versao isso e inofensivo. Com versoes diferentes fica
    # um cv2 montado com metade de cada, e o sintoma e erro ao carregar a
    # biblioteca, sem nada dizendo que a causa e a mistura.
    #
    # Este teste existe para impedir que alguem atualize UM dos dois.
    import re as _re
    with open(os.path.join(BASE, "requirements.txt"), encoding="utf-8") as f:
        req = f.read()
    fixadas = dict(_re.findall(r"^(opencv-python(?:-headless)?)==(\S+)",
                               req, _re.MULTILINE))
    conferir(len(fixadas) == 2,
             "os DOIS estao no requirements.txt",
             f"achei {sorted(fixadas)}")
    if len(fixadas) == 2:
        conferir(len(set(fixadas.values())) == 1,
                 "e travados na mesma versao",
                 f"divergiram: {fixadas}")
    # E a conferencia do ambiente tem de reclamar de DIVERGENCIA, nao de
    # presenca: avisar sempre que os dois aparecem seria aviso permanente, e
    # aviso permanente ninguem le.
    conferir("def conferir_opencv(" in v, "existe a funcao que confere o opencv")
    bloco_cv = v.split("def conferir_opencv(")[1].split("\ndef ")[0]
    conferir("completo == headless" in bloco_cv,
             "ela compara as duas versoes")
    conferir("causa conhecida de conflito" not in v,
             "e o aviso antigo, que disparava so pela presenca, saiu")


if __name__ == "__main__":
    print("=" * 74)
    print("  O verificador cobre as faltas que nao dao erro")
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
