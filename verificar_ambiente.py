# -*- coding: utf-8 -*-
"""
Confere se esta máquina tem tudo o que o programa precisa para rodar.

PARA QUE SERVE

Rodar ANTES de usar o programa numa máquina nova, principalmente no servidor.
Ele responde, em poucos segundos, a pergunta que normalmente só aparece no
meio de um lote: falta alguma coisa aqui?

Confere cinco camadas, e todas elas já quebraram em algum momento:

  1. Pacotes Python, comparando com o que está travado em requirements.txt
  2. Programas externos: ffmpeg, ffprobe e tesseract, que não vêm pelo pip e
     cujos caminhos estão fixos em pastas do Windows
  3. Serviços: o Ollama respondendo, e o modelo de visão baixado
  4. Configuração: os cinco identificadores, a conta do Instagram, os tokens,
     o registro de contratos, o cache de perfis, a cópia da Monitoramento em
     Excel e as cinco chaves do login
  5. Manutenção: se as bibliotecas que baixam vídeo envelheceram, e o espaço
     livre em disco

A CAMADA 4 CRESCEU EM 07/09/2026 e o motivo vale registrar: tudo o que entrou
ali falha em SILÊNCIO. A cópia da Monitoramento faltando não dá erro, joga todo
vídeo em "Ciclo A CONFIRMAR". Uma chave a menos no login não dá erro, abre o
programa sem pedir login. O identificador dos fechamentos faltando não dá erro,
grava a conclusão só nesta máquina. Enquanto isso não era conferido aqui, o
manual de instalação tinha de pedir que a pessoa olhasse arquivo por arquivo.

Não altera nada. Só olha e relata.

    py verificar_ambiente.py
"""
import os
import re
import subprocess
import sys
from importlib import metadata

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

OK, AVISO, FALTA = "ok", "aviso", "falta"
_SIMBOLO = {OK: "  ok  ", AVISO: " aviso", FALTA: " FALTA"}

# IDADE ACEITÁVEL DA CÓPIA DA MONITORAMENTO, EM DIAS.
#
# O número não é escolhido no olho. Foi medido em 07/09/2026 na própria cópia:
# o intervalo entre dois ciclos consecutivos do MESMO influenciador tem mediana
# de 32 dias, em 854 pares de ciclos. O quarto mais rápido vira em 27 dias.
#
# É esse o relógio que importa, e não a idade do arquivo por si: o estrago
# aparece quando um ciclo NOVO começa e a cópia não sabe dele. Com 30 dias, o
# aviso chega perto da virada típica, aceitando que uma parte dos casos mais
# rápidos já terá virado antes. Baixar muito este número transformaria a
# conferência em aviso permanente, que é o que ninguém lê.
DIAS_ATE_A_COPIA_ENVELHECER = 30

resultados = []


def anotar(situacao, item, detalhe=""):
    resultados.append((situacao, item, detalhe))
    print(f"[{_SIMBOLO[situacao]}] {item:<34} {detalhe}")


def esperados_do_requirements():
    """Lê os pacotes travados, ignorando comentário e linha vazia."""
    caminho = os.path.join(BASE, "requirements.txt")
    if not os.path.exists(caminho):
        return {}
    pacotes = {}
    for linha in open(caminho, encoding="utf-8"):
        linha = linha.split("#")[0].strip()
        if not linha:
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*==\s*(.+)$", linha)
        if m:
            pacotes[m.group(1)] = m.group(2).strip()
    return pacotes


def conferir_pacotes():
    print("\n--- pacotes Python ---")
    esperados = esperados_do_requirements()
    if not esperados:
        anotar(FALTA, "requirements.txt", "não achei o arquivo")
        return
    for nome, versao in sorted(esperados.items(), key=lambda x: x[0].lower()):
        try:
            instalada = metadata.version(nome)
        except metadata.PackageNotFoundError:
            anotar(FALTA, nome, f"não instalado (esperado {versao})")
            continue
        if instalada == versao:
            anotar(OK, nome, instalada)
        else:
            anotar(AVISO, nome, f"instalado {instalada}, travado {versao}")

    conferir_opencv()


