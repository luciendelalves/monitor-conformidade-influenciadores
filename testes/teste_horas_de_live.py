# -*- coding: utf-8 -*-
"""
Horas de live, no registro de link externo.

POR QUE ESTE ARQUIVO EXISTE (04/09/2026)

Pedido do auditor: "na opção onde tem baixar apenas o link da live, deve ter
uma opção onde a pessoa adiciona o campo de horas de live e preenche a coluna U
da planilha". No mesmo dia ele pediu o formato: "se tiver como colocar no
formato xx:xx:xx, fica melhor, que é exatamente como tá na planilha deles".

A coluna U (HORAS_LIVE) é do Marketing, e a regra geral do projeto é que a
automação só preenche o que ela tem de onde tirar (ver o comentário de
registrar_na_monitoramento: cronograma, pagamento e observação ficam vazios,
porque a automação não tem como deduzir nenhum dos três). Horas de live é a
única exceção, e só no registro de link externo: ali a pessoa já digita o tipo
à mão, e quando o tipo é LIVE ela sabe a duração porque assistiu ou foi
avisada. Sem o campo, essa informação existia só na cabeça de quem registrava.

Este teste não fala com o Google: registrar_na_monitoramento e
registrar_link_externo escrevem em planilha de verdade, então a conferência é
por leitura de código-fonte, do mesmo jeito que teste_hierarquia_das_pastas.py
já faz para a marcação.

Rodar:

    py testes\teste_horas_de_live.py
"""
import inspect
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
    import fluxo_downloads as fluxo

    print("--- 1. a coluna U tem chave própria em COL_MON ---")
    conferir(fluxo.COL_MON.get("horas_live") == 21,
             "horas_live aponta para a coluna 21",
             str(fluxo.COL_MON.get("horas_live")))
    conferir(fluxo.letra_da_coluna(fluxo.COL_MON["horas_live"]) == "U",
             "e a coluna 21 é mesmo a U",
             fluxo.letra_da_coluna(fluxo.COL_MON["horas_live"]))

    print()
    print("--- 2. registrar_na_monitoramento só escreve quando informado ---")
    fonte_registro = inspect.getsource(fluxo.registrar_na_monitoramento)
    conferir('COL_MON["horas_live"]' in fonte_registro,
             "a função conhece a coluna de horas de live")
    conferir("if horas_live:" in fonte_registro,
             "e só grava quando o valor foi passado",
             "sem a condição, um registro sem live escreveria vazio ou zero "
             "por cima de uma célula que deveria ficar em branco mesmo")
    conferir("horas_live=None" in inspect.signature(
             fluxo.registrar_na_monitoramento).__str__(),
             "o parâmetro é opcional, com padrão None",
             str(inspect.signature(fluxo.registrar_na_monitoramento)))

    print()
    print("--- 3. só é obrigatório quando o tipo é LIVE ---")
    fonte_link = inspect.getsource(fluxo.registrar_link_externo)
    conferir('== "LIVE"' in fonte_link and "horas de live" in fonte_link,
             "a exigência está condicionada ao tipo LIVE",
             "sem a condição, YOUTUBE, TIKTOK e X/TWITTER pediriam duração "
             "que não existe para eles")
    conferir("horas_live=horas_live" in fonte_link
             or "horas_live=(" in fonte_link
             or "horas_live=None" in fonte_link,
             "e o valor é repassado para registrar_na_monitoramento",
             "sem isso o campo apareceria na tela e morreria antes de chegar "
             "na planilha")

    print()
    print("--- 4. a tela tem o campo, e valida antes de mandar ---")
    # "LINK SÓ PARA REGISTRAR" SE MUDOU PARA A PÁGINA DE UPLOADS EM
    # 23/09/2026, e o campo de horas de live foi junto: ele é parte daquele
    # formulário.
    with open(os.path.join(BASE, "pages", "5_Uploads.py"),
              encoding="utf-8") as f:
        tela = f.read()
    conferir("horas_live_link" in tela,
             "existe a variável do campo na tela")
    conferir("text_input" in tela.split("horas_live_link")[1][:200]
             if "horas_live_link" in tela else False,
             "e ela pede o texto livre no formato HH:MM:SS",
             "número decimal (\"1.5\") não é o formato que a planilha do "
             "Marketing usa, e o pedido foi bater com o formato deles")
    conferir('tipo_link == "LIVE" and not horas_live_link' in tela,
             "a tela barra o envio sem nenhuma hora quando o tipo é LIVE",
             "confere duas vezes de propósito: a tela poupa uma rodada de "
             "erro, e fluxo_downloads.py é quem garante de verdade")
    conferir("fluxo.normalizar_horas_live(horas_live_link)" in tela,
             "e a tela confere o FORMATO antes de deixar enviar",
             "sem isso \"1h30\" ou \"90 minutos\" passariam para a planilha "
             "sem forma de comparar com o que já está lá")

    print()
    print("--- 5. o formato HH:MM:SS é validado, e nada é inventado ---")
    conferir(fluxo.normalizar_horas_live("1:30:00") == "01:30:00",
             "hora com um dígito ganha o zero à esquerda",
             fluxo.normalizar_horas_live("1:30:00"))
    conferir(fluxo.normalizar_horas_live("01:05:09") == "01:05:09",
             "já no formato certo, sai igual")
    conferir(fluxo.normalizar_horas_live("120:00:00") == "120:00:00",
             "hora de três dígitos é aceita, para live longa não estourar")
    conferir(fluxo.normalizar_horas_live("1:30") == "01:30:00",
             "sem segundo, mas COM os dois-pontos, completa com \":00\"",
             "16/09/2026: o dois-pontos já diz onde a hora termina e o "
             "minuto começa, então completar o segundo com zero não é "
             "chute, é a única leitura possível do que a pessoa escreveu")
    conferir(fluxo.normalizar_horas_live("01:00") == "01:00:00",
             "\"01:00\" é 1 HORA, não 1 minuto",
             "achado testando: antes disso virava \"00:01:00\" calado, "
             "porque só existia o atalho de só-dígitos, que lê os "
             "dois-pontos como se não estivessem lá e reagrupa \"0100\" "
             "como minuto:segundo, sobrando hora zero")
    conferir(fluxo.normalizar_horas_live("1h30") == "",
             "texto livre tipo \"1h30\" também devolve vazio")
    conferir(fluxo.normalizar_horas_live("1:60:00") == "",
             "minuto 60 não existe, e não é aceito",
             fluxo.normalizar_horas_live("1:60:00"))
    conferir(fluxo.normalizar_horas_live("") == "",
             "vazio continua vazio, sem estourar")

    print()
    print("--- 5b. só dígitos, com MENOS de 5, não é mais um chute (17/09/2026) ---")
    # Achado pelo auditor testando ao vivo: "0150" pensando em 1 hora e 50
    # minutos saía CALADO como "00:01:50" (1 minuto e 50), porque com menos
    # de 5 dígitos "os dois últimos pares são segundo e minuto" é uma leitura
    # tão válida quanto a que a pessoa tinha na cabeça. Mesmo defeito do
    # "01:00" virando "1 minuto" (16/09/2026), só que no atalho sem
    # dois-pontos, que não tinha sido corrigido junto.
    conferir(fluxo.normalizar_horas_live("0150") == "",
             "\"0150\" sozinho é ambíguo (1h50 ou 1min50?) e devolve vazio, "
             "em vez de adivinhar",
             fluxo.normalizar_horas_live("0150"))
    conferir(fluxo.normalizar_horas_live("150") == "",
             "\"150\" (3 dígitos) também é pouco para decidir sozinho",
             fluxo.normalizar_horas_live("150"))
    conferir(fluxo.normalizar_horas_live("50") == "",
             "\"50\" (2 dígitos) idem, mesmo sendo o mais curto que antes "
             "ainda colava (virava 50 segundos)",
             fluxo.normalizar_horas_live("50"))
    conferir(fluxo.normalizar_horas_live("13000") == "01:30:00",
             "com 5 dígitos continua funcionando, exemplo do próprio auditor",
             fluxo.normalizar_horas_live("13000"))
    conferir(fluxo.normalizar_horas_live("015000") == "01:50:00",
             "e com os 6 dígitos, \"1 hora e 50\" sai certo",
             fluxo.normalizar_horas_live("015000"))
    conferir(fluxo.normalizar_horas_live("1:50") == "01:50:00",
             "a saída sem ambiguidade para o mesmo caso é o dois-pontos",
             fluxo.normalizar_horas_live("1:50"))

    print()
    print("--- 6. o formato inválido barra o envio, não passa disfarçado ---")
    fonte_link = inspect.getsource(fluxo.registrar_link_externo)
    conferir("normalizar_horas_live(horas_live)" in fonte_link,
             "registrar_link_externo também confere o formato, não só a tela",
             "duas camadas: a tela avisa rápido, e a função garante de "
             "verdade, porque nem toda chamada futura vai passar pela tela")
    conferir("FORMATO DE HORAS INVALIDO" in fonte_link,
             "e existe um status próprio para esse erro, distinto de "
             "\"falta preencher\"",
             "campo com valor errado não é a mesma coisa que campo vazio")


if __name__ == "__main__":
    print("=" * 74)
    print("  Horas de live, no registro de link externo")
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
