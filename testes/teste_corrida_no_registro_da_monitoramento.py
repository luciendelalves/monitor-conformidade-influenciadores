# -*- coding: utf-8 -*-
"""
Duas escritas quase juntas na Monitoramento não podem se sobrescrever.

POR QUE ESTE TESTE EXISTE (16/09/2026)

O auditor perguntou, pensando no servidor com várias analistas ao mesmo
tempo: "corre risco das pesquisas sobrescreverem?" A resposta, olhando o
código antes desta correção, era sim, num caminho específico.

`registrar_na_monitoramento` lê quantas linhas a Monitoramento tem, calcula a
PRÓXIMA linha vazia (`len(atuais) + 2`), e SÓ DEPOIS escreve nela. Cada
chamada a `sheets_client.executar()` prende a trava da API durante a própria
chamada, mas a solta assim que ela termina. Entre o "ler quantas linhas tem" e
o "escrever na linha seguinte", a trava ficava livre. Duas chamadas quase
juntas podiam calcular a MESMA próxima linha, e a segunda escrita sobrescrevia
a primeira, sem erro nenhum e sem aviso: perda silenciosa de linha de
Monitoramento, a evidência principal da auditoria.

O caminho de download por fila já era protegido por acidente (o próprio
download é serializado num só worker, `linha_de_download` em trabalhador.py),
mas `registrar_link_externo` (a seção "Link só para registrar")
chama esta função direto da tela, sem fila nenhuma no meio. Duas pessoas
registrando link externo ao mesmo tempo, no servidor, corriam esse risco de
verdade.

A CORREÇÃO estende a trava da API por cima do trecho inteiro, leitura e
escrita juntas, então a segunda chamada espera a primeira terminar antes de
sequer ler quantas linhas existem.

TERCEIRA CAMADA, ACRESCENTADA EM 18/09/2026, DEPOIS DE CONFIRMAR COM O
AUDITOR QUE RESPONSÁVEL A E RESPONSÁVEL B JÁ ESCREVEM NA MESMA MONITORAMENTO REAL, DE
MÁQUINAS DIFERENTES: nem a RLock nem a trava de arquivo alcançam duas
máquinas físicas distintas, então a corrida de 16/09 continua possível entre
elas. `registrar_na_monitoramento` agora RELÊ a própria linha depois de
escrever e compara com o que mandou; se vier diferente (outra instalação
escreveu por cima), tenta tudo de novo, com a contagem de linhas renovada,
até `MAXIMO_TENTATIVAS_CORRIDA` vezes. Reproduzido de propósito, contra a
cópia de teste, em `testar_corrida_entre_maquinas.py` (raiz da pasta, não em
`ferramentas\`, porque esta escreve de propósito e aquela pasta é só de
conferência).

SEGUNDA CAMADA, ACRESCENTADA EM 18/09/2026: a trava de 16/09
(`sheets_client._TRAVA_DA_API`) é um `threading.RLock`, e só vale DENTRO do
processo que a criou. Ao planejar duas instalações (Marketing e Futebol)
escrevendo na MESMA Monitoramento real no mesmo servidor, cada uma é um
processo `trabalhador.py`/`painel.py` separado, cada um com sua própria cópia
da RLock na memória: a mesma corrida de 16/09 voltava a existir, um nível
acima. `_caminho_trava_entre_instalacoes` usa `trava.travar()`, que é trava
de arquivo do sistema operacional e por isso vale entre processos, num
arquivo fora da pasta de qualquer instalação (mesmo mecanismo já usado para o
estado da conta do Instagram).

Este teste é estrutural, e não um teste de concorrência de verdade: simular
duas threads (ou dois processos) batendo na API do Google de verdade gastaria
cota e seria instável. O que se prova aqui é que o trecho crítico está mesmo
dentro das duas travas, `trava.travar(...)` por fora e
`with sheets_client._TRAVA_DA_API` por dentro, na ordem certa.

Rodar:

    py testes\\teste_corrida_no_registro_da_monitoramento.py
"""
import inspect
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
    fonte = inspect.getsource(fluxo.registrar_na_monitoramento)

    conferir("trava.travar(_caminho_trava_entre_instalacoes(planilha))" in fonte,
             "abre a trava ENTRE PROCESSOS antes da trava da API")
    conferir("sheets_client._TRAVA_DA_API" in fonte,
             "e continua abrindo também a trava da API (thread-safety do cliente)")

    trava_processos_pos = fonte.find("trava.travar(_caminho_trava_entre_instalacoes(planilha))")
    trava_api_pos = fonte.find("sheets_client._TRAVA_DA_API")
    leitura_pos = fonte.find("atuais = sheets_client.executar")
    numero_linha_pos = fonte.find("numero_linha = len(atuais)")
    escrita_pos = fonte.rfind("spreadsheets().values().update(")

    conferir(0 < trava_processos_pos < trava_api_pos < leitura_pos,
             "a trava entre processos abre por FORA da trava da API, e as duas antes da leitura",
             f"processos {trava_processos_pos}, api {trava_api_pos}, leitura {leitura_pos}")
    conferir(leitura_pos < numero_linha_pos < escrita_pos,
             "e as duas continuam abertas até depois do cálculo da próxima linha e da escrita",
             f"leitura {leitura_pos}, cálculo {numero_linha_pos}, escrita {escrita_pos}")

    # A TRAVA COBRE TAMBÉM O TRECHO DO MEIO (dedup e colunas do cadastro), não
    # só as pontas: senão a corrida ainda existiria entre a leitura e a
    # escrita, só que com um passo a menos no lugar.
    trecho_entre = fonte[leitura_pos:escrita_pos]
    linhas_do_trecho = trecho_entre.split("\n")
    # Toda linha não-vazia do trecho crítico precisa estar recuada pelo menos
    # um nível a mais que "atuais = ...", senão ela escapou do `with`.
    recuo_da_leitura = len(fonte[fonte.rfind("\n", 0, leitura_pos) + 1:leitura_pos])
    fora_da_trava = [l for l in linhas_do_trecho[1:]
                     if l.strip() and (len(l) - len(l.lstrip(" "))) < recuo_da_leitura]
    conferir(not fora_da_trava,
             "nenhuma linha do trecho crítico escapou do recuo da trava",
             fora_da_trava[:3])

    # A TRAVA DA API É REENTRANTE: chamar sheets_client.executar() (que já
    # pega a mesma trava) de DENTRO do bloco não pode travar a própria thread.
    import sheets_client
    conferir(isinstance(sheets_client._TRAVA_DA_API, type(__import__("threading").RLock())),
             "a trava da API é um RLock, então pegar de novo na mesma thread não trava sozinha",
             type(sheets_client._TRAVA_DA_API))

    # A TRAVA ENTRE PROCESSOS PRECISA FICAR FORA DE QUALQUER INSTALAÇÃO
    # (18/09/2026): senão duas cópias da pasta do programa, cada uma
    # calculando o próprio caminho, nunca disputariam o mesmo arquivo, e a
    # trava não protegeria nada de verdade entre a instalação do Marketing e
    # a do Futebol.
    fonte_helper = inspect.getsource(fluxo._caminho_trava_entre_instalacoes)
    conferir("ProgramData" in fonte_helper,
             "o caminho da trava entre processos usa uma pasta comum da máquina (%ProgramData%)")
    conferir("PASTA_TESTE" not in fonte_helper and "BASE" not in fonte_helper,
             "e não depende da pasta de nenhuma instalação específica")

    # TERCEIRA CAMADA (18/09/2026): depois de escrever, relê a mesma linha e
    # compara. Sem isso, duas máquinas diferentes continuam podendo calcular
    # a mesma próxima linha sem nenhuma das duas perceber.
    confirmacao_pos = fonte.find("valor_gravado = confirmacao")
    conferir(confirmacao_pos > escrita_pos,
             "depois de escrever, relê a mesma linha antes de considerar sucesso",
             f"escrita {escrita_pos}, confirmação {confirmacao_pos}")
    conferir("!= link_drive" in fonte and "colidiu" in fonte,
             "e trata divergência do que foi lido contra o que foi mandado como colisão, não como sucesso")

    # E QUEM CHAMA TENTA DE NOVO SOB COLISÃO, em vez de desistir ou devolver
    # sucesso por engano.
    fonte_outer = inspect.getsource(fluxo.registrar_na_monitoramento)
    conferir("_uma_tentativa_de_registro()" in fonte_outer,
             "a função externa chama a tentativa dentro de um laço")
    conferir('status == "colidiu"' not in fonte_outer,
             "colisão não tem tratamento próprio: cai no laço e tenta de novo por padrão",
             "se este texto existir, confira se a lógica ainda segue o padrão ja_registrada/ok")
    conferir("MAXIMO_TENTATIVAS_CORRIDA" in fonte_outer,
             "existe um limite de tentativas, para não tentar para sempre sob colisão constante")


if __name__ == "__main__":
    print("=" * 74)
    print("  Corrida de escrita na Monitoramento: leitura+escrita atômicas")
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