def conferir_opencv():
    """Os dois pacotes do OpenCV, e por que a conferência é de VERSÃO IGUAL.

    CORRIGIDO EM 07/09/2026. Antes daqui, este verificador avisava sempre que
    encontrasse os dois pacotes instalados, tratando isso como conflito. O aviso
    estava errado por dois motivos, e aparecia em toda execução.

    PRIMEIRO, ter os dois não é descuido e não tem como ser diferente: o
    rapidocr-onnxruntime declara opencv-python como dependência dele e o easyocr
    declara opencv-python-headless. São dois dos três motores de leitura de
    texto, os dois são obrigatórios, e instalar o requirements.txt sempre traz os
    dois de volta. Pedir "instale só o headless" é pedir o impossível.

    SEGUNDO, o problema real não é a presença, é a DIVERGÊNCIA DE VERSÃO. Os dois
    pacotes gravam na mesma pasta cv2, conferido nesta máquina: 59 arquivos de um
    e 60 do outro, com o mesmo destino. Quem instala por último sobrescreve o
    outro. Com a mesma versão isso é inofensivo, os arquivos são equivalentes.
    Com versões diferentes fica um cv2 montado com metade de cada, e o sintoma é
    erro ao carregar a biblioteca, não uma mensagem dizendo que há conflito.

    O programa usa só cv2.imread e cv2.Laplacian, em
    validar_avisos_portaria136.py, que são cálculo puro. A parte de janela e tela
    que o headless não traz nunca é chamada, então qual dos dois vence não muda
    resultado nenhum, desde que a versão seja a mesma."""
    try:
        completo = metadata.version("opencv-python")
        headless = metadata.version("opencv-python-headless")
    except metadata.PackageNotFoundError:
        # Só um dos dois instalado é situação válida: o cv2 que sobra atende os
        # dois motores igualmente.
        return
    if completo == headless:
        anotar(OK, "opencv (os dois pacotes)",
               f"{completo} nos dois, que é o esperado: rapidocr pede "
               f"opencv-python e easyocr pede o headless")
    else:
        anotar(AVISO, "opencv (os dois pacotes)",
               f"versões DIFERENTES, opencv-python {completo} e headless "
               f"{headless}. Os dois gravam na mesma pasta cv2 e o último a "
               f"instalar sobrescreve o outro. Iguale com: py -m pip install "
               f"opencv-python=={headless} opencv-python-headless=={headless}")


def conferir_programas():
    print("\n--- programas externos ---")
    try:
        import validar_avisos_portaria136 as motor
    except Exception as e:
        anotar(FALTA, "motor de análise", f"não consegui importar: {str(e)[:80]}")
        return

    for rotulo, comando in (("ffmpeg", motor.FFMPEG_CMD), ("ffprobe", motor.FFPROBE_CMD)):
        try:
            r = subprocess.run([comando, "-version"], capture_output=True, text=True, timeout=20)
            primeira = (r.stdout or r.stderr).splitlines()[0][:60]
            anotar(OK, rotulo, primeira)
        except Exception:
            anotar(FALTA, rotulo, f"não executou: {comando}")

    try:
        import pytesseract
        versao = str(pytesseract.get_tesseract_version())
        # O CAMINHO RESOLVIDO APARECE JUNTO DA VERSÃO. São sete lugares de
        # busca, e o instalador recomendado usa o terceiro. Sem ver o caminho,
        # quem tem duas instalações não descobre qual pegou.
        anotar(OK, "tesseract", f"{versao}  ({motor.PYTESSERACT_CMD})")
        # O código pede lang="por+eng". Se o português não estiver instalado,
        # o Tesseract NÃO dá erro: ele cai para o inglês em silêncio, e ninguém
        # percebe. Foi o que aconteceu aqui, descoberto em 30/08/2026 na
        # primeira execução deste verificador. Por isso é aviso e não falta: o
        # programa funciona, só lê texto em português com o modelo errado.
        idiomas = pytesseract.get_languages()
        if "eng" not in idiomas:
            anotar(FALTA, "idioma inglês do tesseract",
                   "sem ele o primeiro degrau da leitura não funciona")
        if "por" not in idiomas:
            anotar(AVISO, "idioma português do tesseract",
                   "não instalado; o programa pede por+eng e cai para inglês sem avisar")
        else:
            anotar(OK, "idiomas do tesseract", "português e inglês")
    except Exception as e:
        anotar(FALTA, "tesseract", str(e)[:70])

    # O caminho fixo de Windows é impedimento conhecido para servidor Linux.
    if os.name != "nt" and "\\" in str(getattr(motor, "FFMPEG_CMD", "")):
        anotar(FALTA, "caminhos de Windows",
               "o programa está com caminho de Windows num sistema que não é Windows")


