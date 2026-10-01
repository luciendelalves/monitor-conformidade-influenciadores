# -*- coding: utf-8 -*-
"""
Fila de trabalho gravada em disco.

POR QUE EXISTE (29/08/2026)

Até aqui, o lote de análise vivia dentro da aba do navegador de quem clicou:
o grupo de processos e as análises em andamento ficavam guardados na sessão
do Streamlit. Isso tem três defeitos que só aparecem quando mais de uma
pessoa usa o programa:

1. Cada aba aberta abria o SEU próprio grupo de processos. Cinco pessoas
   clicando ao mesmo tempo virava dez análises disputando o mesmo modelo de
   visão, que é um servidor só. Medido em 28/08/2026: acima de duas análises
   ao mesmo tempo não há ganho nenhum, elas só se enfileiram. Ou seja, o
   resultado de cinco pessoas clicando não é cinco vezes mais rápido, é todo
   mundo mais lento.
2. Fechar a aba ou perder a conexão deixava o lote órfão, consumindo a
   máquina sem ninguém conseguir acompanhar nem parar.
3. Ninguém enxergava o trabalho de ninguém. Duas pessoas mandavam analisar o
   mesmo vídeo sem saber.

Agora o trabalho é uma lista de tarefas em arquivo, e existe UM trabalhador
que consome essa lista (ver trabalhador.py). O app só põe tarefa na fila e
mostra a situação. Quem fecha a aba não perde nada, e o que uma pessoa
enfileira todas as outras enxergam.

COMO É POR DENTRO

Uma pasta por situação, e um arquivo JSON por tarefa:

    teste_watch_folder/fila_trabalho/
        pendente/    esperando o trabalhador pegar
        rodando/     o trabalhador está nesta agora
        concluida/   terminou
        falha/       terminou com erro

Mudar uma tarefa de situação é mover o arquivo de pasta, que o sistema
operacional faz de uma vez só. Não há banco de dados: para cinco pessoas e
algumas dezenas de tarefas por dia isso é suficiente, e o dia que não for,
troca-se só este arquivo, porque nada fora dele sabe como a fila é guardada.

O nome do arquivo começa com a data e a hora, então a ordem alfabética já é a
ordem de chegada.
"""
import json
import os
import shutil
import uuid
from datetime import datetime, timedelta

import trava

BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_FILA = os.path.join(BASE, "teste_watch_folder", "fila_trabalho")

PENDENTE = "pendente"
RODANDO = "rodando"
CONCLUIDA = "concluida"
FALHA = "falha"
SITUACOES = (PENDENTE, RODANDO, CONCLUIDA, FALHA)

# Tipos de tarefa que o trabalhador sabe executar.
VALIDAR = "validar"            # analisar um vídeo e escrever o veredito na Monitoramento
BAIXAR_FILA = "baixar_fila"    # rodar a fila de downloads (estágio A)
ENVIAR_ARQUIVOS = "enviar"     # organizar arquivos que a pessoa enviou pela tela
# Vídeo não editado, para conferência informal (23/09/2026, pedido do
# Marketing). Sobe pra pasta "vídeo bruto" do dia; nunca cria linha na
# Monitoramento nem entra na fila de validação. Ver fluxo.enviar_video_bruto.
ENVIAR_VIDEO_BRUTO = "enviar_bruto"

ARQUIVO_SINAL_DE_VIDA = os.path.join(PASTA_FILA, "trabalhador.json")
ARQUIVO_PEDIDO_DE_PARADA = os.path.join(PASTA_FILA, "pedido_de_parada.txt")

# Quanto o trabalhador espera antes de baixar sozinho um link que ficou parado
# na fila (08/09/2026). Mora aqui, e não só no trabalhador, porque a TELA
# precisa do mesmo número para dizer à pessoa quanto falta. Dois lugares com o
# número escrito à mão divergem na primeira mudança, e aí a tela promete um
# prazo que o trabalhador não cumpre.
#
# O motivo de existir e o porquê da espera estão em trabalhador.py, junto da
# função que decide.
SEGUNDOS_DE_ESPERA_ANTES_DE_BAIXAR_SOZINHO = 60

# O trabalhador dá sinal de vida a cada volta do laço dele (2s). Se passar
# disto sem sinal, o app considera que ele caiu. Folga grande de propósito:
# uma volta pode demorar mais quando ele está escrevendo na planilha, e dizer
# "caiu" para quem está de pé é pior do que demorar a perceber uma queda.
SEGUNDOS_SEM_SINAL_PARA_CONSIDERAR_PARADO = 45

