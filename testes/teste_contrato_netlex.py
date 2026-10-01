# -*- coding: utf-8 -*-
"""
O número do contrato no Netlex, e o caso da RENOVAÇÃO.

POR QUE ESTE TESTE EXISTE

Pedido do auditor em 03/09/2026: "na parte de Cadastro também deve conter o
numero do contrato NETLEX (Caso ele tenha, se não tiver, fica em branco mesmo)".
E, na mesma conversa: "temos que pensar no caso de renovação de contrato".

As duas coisas se resolvem na mesma decisão, que é a CHAVE do registro. O
auditor já havia registrado em 31/08 que renovação não encerra o contrato
anterior. Se a chave fosse só o @, renovar sobrescreveria o número antigo e o
papel de trabalho perderia qual contrato valia quando a peça foi publicada.

Rodar:

    py testes\teste_contrato_netlex.py
"""
import os
import sys
import tempfile

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
    import contratos_netlex as cn

    print("--- 1. a chave não depende de como a pessoa digitou ---")
    conferir(cn.normalizar_handle(" @Fulano ") == "fulano",
             "arroba, espaço e maiúscula somem da chave",
             cn.normalizar_handle(" @Fulano "))
    conferir(cn.chave("@x", "03/10/2025", "03/01/2026")
             == cn.chave("X", "2025-10-03", "2026-01-03"),
             "a mesma janela escrita de duas formas dá a MESMA chave",
             "senão o mesmo contrato viraria dois registros")

    print()
    print("--- 2. o serial do Sheets é lido, e data ilegível não é chutada ---")
    # O serial aparece de verdade no dado do Marketing, e chutar data criaria
    # chave que não corresponde a contrato nenhum.
    conferir(cn.normalizar_data("45933") == "2025-10-03",
             "serial de 5 dígitos vira data", cn.normalizar_data("45933"))
    conferir(cn.normalizar_data("contrato antigo") == "",
             "texto que não é data vira janela vazia, e não uma data inventada")
    conferir(cn.normalizar_data("") == "" and cn.normalizar_data(None) == "",
             "vazio continua vazio")

    print()
    print("--- 3. em branco é resposta válida ---")
    # Pedido literal do auditor: "caso ele tenha, se não tiver, fica em branco
    # mesmo". Vazio NÃO pode virar alerta nem erro.
    with tempfile.TemporaryDirectory() as pasta:
        cn.ARQUIVO = os.path.join(pasta, "netlex_contratos.csv")
        conferir(cn.ler() == [],
                 "antes do primeiro uso o registro está vazio, sem estourar")
        conferir(cn.numero_de("@ninguem", "", "") == "",
                 "quem não tem número devolve vazio, e não erro")

        registro = cn.gravar("@fulano", "03/10/2025", "03/01/2026", "", "eu",
                             "contrato não localizado no Netlex")
        conferir(registro["numero_netlex"] == "",
                 "gravar em branco é permitido")
        conferir(len(cn.ler()) == 1,
                 "e fica registrado, com quem conferiu e quando",
                 "é diferente de ninguém ter olhado")
        conferir(bool(registro["quem"]) and bool(registro["quando"]),
                 "o registro guarda quem informou e quando")

        print()
        print("--- 4. RENOVAÇÃO: o número novo não apaga o antigo ---")
        # É o caso que o auditor levantou. O Marketing sobrescreve as datas na
        # linha do influenciador quando renova, então a janela antiga desaparece
        # da planilha DELES. Aqui ela não desaparece.
        cn.gravar("@fulano", "03/10/2025", "03/01/2026", "CT-1000", "eu")
        cn.gravar("@fulano", "04/01/2026", "04/07/2026", "CT-2000", "eu")
        conferir(cn.numero_de("@fulano", "03/10/2025", "03/01/2026") == "CT-1000",
                 "a janela antiga continua com o número dela",
                 cn.numero_de("@fulano", "03/10/2025", "03/01/2026"))
        conferir(cn.numero_de("@fulano", "04/01/2026", "04/07/2026") == "CT-2000",
                 "e a janela nova tem o seu",
                 cn.numero_de("@fulano", "04/01/2026", "04/07/2026"))
        historico = cn.historico_de("@fulano")
        conferir(len({(h["inicio"], h["fim"]) for h in historico}) == 2,
                 "o histórico mostra as DUAS janelas do mesmo influenciador",
                 str([(h["inicio"], h["fim"]) for h in historico]))
        conferir(historico[0]["inicio"] == "2026-01-04",
                 "com a mais recente na frente", historico[0]["inicio"])

        print()
        print("--- 5. corrigir número digitado errado é gravar de novo ---")
        cn.gravar("@fulano", "04/01/2026", "04/07/2026", "CT-2001", "eu",
                  "corrigindo digitação")
        conferir(cn.numero_de("@fulano", "04/01/2026", "04/07/2026") == "CT-2001",
                 "o último gravado vence na leitura")
        conferir(sum(1 for r in cn.ler()
                     if r["numero_netlex"] in ("CT-2000", "CT-2001")) == 2,
                 "e as duas versões continuam no arquivo, como trilha",
                 "gravação é acréscimo; o histórico não se apaga")

        print()
        print("--- 6. um influenciador não herda o número do outro ---")
        cn.gravar("@outro", "03/10/2025", "03/01/2026", "CT-9999", "eu")
        conferir(cn.numero_de("@fulano", "03/10/2025", "03/01/2026") == "CT-1000",
                 "mesma janela, @ diferente, número diferente")
        conferir(cn.numero_de("@terceiro", "03/10/2025", "03/01/2026") == "",
                 "e quem nunca foi registrado continua em branco")

        print()
        print("--- 7. sem @ não há o que registrar ---")
        try:
            cn.gravar("  ", "", "", "CT-1", "eu")
            conferir(False, "gravar sem @ falha em vez de criar registro órfão")
        except ValueError:
            conferir(True, "gravar sem @ falha em vez de criar registro órfão")

        print()
        print("--- 7b. o número do papel de trabalho não tem janela ---")
        # A planilha final da auditoria guarda data de PAGAMENTO, não a vigência
        # do contrato, então o número importado entra sem janela e vale para o
        # influenciador. A tela cai nele quando a janela da linha do Marketing
        # não casa com registro nenhum.
        cn.gravar("@importado", "", "", "1690", "importação",
                  origem=cn.ORIGEM_PAPEL_DE_TRABALHO)
        conferir(cn.numeros_do_influenciador("@importado") == ["1690"],
                 "o número é achado pelo @, sem depender de janela",
                 str(cn.numeros_do_influenciador("@importado")))
        conferir(cn.numero_de("@importado", "01/01/2026", "01/07/2026") == "",
                 "e ele NÃO se apresenta como sendo daquela janela",
                 "seria afirmar vigência que a fonte não tem")
        registros = cn.ler()
        conferir(any(r["origem"] == cn.ORIGEM_PAPEL_DE_TRABALHO
                     for r in registros),
                 "a origem fica gravada, para não confundir importado com digitado")

        print()
        print("--- 7c. MAIS DE UM CONTRATO devolve os dois, sem escolher ---")
        # Medido em 03/09/2026 no papel de trabalho: três influenciadores têm
        # dois números (@clararodriiguess 1137 e 2163, @ruivinhademarte 1029 e
        # 2074, @nathanqueiroz 1290 e 12902). Escolher um seria o programa
        # decidindo qual contrato vale.
        cn.gravar("@dois", "", "", "1137", "importação",
                  origem=cn.ORIGEM_PAPEL_DE_TRABALHO)
        cn.gravar("@dois", "", "", "2163", "importação",
                  origem=cn.ORIGEM_PAPEL_DE_TRABALHO)
        conferir(cn.numeros_do_influenciador("@dois") == ["1137", "2163"],
                 "os dois números voltam, em ordem",
                 str(cn.numeros_do_influenciador("@dois")))
        conferir(cn.numeros_do_influenciador("@ninguem") == [],
                 "e quem não tem nenhum devolve lista vazia, não erro")

    print()
    print("--- 7d. a coluna nova não desalinha o registro antigo ---")
    with tempfile.TemporaryDirectory() as pasta:
        import csv as _csv
        cn.ARQUIVO = os.path.join(pasta, "netlex_contratos.csv")
        antigos = ("handle", "inicio", "fim", "numero_netlex", "observacao",
                   "quem", "quando")
        with open(cn.ARQUIVO, "w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=antigos)
            w.writeheader()
            w.writerow({"handle": "antigo", "inicio": "", "fim": "",
                        "numero_netlex": "999", "observacao": "",
                        "quem": "alguem", "quando": "2026-09-03 10:00:00"})
        cn.gravar("@novo", "", "", "1000", "eu")
        with open(cn.ARQUIVO, encoding="utf-8", newline="") as f:
            depois = list(_csv.DictReader(f))
        conferir(tuple(depois[0].keys()) == cn.CAMPOS,
                 "o arquivo é reescrito com os títulos novos",
                 str(tuple(depois[0].keys())))
        conferir(cn.numeros_do_influenciador("antigo") == ["999"],
                 "sem perder o que já estava gravado")
        conferir(depois[0]["origem"] == "",
                 "e a coluna nova fica vazia no registro antigo, não chutada")

    print()
    print("--- 8. o número NÃO vai para a planilha do Marketing ---")
    # A regra do projeto, e ela vale também para este campo novo: a
    # Monitoramento real nunca recebe escrita.
    with open(os.path.join(BASE, "contratos_netlex.py"), encoding="utf-8") as f:
        fonte_modulo = f.read()
    for termo in ("sheets_client", "spreadsheets", "batchUpdate",
                  "values().append", "values().update"):
        conferir(termo not in fonte_modulo,
                 f"o módulo não usa {termo}",
                 "o número é registro NOSSO; a planilha deles é só leitura")
    conferir("renova" in fonte_modulo.lower(),
             "e o porquê da janela na chave está escrito no próprio arquivo",
             "sem isso, alguém simplifica a chave para só o @ depois")


if __name__ == "__main__":
    print("=" * 74)
    print("  Número do contrato no Netlex, por janela de contrato")
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
