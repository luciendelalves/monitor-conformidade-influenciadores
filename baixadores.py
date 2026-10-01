# -*- coding: utf-8 -*-
"""
Estado e manutenção das bibliotecas que baixam vídeo.

POR QUE ESTE ARQUIVO EXISTE (05/09/2026)

Pedido do auditor: "queria implementar mecanismos que pode atualizar ou alterar
o programa de baixar, pq sei que são voláteis". Ele está certo sobre a
volatilidade, e o `requirements.txt` já avisava: o yt-dlp é a peça que persegue
as mudanças do Instagram, e uma versão travada por muito tempo PARA DE
FUNCIONAR, com o sintoma de download falhando sem motivo aparente.

O PROBLEMA NÃO ERA FALTA DE RESERVA, ERA FALTA DE AVISO. A cadeia de recuo já
existia e é boa: Story tenta yt-dlp e cai no instaloader; post tenta yt-dlp
anônimo, depois autenticado, depois instaloader pelo código do post; e, se tudo
falhar, a pessoa baixa à mão e sobe pelo envio de arquivo. O que faltava era o
programa saber, e dizer, que a versão instalada está envelhecendo. Ela envelhece
em silêncio, e o silêncio vira "não sei por que parou de funcionar".

MEDIDO EM 05/09/2026, e foi o que motivou o arquivo: a versão travada era a
2026.7.4, de dois meses antes, com a 2026.8.19 disponível. Nada na tela dizia.

POR QUE A VERSÃO CONTINUA TRAVADA no requirements.txt, mesmo sendo volátil: o
programa produz evidência de auditoria, e reproduzir o ambiente que gerou um
resultado importa. Travar é decisão certa; o que faltava era o lembrete de que
travado não quer dizer esquecido.

O QUE ESTE ARQUIVO NÃO FAZ: ele não atualiza nada sozinho. Atualizar a peça que
baixa é ato consciente, feito com o trabalhador parado e seguido de teste. Aqui
só se mede o estado e se monta o comando; quem executa é uma pessoa.
"""
import datetime
import importlib
import os
import re
import sys

# O subprocess É IMPORTADO DENTRO DE atualizar(), e não no topo, de propósito.
# Ele serve a UMA função, a única que executa alguma coisa. Deixá-lo no topo
# daria a impressão de que o módulo inteiro roda comandos, quando o resto só
# mede e monta texto. Ver o comentário longo em cima de atualizar().

# Quantos dias até a versão instalada ser considerada velha.
#
# 45 DIAS, E O NÚMERO TEM RAZÃO DE SER: o yt-dlp publica versão a cada poucas
# semanas, e as quebras do Instagram costumam aparecer no intervalo de um a dois
# meses. Avisar a cada 15 dias viraria ruído que se aprende a ignorar; avisar a
# cada 90 chegaria depois de já ter quebrado.
DIAS_ATE_ENVELHECER = 45

# As bibliotecas que baixam vídeo, na ordem de importância para o fluxo.
#
# `papel` diz o que se perde se ela falhar, e é isso que a tela mostra: a pessoa
# não precisa saber o nome da biblioteca, precisa saber o que para de funcionar.
BAIXADORES = (
    {
        "modulo": "yt_dlp",
        "nome": "yt-dlp",
        "papel": "baixa Story, Reel e post do Instagram, e vídeo de YouTube, "
                 "TikTok e X. É o caminho principal.",
        "reserva": "Se falhar, o programa tenta o instaloader sozinho.",
    },
    {
        "modulo": "instaloader",
        "nome": "instaloader",
        "papel": "reserva do Instagram: entra quando o yt-dlp não consegue.",
        "reserva": "Se falhar também, resta o envio de arquivo pela tela.",
    },
    {
        "modulo": "curl_cffi",
        "nome": "curl_cffi",
        "papel": "faz o programa se apresentar como navegador de verdade, o que "
                 "reduz a chance de ser barrado.",
        "reserva": "Sem ele o download funciona igual, só mais exposto. O "
                   "programa recua sozinho quando a rede da empresa o recusa.",
    },
)


