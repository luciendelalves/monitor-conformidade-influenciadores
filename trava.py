# -*- coding: utf-8 -*-
"""
Trava de arquivo: impede que dois processos gravem o mesmo arquivo ao mesmo
tempo.

POR QUE EXISTE (29/08/2026)

Três arquivos deste programa são gravados em ciclo de ler, alterar e gravar:
o estado da conta do Instagram (contador do dia e pausa), o mapa de números de
perfil e o registro de análises já feitas. Com uma pessoa só usando, isso
nunca deu problema, porque nunca houve duas gravações ao mesmo tempo.

A partir do momento em que o programa fica num servidor com várias pessoas, e
com o trabalhador rodando ao lado do app, duas gravações simultâneas fazem a
segunda apagar o que a primeira acabou de escrever. No estado da conta, o que
se perde é justamente o contador de chamadas e a pausa do Instagram, ou seja,
o freio deixa de valer sem dar erro nenhum na tela. Foi o descuido com o
contador que marcou duas contas em agosto de 2026, e ali havia uma pessoa só.

DECISÕES

Funciona no Windows e no Linux porque o programa vai sair desta máquina para
um servidor. Não usa biblioteca de fora de propósito, para não acrescentar
dependência nova a poucos dias de subir.

A trava é aconselhada, não obrigatória: ela só vale entre processos que a
usam. Quem abrir o arquivo por fora (o Bloco de Notas, por exemplo) passa por
cima dela. Isso é aceitável aqui porque todos os pontos de gravação estão
neste mesmo programa.

USO

    import trava
    with trava.travar(CAMINHO_DO_ARQUIVO):
        dados = ler()
        dados["x"] = 1
        gravar(dados)

O ciclo inteiro precisa ficar dentro do bloco. Travar só a gravação não
resolve nada: o problema é a leitura ficar velha entre o ler e o gravar.
"""
import os
import time
from contextlib import contextmanager

# Quanto tempo esperar pela vez antes de desistir. Generoso de propósito: as
# operações protegidas aqui são todas curtas (gravar um JSON pequeno), então
# se passar disso é sinal de que algo travou de verdade, e aí é melhor dar
# erro visível do que esperar para sempre.
SEGUNDOS_LIMITE_PADRAO = 30

if os.name == "nt":
    import msvcrt

    def _tentar_travar(arquivo):
        try:
            msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    def _destravar(arquivo):
        try:
            msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
else:
    import fcntl

    def _tentar_travar(arquivo):
        try:
            fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def _destravar(arquivo):
        try:
            fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass


@contextmanager
def travar(caminho, segundos_limite=SEGUNDOS_LIMITE_PADRAO):
    """Segura a vez para mexer em `caminho`, e libera ao sair do bloco.

    A trava não é feita no arquivo de dados em si, e sim num arquivo vizinho
    de mesmo nome com ".trava" no fim. Isso é de propósito: a gravação segura
    dos dados é feita em arquivo temporário que depois substitui o definitivo,
    e nesse momento o arquivo original deixa de existir por um instante, o que
    derrubaria uma trava presa nele."""
    arquivo_trava = caminho + ".trava"
    pasta = os.path.dirname(arquivo_trava)
    if pasta:
        os.makedirs(pasta, exist_ok=True)

    arquivo = open(arquivo_trava, "a+b")
    try:
        # No Windows a trava vale sobre uma faixa de bytes, então o arquivo
        # precisa ter pelo menos um. Duas pessoas escrevendo esse byte ao
        # mesmo tempo não faz mal nenhum: o conteúdo não é lido por ninguém.
        if os.path.getsize(arquivo_trava) == 0:
            arquivo.write(b"1")
            arquivo.flush()

        limite = time.time() + segundos_limite
        while True:
            arquivo.seek(0)
            if _tentar_travar(arquivo):
                break
            if time.time() >= limite:
                raise TimeoutError(
                    f"Esperei {segundos_limite}s pela vez de mexer em "
                    f"{os.path.basename(caminho)} e outro processo não soltou. "
                    "Verifique se sobrou algum processo travado."
                )
            time.sleep(0.05)

        try:
            yield
        finally:
            arquivo.seek(0)
            _destravar(arquivo)
    finally:
        arquivo.close()


# Quanto insistir quando o Windows recusa mexer num arquivo porque outro
# processo está com ele aberto. As leituras deste programa são todas de
# arquivos pequenos e duram milissegundos, então em três segundos ou já
# passou, ou o problema é outro.
SEGUNDOS_INSISTINDO = 3


def substituir(origem, destino, segundos=SEGUNDOS_INSISTINDO):
    """os.replace que insiste um pouco quando o Windows recusa.

    POR QUE (medido em 29/08/2026): no Windows, trocar um arquivo pelo outro
    falha com "acesso negado" se qualquer processo estiver com o arquivo de
    destino aberto naquele exato instante, mesmo que só para ler. No Linux
    isso não acontece. Como agora o app lê os mesmos arquivos que o
    trabalhador grava, essa colisão deixou de ser hipótese: apareceu no
    primeiro teste com seis processos.

    A trava não resolve isto sozinha, porque quem só lê não pega trava. Em
    vez de obrigar toda leitura a travar, o que deixaria a tela mais lenta à
    toa, a gravação espera a leitura terminar, que dura milissegundos."""
    limite = time.time() + segundos
    while True:
        try:
            os.replace(origem, destino)
            return
        except PermissionError:
            if time.time() >= limite:
                raise
            time.sleep(0.03)


def ler_insistindo(caminho, funcao_de_leitura, segundos=SEGUNDOS_INSISTINDO):
    """Lê um arquivo insistindo pelo mesmo motivo de `substituir`, só que do
    outro lado: a leitura pode cair bem no instante em que o arquivo está
    sendo trocado. Devolver vazio nessa hora seria pior que esperar, porque
    vazio aqui significa "nunca foi analisado" e faz refazer trabalho."""
    limite = time.time() + segundos
    while True:
        try:
            return funcao_de_leitura(caminho)
        except (PermissionError, FileNotFoundError):
            if time.time() >= limite:
                raise
            time.sleep(0.03)