def conferir_servicos():
    print("\n--- serviços ---")
    try:
        import json
        import urllib.request
        import validar_avisos_portaria136 as motor
        endereco = motor.OLLAMA_URL.replace("/api/generate", "/api/tags")
        with urllib.request.urlopen(endereco, timeout=8) as r:
            modelos = [m["name"] for m in json.loads(r.read()).get("models", [])]
        anotar(OK, "ollama", f"{len(modelos)} modelo(s) disponível(is)")
        procurado = motor.OLLAMA_VISION_MODEL
        if any(m.split(":")[0] == procurado.split(":")[0] for m in modelos):
            anotar(OK, f"modelo {procurado}", "baixado")
        else:
            anotar(FALTA, f"modelo {procurado}", f"rode: ollama pull {procurado}")
    except Exception as e:
        anotar(FALTA, "ollama", f"não respondeu: {str(e)[:70]}")


def conferir_configuracao():
    print("\n--- configuração ---")
    try:
        import fluxo_downloads as fluxo
    except Exception as e:
        anotar(FALTA, "fluxo de download", str(e)[:70])
        return

    # OS QUATRO IDENTIFICADORES, e não dois (02/09/2026). Faltavam a raiz do
    # Drive e o cadastro, e faltar um deles faz a tela abrir e falhar depois,
    # sem dizer por quê. Encontrado ao preparar a instalação numa máquina nova.
    for rotulo, caminho in (
        ("identificador da Monitoramento", fluxo.ARQUIVO_MONITORAMENTO_ID),
        ("identificador da fila", fluxo.ARQUIVO_FILA_ID),
        ("identificador da pasta do Drive", fluxo.ARQUIVO_DRIVE_RAIZ_ID),
        ("identificador do cadastro", fluxo.ARQUIVO_CADASTRO_ID),
        ("cookies do Instagram", fluxo.ARQUIVO_COOKIES),
    ):
        if os.path.exists(caminho):
            anotar(OK, rotulo, "presente")
        else:
            anotar(AVISO, rotulo, f"não existe: {os.path.basename(caminho)}")

    # LAYOUT DE PASTAS DO DRIVE (12/09/2026): três hoje, teste/marketing/futebol.
    # Aparece sempre, pelo mesmo motivo da conta do Instagram logo abaixo: é
    # fácil uma máquina ficar no layout errado sem ninguém perceber até o
    # primeiro download falhar.
    #
    # A CONFERÊNCIA DO MAPA @ -> PASTA SAIU EM 21/09/2026: o layout futebol
    # foi redesenhado para seguir o mesmo caminho do Marketing (pasta achada
    # pelo @, com bet e sem ano), e o mapa (`pasta_por_handle_futebol.json`)
    # ficou sem uso. Ele não foi apagado do disco nem do código por cautela,
    # mas não faz mais sentido avisar sobre a falta dele aqui.
    anotar(OK, "layout de pastas do Drive", fluxo.LAYOUT_PASTAS)

    # MODO DE ESCRITA: TESTE OU REAL (08/09/2026), e aparece sempre, pelo
    # mesmo motivo da conta do Instagram logo abaixo: é o item mais caro de
    # não notar. Ligar sem querer escreveria de verdade na Monitoramento e
    # no Drive do Marketing; não perceber que já ligou faria alguém achar
    # que está testando quando não está. Ver
    # fluxo_downloads.modo_real_autorizado.
    if fluxo.modo_real_autorizado():
        anotar(OK, "modo de escrita",
               "REAL — grava na Monitoramento e no Drive do Marketing")
    else:
        anotar(OK, "modo de escrita",
               "teste — grava só na cópia, como de costume")

    # A CONTA DO INSTAGRAM APARECE SEMPRE, mesmo quando está tudo certo
    # (02/09/2026). É o item mais perigoso de instalar errado: com o nome de
    # outra pessoa, a sessão é tratada como ANÔNIMA sem avisar, os limites do
    # Instagram ficam muito mais duros, e a conta corre risco de bloqueio pelo
    # mesmo caminho de 25/08/2026. Nada quebra na tela, então quem instala tem
    # que VER o nome e confirmar que é o dele.
    de_arquivo = os.path.exists(fluxo.ARQUIVO_CONTA_INSTAGRAM)
    de_variavel = bool(os.environ.get("USUARIO_INSTAGRAM"))
    if de_arquivo:
        origem = os.path.basename(fluxo.ARQUIVO_CONTA_INSTAGRAM)
        anotar(OK, "conta do Instagram", f"@{fluxo.USUARIO_DOS_COOKIES} (de {origem})")
    elif de_variavel:
        anotar(OK, "conta do Instagram",
               f"@{fluxo.USUARIO_DOS_COOKIES} (da variável USUARIO_INSTAGRAM)")
    else:
        anotar(AVISO, "conta do Instagram",
               f"@{fluxo.USUARIO_DOS_COOKIES} — valor do código. "
               f"CONFIRME que é a sua conta: escreva o @ em "
               f"{os.path.basename(fluxo.ARQUIVO_CONTA_INSTAGRAM)}")

    credenciais = os.path.join(BASE, "_drive_credenciais")
    tokens = [f for f in os.listdir(credenciais) if f.endswith("token.json")] \
        if os.path.isdir(credenciais) else []
    if tokens:
        anotar(OK, "credenciais do Google", f"{len(tokens)} token(s)")
    else:
        anotar(FALTA, "credenciais do Google", "nenhum token; rode os autorizar_*.py")

    # O QUINTO IDENTIFICADOR (07/09/2026). Entrou em 05/09 com o registro de
    # fechamentos e ficou fora daqui, então a falta dele só aparecia quando
    # alguém fechava um ciclo e via o aviso de que o registro ficou só na
    # máquina. É aviso e não falta porque o programa não quebra sem ele.
    try:
        import registro_fechamentos
        caminho = os.path.join(fluxo.PASTA_TESTE,
                               registro_fechamentos.NOME_DO_ARQUIVO_ID)
        if os.path.exists(caminho):
            anotar(OK, "identificador dos fechamentos", "presente")
        else:
            anotar(AVISO, "identificador dos fechamentos",
                   f"não existe: {registro_fechamentos.NOME_DO_ARQUIVO_ID}. "
                   f"O fechamento de ciclo vai gravar só nesta máquina")
    except Exception as e:
        anotar(AVISO, "identificador dos fechamentos", str(e)[:70])

    # O CALENDÁRIO DE DIVULGAÇÕES (11/09/2026). Segunda planilha do Marketing,
    # onde o programa preenche Jogo, Status, Horário e Monitorado por. Mostra
    # QUAL das duas está valendo, e não só se o arquivo existe, pelo mesmo
    # motivo do modo de escrita acima: o caro aqui não é faltar, é a pessoa
    # achar que está escrevendo na cópia de teste quando está na real, ou o
    # contrário. Ver DESENHO_CALENDARIO.md.
    try:
        import calendario_divulgacoes as cal
        real = cal.ler_id_real()
        valendo = cal.planilha_id()
        if not valendo:
            anotar(AVISO, "Calendário de Divulgações",
                   f"sem identificador nenhum: crie "
                   f"{os.path.basename(cal.ARQUIVO_ID_TESTE)} em "
                   f"teste_watch_folder. O programa não vai preencher o "
                   f"Calendário")
        elif real and valendo == real:
            anotar(OK, "Calendário de Divulgações",
                   "REAL — preenche o Calendário do Marketing de verdade")
        else:
            anotar(OK, "Calendário de Divulgações",
                   "cópia de teste, como de costume")
    except Exception as e:
        anotar(AVISO, "Calendário de Divulgações", str(e)[:70])

    # O REGISTRO DE CONTRATOS DO NETLEX. Não é identificador nem credencial, e
    # por isso não estava em nenhuma lista. Sem ele a tela de Cadastro abre e o
    # número de contrato simplesmente não aparece, sem erro nenhum.
    try:
        import contratos_netlex
        if os.path.exists(contratos_netlex.ARQUIVO):
            quantos = len(contratos_netlex.ler())
            anotar(OK, "registro de contratos do Netlex", f"{quantos} registro(s)")
        else:
            anotar(AVISO, "registro de contratos do Netlex",
                   f"não existe: {os.path.basename(contratos_netlex.ARQUIVO)}. "
                   f"O Cadastro abre sem o número do contrato")
    except Exception as e:
        anotar(AVISO, "registro de contratos do Netlex", str(e)[:70])

    # O CACHE DE PERFIS APARECE COMO INFORMAÇÃO, NUNCA COMO FALTA. Ele é cache
    # de dado público (o número interno do perfil) e o programa funciona sem
    # ele. O motivo de mostrar é econômico: descobrir esse número passa pelo
    # endereço que o Instagram limita com mais rigor, o que ficou travado horas
    # em 25/08/2026. Numa máquina nova é normal aparecer 0.
    try:
        import json as _json
        if os.path.exists(fluxo.ARQUIVO_USERIDS):
            with open(fluxo.ARQUIVO_USERIDS, encoding="utf-8") as f:
                quantos = len(_json.load(f))
            anotar(OK, "cache de perfis do Instagram",
                   f"{quantos} perfil(is) conhecido(s)")
        else:
            anotar(OK, "cache de perfis do Instagram",
                   "vazio; o programa aprende perfil por perfil, gastando a "
                   "chamada mais limitada do Instagram")
    except Exception as e:
        anotar(AVISO, "cache de perfis do Instagram", str(e)[:70])

    # A CÓPIA DA MONITORAMENTO EM EXCEL, que mora FORA da pasta do programa e
    # por isso não vem na cópia. Sem ela nada quebra e TODO vídeo cai em "Ciclo
    # A CONFIRMAR", o que só se descobre depois, no Drive e na planilha. É a
    # falta mais cara de perceber tarde.
    try:
        caminho = fluxo._achar_monitoramento()
        if caminho and os.path.exists(caminho):
            anotar(OK, "cópia da Monitoramento em Excel",
                   os.path.basename(caminho))
            conferir_idade_da_monitoramento(caminho)
        else:
            anotar(FALTA, "cópia da Monitoramento em Excel",
                   "não achei; sem ela todo vídeo cai em 'Ciclo A CONFIRMAR'. "
                   "Aponte com ARQUIVO_MONITORAMENTO ou PASTA_CONTEXTO")
    except Exception as e:
        anotar(FALTA, "cópia da Monitoramento em Excel", str(e)[:70])

    conferir_login()