def _versao_instalada(modulo):
    """A versão que está rodando AGORA, lida do módulo importado.

    Lê do módulo, e não do requirements.txt, de propósito: o que importa é o que
    está instalado nesta máquina, não o que está escrito no arquivo. Os dois
    podem divergir, e é justamente essa divergência que interessa saber."""
    try:
        mod = importlib.import_module(modulo)
    except Exception:
        return None
    for atributo in ("__version__", "version"):
        valor = getattr(mod, atributo, None)
        if isinstance(valor, str):
            return valor
        # yt_dlp guarda em yt_dlp.version.__version__
        interno = getattr(valor, "__version__", None)
        if isinstance(interno, str):
            return interno
    try:
        from importlib.metadata import version
        return version(modulo.replace("_", "-"))
    except Exception:
        return None


def _data_da_versao(versao):
    """A data embutida numa versão de calendário como "2026.8.19".

    O yt-dlp versiona por data, então a própria versão diz quando saiu, sem
    precisar consultar a internet. Bibliotecas que não versionam assim (o
    instaloader usa 4.15.3) devolvem None, e para elas não há idade a calcular."""
    m = re.fullmatch(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", str(versao or "").strip())
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# QUANDO VI ESTA VERSÃO PELA PRIMEIRA VEZ
# ---------------------------------------------------------------------------
# POR QUE ISTO EXISTE (05/09/2026)
#
# A idade calculada pela versão só funciona para quem versiona por data, e só o
# yt-dlp faz isso. Para o instaloader (4.15.3) e o curl_cffi (0.15.0) o programa
# dizia honestamente "não sei a idade", e o auditor apontou o problema: "temos
# que ter uma forma de manter tudo atualizado, não?".
#
# E O RISCO É PIOR NA RESERVA. O instaloader só roda quando o yt-dlp falha, ou
# seja, quase nunca. Se ele apodrecer, ninguém descobre no uso diário: descobre
# no dia em que o yt-dlp quebrar, que é exatamente o dia em que ele era
# necessário. Backup que nunca foi exercitado é esperança, não plano.
#
# A SOLUÇÃO FUNCIONA SEM INTERNET, de propósito. Em vez de perguntar ao PyPI
# qual é a última versão (consulta que a rede da empresa pode barrar, e que já
# barra domínio de ferramenta), o programa guarda QUANDO viu cada versão pela
# primeira vez. Isso não diz "existe versão nova", diz "faz X dias que ninguém
# mexe nisso", que é o aviso que importa e serve para as três bibliotecas.
ARQUIVO_VERSOES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "teste_watch_folder", "versoes_dos_baixadores.json")