# De quanto em quanto tempo o histórico de tarefas terminadas é limpo. Elas
# servem para mostrar o que aconteceu hoje na tela, não para virar arquivo
# morto: o histórico de verdade é a planilha.
HORAS_PARA_GUARDAR_TERMINADAS = 48


def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def quem_esta_usando():
    """Nome de quem está mexendo, para ficar registrado na tarefa.

    Hoje devolve o usuário do computador, porque o programa ainda não tem
    login. Quando o login entrar, passa a devolver a pessoa autenticada sem
    precisar mexer em mais nada: é por isso que a informação já é gravada
    agora, mesmo sem uso imediato. Sem ela, cinco pessoas usando o mesmo
    servidor produzem um histórico em que não dá para saber quem pediu o quê,
    o que numa ferramenta de auditoria é justamente o que não pode faltar."""
    # Só olha o Streamlit se ele já estiver carregado, ou seja, se quem
    # chamou for uma tela. No trabalhador e na linha de comando isso evita
    # carregar a biblioteca inteira à toa e evita o aviso de "sem contexto de
    # execução" que ela imprime nesse caso.
    try:
        import sys
        if "streamlit" in sys.modules:
            usuario = getattr(sys.modules["streamlit"], "user", None)
            email = None
            if usuario is not None:
                try:
                    email = usuario.get("email")
                except Exception:
                    email = getattr(usuario, "email", None)
            if email:
                return str(email)
    except Exception:
        pass
    return os.environ.get("USERNAME") or os.environ.get("USER") or "desconhecido"


def garantir_pastas():
    for situacao in SITUACOES:
        os.makedirs(os.path.join(PASTA_FILA, situacao), exist_ok=True)


def _caminho(situacao, id_tarefa):
    return os.path.join(PASTA_FILA, situacao, f"{id_tarefa}.json")


def _gravar(caminho, tarefa):
    """Grava em arquivo temporário e só então substitui o definitivo, pelo
    mesmo motivo do registro de análises: interrupção no meio da gravação
    deixaria um arquivo cortado, e aí a tarefa some da fila sem ter rodado."""
    temporario = caminho + ".tmp"
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(tarefa, f, ensure_ascii=False, indent=2)
    trava.substituir(temporario, caminho)