def conferir_idade_da_monitoramento(caminho):
    """Há quanto tempo a cópia da Monitoramento foi tirada.

    POR QUE A PRESENÇA NÃO BASTA (07/09/2026)

    Até aqui a conferência só perguntava se o arquivo existe. Existir e estar
    velho são coisas diferentes, e o segundo caso erra de um jeito pior.

    Sem a cópia, todo vídeo cai em "Ciclo A CONFIRMAR". É ruim, mas aparece: o
    rótulo está na cara de quem olha, e alguém corrige.

    Com a cópia VELHA existem duas falhas, e a segunda é a que preocupa:

      1. Influenciador que entrou depois da cópia não está nela, e cai em
         "Ciclo A CONFIRMAR". Visível, igual ao caso acima.

      2. Influenciador que a cópia CONHECE, com vídeo de data posterior ao
         último ciclo dela, recebe o rótulo do CICLO ANTIGO. Está em
         fluxo_downloads.inferir_ciclo: quando a data passa do fim do último
         ciclo conhecido, o programa devolve esse último ciclo em vez de
         "A CONFIRMAR". O vídeo do ciclo novo é arquivado e registrado com o
         número do ciclo anterior, sem nada na tela sugerindo problema, e o
         erro vai para a coluna CICLO da planilha.

    O segundo caso é exatamente o tipo de falha que esta camada existe para
    pegar: não quebra, não avisa, e só aparece muito depois, na conferência de
    escopo contra entrega, onde o ciclo é a chave da cota.

    A data sai do nome do arquivo quando ele traz uma ("..._2026-08-19.xlsx",
    que é como o Marketing entrega), e da data de gravação quando não traz."""
    import datetime

    nome = os.path.basename(caminho)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", nome)
    if m:
        try:
            data = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            origem = "pela data no nome"
        except ValueError:
            data, origem = None, ""
    else:
        data, origem = None, ""
    if data is None:
        data = datetime.date.fromtimestamp(os.path.getmtime(caminho))
        origem = "pela data de gravação, o nome não traz data"

    dias = (datetime.date.today() - data).days
    quando = f"de {data.strftime('%d/%m/%Y')}, há {dias} dia(s) ({origem})"
    if dias < DIAS_ATE_A_COPIA_ENVELHECER:
        anotar(OK, "idade da cópia da Monitoramento", quando)
    else:
        anotar(AVISO, "idade da cópia da Monitoramento",
               f"{quando}. O ciclo do mesmo influenciador vira a cada 32 dias na "
               f"mediana, então provavelmente já existe ciclo que esta cópia não "
               f"conhece, e o vídeo dele vai receber o número do ciclo ANTIGO em "
               f"silêncio. Peça uma cópia nova da Monitoramento ao Marketing e "
               f"deixe em {os.path.dirname(caminho)}")