def _ler_versoes_vistas():
    try:
        import json
        with open(ARQUIVO_VERSOES, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def registrar_versoes_vistas(hoje=None, caminho=None):
    """Anota a data em que cada versão instalada foi vista pela primeira vez.

    Só grava quando a versão MUDA. Assim a data guardada é a da troca, e a
    diferença até hoje é o tempo que aquela versão está parada nesta máquina.

    Devolve o mapa {nome: {"versao", "visto_em"}}."""
    import json
    hoje = hoje or datetime.date.today()
    caminho = caminho or ARQUIVO_VERSOES
    try:
        with open(caminho, encoding="utf-8") as f:
            mapa = json.load(f)
    except Exception:
        mapa = {}

    mudou = False
    for b in BAIXADORES:
        versao = _versao_instalada(b["modulo"])
        if not versao:
            continue
        registro = mapa.get(b["nome"]) or {}
        if registro.get("versao") != versao:
            mapa[b["nome"]] = {"versao": versao, "visto_em": hoje.isoformat()}
            mudou = True
    if mudou:
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(mapa, f, ensure_ascii=False, indent=2)
        except Exception:
            # Não conseguir anotar não pode derrubar a tela: o aviso de idade é
            # comodidade, e a falta dele não impede baixar nada.
            pass
    return mapa


def estado(hoje=None):
    """Retrato das bibliotecas de download, para a tela mostrar.

    Devolve uma lista de dicionários com: nome, papel, reserva, versao, data,
    dias, envelheceu (bool ou None quando não dá para saber) e presente.

    `hoje` é parâmetro para o teste poder fixar a data em vez de depender do
    calendário de quem roda o teste."""
    hoje = hoje or datetime.date.today()
    vistas = _ler_versoes_vistas()
    linhas = []
    for b in BAIXADORES:
        versao = _versao_instalada(b["modulo"])
        data = _data_da_versao(versao)
        dias = (hoje - data).days if data else None
        # SEGUNDA FONTE DE IDADE, para quem não versiona por data. Aqui "idade"
        # quer dizer outra coisa: não é quando a versão saiu, é há quantos dias
        # ela está parada nesta máquina. Serve ao mesmo propósito (avisar que
        # ninguém mexe nisso) e é a única disponível para instaloader e
        # curl_cffi. Só entra quando a primeira não existe, para não sobrepor a
        # informação melhor pela pior.
        dias_parada = None
        reg = vistas.get(b["nome"]) or {}
        if reg.get("versao") == versao and reg.get("visto_em"):
            try:
                visto = datetime.date.fromisoformat(reg["visto_em"])
                dias_parada = (hoje - visto).days
            except ValueError:
                dias_parada = None
        linhas.append({
            "nome": b["nome"],
            "modulo": b["modulo"],
            "papel": b["papel"],
            "reserva": b["reserva"],
            "presente": versao is not None,
            "versao": versao,
            "data": data,
            "dias": dias,
            "dias_parada": dias_parada,
            # None quando a versão não é de calendário: não é "está novo", é
            # "não dá para saber pela versão". Dizer as duas coisas com o mesmo
            # valor esconderia a diferença.
            # Envelheceu pela data da versão OU por estar parada há muito
            # tempo. As duas medem coisas diferentes e as duas justificam olhar.
            "envelheceu": ((dias is not None and dias > DIAS_ATE_ENVELHECER)
                           or (dias is None and dias_parada is not None
                               and dias_parada > DIAS_ATE_ENVELHECER)),
        })
    return linhas


def precisa_de_atencao(hoje=None):
    """Só as bibliotecas velhas ou ausentes. Vazio quer dizer tudo em ordem."""
    return [b for b in estado(hoje)
            if b["envelheceu"] or not b["presente"]]


# ---------------------------------------------------------------------------
# A VISÃO DE QUEBRA
# ---------------------------------------------------------------------------
# POR QUE ISTO EXISTE (05/09/2026)
#
# Pedido do auditor, comparando com a ferramenta do Marketing: "seria
# interessante ter uma visão caso as extensões deixem de funcionar por conta de
# atualizações do instagram, isso é possível?".
#
# É possível, E DE GRAÇA, porque não precisa de sonda nova. O programa já grava
# cada tentativa com uma CLASSE de resultado diferente, e uma quebra de
# biblioteca tem assinatura própria:
#
#   OK                    baixou
#   SEM STORY NO AR       o perfil não tem story. Não é defeito de nada.
#   CONTA PAUSADA         a conta está de castigo. Problema de ritmo, não de
#                         biblioteca.
#   BAIXAR MANUALMENTE    o Instagram bloqueou ou exigiu login.
#   número do perfil      falta descobrir o número. Caso com solução conhecida.
#   FALTA PASTA NO DRIVE  problema de Drive, nada a ver com download.
#   FALHA                 o resto. É AQUI que a quebra aparece.
#
# A CHAVE É QUE "FALHA" É A CLASSE RESIDUAL. Quando o Instagram muda e a
# biblioteca não acompanha, o erro não é bloqueio nem story ausente: é o
# extrator não entendendo mais a página, e isso cai em FALHA. Uma sequência de
# FALHA onde antes havia OK é o sinal.
#
# POR QUE NÃO UMA SONDA QUE BAIXA UM VÍDEO DE TESTE: porque toda conversa com o
# Instagram conta no teto do dia e soma no padrão de acesso que já derrubou duas
# contas. Uma sonda periódica gastaria cota para descobrir o que o próprio
# trabalho do dia já revela.
CLASSES_DE_RESULTADO = (
    ("ok", "baixou", lambda s: s.strip().upper() == "OK"),
    ("sem_story", "perfil sem story no ar",
     lambda s: "SEM STORY NO AR" in s.upper()),
    ("conta_pausada", "conta em pausa ou no teto do dia",
     lambda s: "PAUSAD" in s.upper() or "TETO" in s.upper()),
    ("bloqueio", "Instagram bloqueou ou exigiu login",
     lambda s: "BAIXAR MANUALMENTE" in s.upper()),
    ("perfil_desconhecido", "falta descobrir o número do perfil",
     lambda s: "número do perfil" in s or "numero do perfil" in s),
    ("drive", "problema de pasta no Drive",
     lambda s: "FALTA PASTA NO DRIVE" in s.upper()),
    ("falha", "falha sem causa conhecida",
     lambda s: s.strip().upper().startswith("FALHA")),
)


def classificar_resultado(status):
    """A classe de um status do registro. Ordem importa: a primeira que casa."""
    s = str(status or "")
    for chave, _rotulo, casa in CLASSES_DE_RESULTADO:
        if casa(s):
            return chave
    return "outro"


def saude_do_download(dias=7, ler_log=None, hoje=None):
    """Retrato do download nos últimos `dias`, lido do registro de fluxo.

    Devolve {"tentativas", "por_classe", "por_dia", "suspeita_de_quebra",
    "motivo"}.

    `suspeita_de_quebra` é conservadora de propósito: exige um mínimo de
    tentativas antes de acusar, senão dois erros num dia parado viram alarme.
    Alarme falso ensina a ignorar o alarme."""
    import collections
    hoje = hoje or datetime.date.today()
    if ler_log is None:
        import fluxo_downloads
        ler_log = fluxo_downloads.ler_log
    try:
        registros = ler_log() or []
    except Exception as e:
        return {"tentativas": 0, "por_classe": {}, "por_dia": {},
                "suspeita_de_quebra": False,
                "motivo": f"não consegui ler o registro: {str(e)[:90]}"}

    limite = hoje - datetime.timedelta(days=dias)
    por_classe = collections.Counter()
    por_dia = collections.defaultdict(collections.Counter)
    for r in registros:
        # Só o estágio A é download. O resto é análise e correção, e misturar
        # inflaria o denominador com coisa que não fala com o Instagram.
        if (r.get("estagio") or "").strip().upper() != "A":
            continue
        quando = str(r.get("quando") or "")[:10]
        try:
            dia = datetime.date.fromisoformat(quando)
        except ValueError:
            continue
        if dia < limite:
            continue
        classe = classificar_resultado(r.get("status"))
        por_classe[classe] += 1
        por_dia[dia.isoformat()][classe] += 1

    tentativas = sum(por_classe.values())
    ok = por_classe.get("ok", 0)
    falhas = por_classe.get("falha", 0)

    # O GATILHO. Duas condições juntas, e as duas existem para evitar alarme
    # falso: volume mínimo (um dia com 3 tentativas não diz nada) e falha
    # residual dominando (não bloqueio, não story ausente, não conta pausada).
    MINIMO_PARA_OPINAR = 8
    suspeita = False
    if tentativas >= MINIMO_PARA_OPINAR and falhas >= 3:
        proporcao = falhas / tentativas
        if proporcao >= 0.5:
            suspeita = True
            motivo = (f"{falhas} de {tentativas} tentativas nos últimos "
                      f"{dias} dias falharam sem causa conhecida "
                      f"({proporcao:.0%}), e só {ok} baixaram. Falha sem causa "
                      f"conhecida em série é a assinatura de biblioteca que "
                      f"deixou de entender a página do Instagram.")
        else:
            motivo = (f"{falhas} falha(s) sem causa conhecida em {tentativas} "
                      f"tentativas. Abaixo do que caracterizaria quebra.")
    elif tentativas < MINIMO_PARA_OPINAR:
        motivo = (f"apenas {tentativas} tentativa(s) nos últimos {dias} dias, "
                  f"pouco para opinar sobre saúde do download.")
    else:
        motivo = f"{ok} de {tentativas} tentativas baixaram normalmente."

    return {"tentativas": tentativas, "por_classe": dict(por_classe),
            "por_dia": {d: dict(c) for d, c in sorted(por_dia.items())},
            "suspeita_de_quebra": suspeita, "motivo": motivo}


def comando_de_atualizacao(nomes=None):
    """O comando que atualiza, montado para quem preferir rodar à mão."""
    alvos = nomes or [b["nome"] for b in BAIXADORES]
    return f"py -m pip install --upgrade {' '.join(alvos)}"


def comando_de_volta(nome, versao):
    """Como desfazer, se a versão nova quebrar.

    Existe porque atualizar sem saber voltar é aposta. A versão anterior é
    guardada antes de atualizar, e este comando é mostrado junto do resultado."""
    return f"py -m pip install {nome}=={versao}"


# ---------------------------------------------------------------------------
# A ATUALIZAÇÃO GUIADA
# ---------------------------------------------------------------------------
# POR QUE ELA EXECUTA, DEPOIS DE EU TER ARGUMENTADO QUE NÃO DEVIA (05/09/2026).
#
# A primeira versão deste arquivo só MONTAVA o comando, e o argumento era bom:
# um botão de um clique esconde três coisas que quebram de verdade (trabalhador
# de pé segura a versão velha em memória, requirements.txt desatualizado faz a
# próxima máquina instalar a versão velha, e sem teste ninguém sabe se a versão
# nova funciona).
#
# O auditor trouxe informação que muda a conta: "outras pessoas mais leigas que
# irão utilizar". Para quem não abre terminal, "é só rodar um comando" não é
# instrução, é obstáculo, e o resultado prático de exigir isso é que ninguém
# atualiza nunca. Aí a peça mais volátil do programa apodrece.
#
# A RESPOSTA CERTA NÃO ERA TIRAR O BOTÃO, ERA PÔR AS TRAVAS DENTRO DELE. As três
# coisas que o botão escondia agora são passos que ele executa e relata:
#
#   1. recusa rodar com o trabalhador de pé, e diz como encerrá-lo
#   2. anota a versão nova no requirements.txt, com a data
#   3. devolve o comando de volta, caso a versão nova quebre
#
# O que ele NÃO faz é dizer que deu certo sem prova: quem confirma é o teste de
# download, rodado depois, com o trabalhador de pé de novo.
TEMPO_LIMITE_ATUALIZACAO = 300  # segundos


def atualizar(nomes, executor=None):
    """Atualiza as bibliotecas indicadas e devolve o que mudou.

    `executor` existe para o teste poder rodar sem instalar nada de verdade.
    Em uso normal ele é None e a função chama o pip.

    Devolve: {"ok", "saida", "antes", "depois", "mudou", "comando"}.
    `antes` e `depois` são {nome: versao}, e `mudou` lista quem realmente
    trocou de versão. Comparar as duas pontas importa: pip pode terminar sem
    erro e sem atualizar nada, e tratar isso como sucesso seria mentir."""
    import subprocess

    alvos = list(nomes)
    por_nome = {b["nome"]: b["modulo"] for b in BAIXADORES}
    antes = {n: _versao_instalada(por_nome[n]) for n in alvos if n in por_nome}

    comando = [sys.executable, "-m", "pip", "install", "--upgrade", *alvos]
    if executor is None:
        def executor(cmd):
            return subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=TEMPO_LIMITE_ATUALIZACAO)
    try:
        resultado = executor(comando)
        codigo = resultado.returncode
        saida = (resultado.stdout or "") + (resultado.stderr or "")
    except Exception as e:
        return {"ok": False, "saida": f"Não consegui rodar o pip: {e}",
                "antes": antes, "depois": antes, "mudou": [],
                "comando": " ".join(comando)}

    # A VERSÃO É LIDA DE NOVO NUM PROCESSO À PARTE, e não do módulo já
    # importado: este processo carregou a biblioteca antes da atualização e
    # continua com a versão velha em memória. Perguntar a ele devolveria sempre
    # a versão antiga, e o programa concluiria que nada mudou.
    depois = {}
    for n in alvos:
        modulo = por_nome.get(n)
        if not modulo:
            continue
        try:
            import subprocess as _sp
            r = _sp.run([sys.executable, "-c",
                         f"import {modulo};"
                         f"v=getattr({modulo},'__version__',None) or "
                         f"getattr(getattr({modulo},'version',None),'__version__','');"
                         f"print(v)"],
                        capture_output=True, text=True, timeout=60)
            depois[n] = (r.stdout or "").strip() or None
        except Exception:
            depois[n] = None

    mudou = [n for n in alvos
             if antes.get(n) and depois.get(n) and antes[n] != depois[n]]
    return {"ok": codigo == 0, "saida": saida[-4000:], "antes": antes,
            "depois": depois, "mudou": mudou, "comando": " ".join(comando)}