def _carregar_json(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _ler(caminho):
    """Devolve None quando o arquivo não dá para ler.

    Insiste um pouco antes de desistir: a tela lê estes arquivos ao mesmo
    tempo que o trabalhador os grava, e no Windows os dois se atrapelam por
    alguns milissegundos (ver trava.substituir). Sem insistir, uma tarefa
    desaparecia da tela por um instante sem motivo."""
    try:
        return trava.ler_insistindo(caminho, _carregar_json)
    except (ValueError, OSError):
        return None


def criar(tipo, dados, rotulo="", criada_por=None):
    """Põe uma tarefa nova na fila e devolve ela."""
    garantir_pastas()
    id_tarefa = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
    tarefa = {
        "id": id_tarefa,
        "tipo": tipo,
        "rotulo": rotulo,
        "dados": dados,
        "situacao": PENDENTE,
        "criada_em": _agora(),
        "criada_por": criada_por or quem_esta_usando(),
        "mensagens": [],
    }
    _gravar(_caminho(PENDENTE, id_tarefa), tarefa)
    return tarefa


def listar(situacao, tipo=None):
    """Tarefas de uma situação, da mais antiga para a mais nova."""
    pasta = os.path.join(PASTA_FILA, situacao)
    if not os.path.isdir(pasta):
        return []
    tarefas = []
    for nome in sorted(os.listdir(pasta)):
        if not nome.endswith(".json"):
            continue
        tarefa = _ler(os.path.join(pasta, nome))
        if tarefa and (tipo is None or tarefa.get("tipo") == tipo):
            tarefas.append(tarefa)
    return tarefas


def contar(situacao, tipo=None):
    return len(listar(situacao, tipo))


def resumo(tipo=None):
    return {situacao: contar(situacao, tipo) for situacao in SITUACOES}


def ha_trabalho(tipo=None):
    """True quando existe alguma tarefa esperando ou em andamento."""
    return bool(listar(PENDENTE, tipo) or listar(RODANDO, tipo))


def proxima(tipos=None):
    """Pega a tarefa pendente mais antiga e passa ela para "rodando".

    Só o trabalhador chama isto. A trava está aqui mesmo assim, para o caso de
    alguém subir um segundo trabalhador por engano: sem ela os dois pegariam a
    mesma tarefa e o vídeo seria analisado duas vezes."""
    garantir_pastas()
    with trava.travar(os.path.join(PASTA_FILA, "fila")):
        for tarefa in listar(PENDENTE):
            if tipos and tarefa.get("tipo") not in tipos:
                continue
            origem = _caminho(PENDENTE, tarefa["id"])
            destino = _caminho(RODANDO, tarefa["id"])
            tarefa["situacao"] = RODANDO
            tarefa["comecou_em"] = _agora()
            try:
                _gravar(origem, tarefa)
                os.replace(origem, destino)
            except OSError:
                continue
            return tarefa
    return None


def anotar(tarefa, mensagem):
    """Acrescenta uma linha de acompanhamento à tarefa em andamento, para
    quem estiver olhando a tela ver o que está acontecendo agora."""
    tarefa.setdefault("mensagens", []).append(f"{datetime.now():%H:%M:%S} {mensagem}")
    # Guarda só as últimas: a fila de downloads escreve bastante e o arquivo
    # não precisa virar log.
    tarefa["mensagens"] = tarefa["mensagens"][-200:]
    caminho = _caminho(RODANDO, tarefa["id"])
    if os.path.exists(caminho):
        _gravar(caminho, tarefa)


def _encerrar(tarefa, situacao, extra=None):
    tarefa.update(extra or {})
    tarefa["situacao"] = situacao
    tarefa["terminou_em"] = _agora()
    _gravar(_caminho(situacao, tarefa["id"]), tarefa)
    try:
        os.remove(_caminho(RODANDO, tarefa["id"]))
    except OSError:
        pass
    return tarefa


def concluir(tarefa, resultado=None):
    return _encerrar(tarefa, CONCLUIDA, {"resultado": resultado or {}})


def falhar(tarefa, erro):
    return _encerrar(tarefa, FALHA, {"erro": str(erro)[:1000]})


def cancelar_pendentes(tipo=None, de_quem=None):
    """Tira da fila o que ainda não começou. O que já está rodando termina:
    interromper análise no meio só desperdiça o que já foi processado.

    `de_quem` limita ao que aquela pessoa pediu. Existe desde 29/08/2026: a
    fila é compartilhada, e sem esse limite um clique tirava da fila o que as
    outras quatro pessoas tinham mandado analisar, possivelmente no meio do
    trabalho delas."""
    apagadas = 0
    for tarefa in listar(PENDENTE, tipo):
        if de_quem is not None and tarefa.get("criada_por") != de_quem:
            continue
        try:
            os.remove(_caminho(PENDENTE, tarefa["id"]))
            apagadas += 1
        except OSError:
            pass
    return apagadas


def pendentes_por_pessoa(tipo=None):
    """Quantas tarefas esperando, por quem pediu. Serve para a tela dizer o
    que exatamente vai sumir antes de alguém clicar."""
    contagem = {}
    for tarefa in listar(PENDENTE, tipo):
        quem = tarefa.get("criada_por") or "sem identificação"
        contagem[quem] = contagem.get(quem, 0) + 1
    return contagem


def reenfileirar(id_tarefa):
    """Devolve para a fila uma tarefa que falhou. Para análise isso é barato:
    o resultado já ficou guardado, então ela não é refeita, só a escrita na
    planilha é tentada de novo."""
    for situacao in (FALHA, CONCLUIDA):
        caminho = _caminho(situacao, id_tarefa)
        tarefa = _ler(caminho)
        if not tarefa:
            continue
        tarefa["situacao"] = PENDENTE
        tarefa["tentativas"] = int(tarefa.get("tentativas") or 0) + 1
        tarefa.pop("erro", None)
        _gravar(_caminho(PENDENTE, id_tarefa), tarefa)
        try:
            os.remove(caminho)
        except OSError:
            pass
        return tarefa
    return None


def recuperar_orfas():
    """Tarefa que ficou em "rodando" quer dizer que o trabalhador morreu no
    meio dela. Volta para a fila.

    Repetir é seguro nos dois tipos de tarefa que existem hoje: a análise usa
    o resultado guardado e só escreve em célula vazia, e a fila de downloads
    só processa linha sem situação preenchida. Se algum dia entrar uma tarefa
    que não possa ser repetida, ela precisa ser tratada aqui de outro jeito."""
    garantir_pastas()
    recuperadas = []
    for tarefa in listar(RODANDO):
        tarefa["situacao"] = PENDENTE
        tarefa.setdefault("mensagens", []).append(
            f"{datetime.now():%H:%M:%S} o trabalhador foi reiniciado, esta tarefa voltou para a fila")
        _gravar(_caminho(PENDENTE, tarefa["id"]), tarefa)
        try:
            os.remove(_caminho(RODANDO, tarefa["id"]))
        except OSError:
            pass
        recuperadas.append(tarefa)
    return recuperadas


def limpar_terminadas(horas=HORAS_PARA_GUARDAR_TERMINADAS, tipo=None):
    """Apaga o histórico de tarefas terminadas mais velhas que o prazo.

    Com horas=0 apaga o histórico inteiro, que é o que o botão de limpar da
    tela usa. Isso mexe SÓ no acompanhamento da tela: o veredito de cada linha
    continua na Monitoramento, que é a fonte única, e os vídeos continuam no
    Drive. `tipo` limita a um tipo de tarefa, para o botão de uma tela não
    apagar o histórico da outra."""
    limite = datetime.now() - timedelta(hours=horas)
    apagadas = 0
    for situacao in (CONCLUIDA, FALHA):
        for tarefa in listar(situacao, tipo):
            quando = tarefa.get("terminou_em") or tarefa.get("criada_em")
            try:
                if datetime.strptime(quando, "%Y-%m-%d %H:%M:%S") >= limite:
                    continue
            except (TypeError, ValueError):
                continue
            try:
                os.remove(_caminho(situacao, tarefa["id"]))
                apagadas += 1
            except OSError:
                pass
    return apagadas


def esvaziar_tudo():
    """Apaga a fila inteira, inclusive o histórico. Existe para teste e para
    recomeçar do zero se a fila ficar num estado esquisito."""
    if os.path.isdir(PASTA_FILA):
        shutil.rmtree(PASTA_FILA, ignore_errors=True)
    garantir_pastas()


# ------------------------------------------------------------------
# Sinal de vida do trabalhador
# ------------------------------------------------------------------
def registrar_sinal_de_vida(informacoes):
    garantir_pastas()
    dados = {"atualizado_em": _agora(), **informacoes}
    try:
        _gravar(ARQUIVO_SINAL_DE_VIDA, dados)
    except OSError:
        pass


def ler_sinal_de_vida():
    return _ler(ARQUIVO_SINAL_DE_VIDA) or {}


def trabalhador_de_pe():
    """Devolve (está de pé, informações). Serve para o app avisar que ninguém
    vai pegar a tarefa antes que a pessoa fique esperando à toa."""
    sinal = ler_sinal_de_vida()
    quando = sinal.get("atualizado_em")
    if not quando:
        return False, sinal
    try:
        visto = datetime.strptime(quando, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False, sinal
    atraso = (datetime.now() - visto).total_seconds()
    return atraso <= SEGUNDOS_SEM_SINAL_PARA_CONSIDERAR_PARADO, sinal


def pedir_parada():
    """Pede ao trabalhador que termine o que está fazendo e encerre. Usado
    antes de mexer no código, porque alterar arquivo com lote rodando derruba
    o lote no meio."""
    garantir_pastas()
    with open(ARQUIVO_PEDIDO_DE_PARADA, "w", encoding="utf-8") as f:
        f.write(_agora())


def parada_pedida():
    return os.path.exists(ARQUIVO_PEDIDO_DE_PARADA)


def limpar_pedido_de_parada():
    try:
        os.remove(ARQUIVO_PEDIDO_DE_PARADA)
    except OSError:
        pass


# ------------------------------------------------------------------
# Consultas usadas pelas telas
# ------------------------------------------------------------------
def links_em_andamento():
    """Links de vídeo que já estão na fila ou sendo analisados agora. A tela
    usa isto para não deixar a mesma pessoa (ou duas pessoas diferentes)
    enfileirarem o mesmo vídeo duas vezes."""
    links = set()
    for situacao in (PENDENTE, RODANDO):
        for tarefa in listar(situacao, VALIDAR):
            link = (tarefa.get("dados") or {}).get("link")
            if link:
                links.add(link)
    return links


def ultimas_terminadas(tipo=None, quantas=25):
    """As últimas tarefas terminadas, da mais recente para a mais antiga,
    juntando as que deram certo e as que falharam."""
    tarefas = listar(CONCLUIDA, tipo) + listar(FALHA, tipo)
    tarefas.sort(key=lambda t: t.get("terminou_em") or "", reverse=True)
    return tarefas[:quantas]