def conferir_login():
    """As cinco chaves do secrets.toml, SEM imprimir valor nenhum.

    POR QUE ESTA CONFERÊNCIA EXISTE (07/09/2026)

    A falha aqui é silenciosa e ao contrário do esperado: faltando qualquer uma
    das cinco chaves, `acesso.login_configurado()` devolve falso e o programa
    ABRE SEM PEDIR LOGIN. Quem montou o arquivo pensa que ligou o login, e não
    ligou. Nada na tela contradiz essa impressão.

    Lê o arquivo direto com tomllib em vez de st.secrets, porque st.secrets
    depende do Streamlit estar rodando e aqui não está."""
    caminho = os.path.join(BASE, ".streamlit", "secrets.toml")
    if not os.path.exists(caminho):
        anotar(AVISO, "login do programa",
               "sem .streamlit/secrets.toml: o programa abre SEM pedir login")
        return
    try:
        import tomllib
        import acesso
        with open(caminho, "rb") as f:
            dados = tomllib.load(f)
        auth = dados.get("auth") or {}
        # Só o NOME da chave é impresso, nunca o valor: este arquivo equivale a
        # senha, e a saída deste comando é feita para ser colada num chat.
        faltando = [c for c in acesso.CHAVES_DO_LOGIN if not auth.get(c)]
        if faltando:
            anotar(AVISO, "login do programa",
                   f"faltam {len(faltando)} de {len(acesso.CHAVES_DO_LOGIN)} "
                   f"chaves em [auth] ({', '.join(faltando)}): o programa abre "
                   f"SEM pedir login")
        else:
            anotar(OK, "login do programa",
                   f"as {len(acesso.CHAVES_DO_LOGIN)} chaves de [auth] estão lá")
    except Exception as e:
        anotar(AVISO, "login do programa", f"não consegui ler: {str(e)[:60]}")