def anotar_no_requirements(nome, versao, caminho=None):
    """Trava a versão nova no requirements.txt, com a data.

    SEM ISSO A ATUALIZAÇÃO É PELA METADE: a máquina de quem clicou fica nova e
    qualquer outra que instale pelo requirements.txt continua na versão velha.
    Já é o tipo de diferença que produz "aqui funciona e lá não".

    Devolve (mudou, linha_nova) ou (False, motivo)."""
    caminho = caminho or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if not os.path.exists(caminho):
        return False, "requirements.txt não encontrado"
    with open(caminho, encoding="utf-8") as f:
        texto = f.read()

    hoje = datetime.date.today().strftime("%d/%m/%Y")
    linha_nova = f"{nome}=={versao}  # atualizado em {hoje}"
    # Casa a linha do pacote com ou sem comentário depois, e nada mais: o nome
    # aparece também nos comentários explicativos acima, e substituir lá
    # estragaria o texto que explica por que a versão é travada.
    padrao = re.compile(rf"(?m)^{re.escape(nome)}==[^\s#]+(\s*#.*)?$")
    if not padrao.search(texto):
        return False, f"não achei a linha de {nome} no requirements.txt"
    novo = padrao.sub(linha_nova, texto, count=1)
    if novo == texto:
        return False, "nada mudou"
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write(novo)
    return True, linha_nova