def conferir_manutencao():
    """Idade das bibliotecas de download e espaço em disco.

    POR QUE ENTRA NA CONFERÊNCIA DE AMBIENTE (07/09/2026)

    O verificador dizia se o pacote está instalado conforme o travado no
    requirements.txt, e não se a versão ENVELHECEU. São perguntas diferentes, e
    numa instalação nova a resposta divergia: o yt-dlp travado sai conforme e ao
    mesmo tempo velho, porque a versão travada é de 04/07/2026. Quem instalava
    lia "nada faltando" e só descobria o aviso ao abrir a tela de Downloads."""
    print("\n--- manutenção ---")
    try:
        import baixadores
        for b in baixadores.estado():
            nome = b.get("nome", "?")
            if not b.get("presente"):
                anotar(FALTA, nome,
                       "não instalado; rode py -m pip install -r requirements.txt")
            elif b.get("envelheceu"):
                # A IDADE VEM DE DOIS RELÓGIOS. Só o yt-dlp versiona por data,
                # então só ele tem idade calculável pela própria versão. Para os
                # outros o relógio é o tempo desde que aquela versão apareceu
                # nesta máquina. Dizer qual dos dois falou evita a leitura
                # errada de que as outras estão novas.
                idade = (f"lançada há {b['dias']} dias" if b.get("dias")
                         else f"sem atualizar há {b.get('dias_parada')} dias")
                anotar(AVISO, nome,
                       f"{b.get('versao')}, {idade}, e o programa considera "
                       f"velha depois de {baixadores.DIAS_ATE_ENVELHECER}. "
                       f"Ver a seção de manutenção do INSTALAR.md")
            else:
                anotar(OK, nome, str(b.get("versao")))
    except Exception as e:
        anotar(AVISO, "bibliotecas de download", str(e)[:70])

    # ESPAÇO EM DISCO. O mínimo de 60 GB está medido no preparar_servidor.ps1,
    # que é o roteiro de servidor e não roda em máquina comum. O modelo de visão
    # sozinho tem 5,5 GB, e os vídeos passam por aqui antes de ir para o Drive.
    try:
        import shutil
        livre = shutil.disk_usage(BASE).free / (1024 ** 3)
        if livre < 10:
            anotar(FALTA, "espaço em disco",
                   f"{livre:.1f} GB livres; o modelo de visão sozinho tem 5,5 GB")
        elif livre < 60:
            anotar(AVISO, "espaço em disco",
                   f"{livre:.1f} GB livres; o roteiro de servidor pede 60 GB")
        else:
            anotar(OK, "espaço em disco", f"{livre:.1f} GB livres")
    except Exception as e:
        anotar(AVISO, "espaço em disco", str(e)[:70])


if __name__ == "__main__":
    print("=" * 74)
    print("  Conferência de ambiente  |  Monitoramento de Influenciadores")
    print(f"  Python {sys.version.split()[0]} em {os.name}")
    print("=" * 74)

    conferir_pacotes()
    conferir_programas()
    conferir_servicos()
    conferir_configuracao()
    conferir_manutencao()

    faltas = [r for r in resultados if r[0] == FALTA]
    avisos = [r for r in resultados if r[0] == AVISO]

    print()
    print("=" * 74)
    if faltas:
        print(f"  {len(faltas)} item(ns) FALTANDO. O programa não vai rodar direito assim:")
        for _, item, detalhe in faltas:
            print(f"    - {item}: {detalhe}")
    else:
        print("  Nada faltando.")
    if avisos:
        print(f"  {len(avisos)} aviso(s), que não impedem mas merecem olhada:")
        for _, item, detalhe in avisos:
            print(f"    - {item}: {detalhe}")
    print("=" * 74)
    sys.exit(1 if faltas else 0)