COMO_ATUALIZAR = """1. Feche a janela do trabalhador (o processo antigo continua
   com a versão velha em memória enquanto estiver de pé).
2. Rode:  {comando}
3. Anote a versão nova no requirements.txt, com a data.
4. Rode:  py testes\\teste_download_em_duas_etapas.py
5. Suba o trabalhador de novo."""


def instrucoes(nomes=None):
    return COMO_ATUALIZAR.format(comando=comando_de_atualizacao(nomes))


# O QUE DIZER QUANDO TUDO FALHA. Mora aqui, e não na tela, porque mais de um
# lugar precisa dizer a mesma coisa: o erro do download, a tela de fila e o
# aviso de versão velha. Antes de 05/09/2026 a mensagem de falha não mencionava
# o envio de arquivo, então quem via o erro não sabia que existia saída.
SAIDA_MANUAL = (
    "Se nada funcionar: baixe o vídeo à mão e use o **envio de arquivo**. "
    "O programa faz o resto igual."
)


def diagnostico(hoje=None):
    """Texto curto de uma linha por biblioteca, para log e para a tela."""
    partes = []
    for b in estado(hoje):
        if not b["presente"]:
            partes.append(f"{b['nome']}: NÃO INSTALADO")
        elif b["dias"] is None:
            partes.append(f"{b['nome']} {b['versao']}")
        else:
            idade = f"{b['dias']} dia(s)"
            marca = " VELHA" if b["envelheceu"] else ""
            partes.append(f"{b['nome']} {b['versao']} ({idade}{marca})")
    return " · ".join(partes)


if __name__ == "__main__":
    print("Bibliotecas que baixam vídeo")
    print("=" * 70)
    for b in estado():
        marca = "!" if (b["envelheceu"] or not b["presente"]) else " "
        versao = b["versao"] or "NÃO INSTALADO"
        idade = f"{b['dias']} dia(s)" if b["dias"] is not None else "sem data na versão"
        print(f" [{marca}] {b['nome']:<14} {versao:<14} {idade}")
        print(f"     {b['papel']}")
    print()
    atencao = precisa_de_atencao()
    if atencao:
        print(f"{len(atencao)} precisa(m) de atenção.")
        print()
        print(instrucoes([b["nome"] for b in atencao]))
    else:
        print("Tudo em dia.")
    sys.exit(0)
