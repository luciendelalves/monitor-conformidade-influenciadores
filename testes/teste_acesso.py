# -*- coding: utf-8 -*-
"""
Prova que a combinação perigosa não passa: tela na rede sem login.

POR QUE ESTE TESTE EXISTE (30/08/2026)

O que está atrás da tela são as credenciais do Google que ficam no servidor, de
escopo amplo, e a conta do Instagram. Quem abre a tela usa as duas sem provar
quem é. Enquanto o programa escuta só em 127.0.0.1, tudo bem: quem alcança já
está na máquina. O par que importa é este:

    127.0.0.1  +  sem login   ->  aceitável, é o de hoje
    na rede    +  sem login   ->  NAO, entrega as credenciais para a rede
    na rede    +  com login   ->  é o que se quer no servidor

O risco real não é alguém decidir subir sem login. É trocar UMA linha do
config.toml para as cinco pessoas alcançarem a tela, e esquecer a outra metade.
São dois arquivos diferentes, mexidos em momentos diferentes, provavelmente por
pessoas diferentes.

Por isso o programa TRAVA nesse caso, em vez de avisar. É o único lugar do
programa onde travar é melhor que avisar.

    py testes\teste_acesso.py
"""
import os
import re
import sys
from unittest import mock

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import acesso

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


class Parou(Exception):
    """st.stop() de mentira, para saber que a página foi interrompida."""


def montar_streamlit(endereco, segredos, logado, email="alguem@empresa.com"):
    """Um Streamlit de mentira, com só o que acesso.py usa."""
    falso = mock.MagicMock()
    falso.get_option.side_effect = lambda chave: (
        endereco if chave == "server.address" else None)

    if segredos is None:
        # Sem secrets.toml, tocar em st.secrets levanta erro de verdade.
        tipo = type("SemSegredos", (), {
            "get": lambda self, *a, **k: (_ for _ in ()).throw(
                FileNotFoundError("no secrets"))})
        falso.secrets = tipo()
    else:
        falso.secrets = {"auth": segredos} if segredos else {}
        falso.secrets = mock.MagicMock()
        falso.secrets.get.side_effect = lambda c, *a: (
            segredos if c == "auth" else None)

    falso.user = mock.MagicMock()
    falso.user.is_logged_in = logado
    falso.user.email = email
    falso.stop.side_effect = Parou
    return falso


AUTH_COMPLETO = {
    "client_id": "x", "client_secret": "y",
    "server_metadata_url": "https://exemplo/.well-known/openid-configuration",
    "redirect_uri": "https://servidor/oauth2callback",
    "cookie_secret": "z",
}
AUTH_PELA_METADE = {"client_id": "x", "client_secret": "y"}


def tentar_entrar(**kw):
    """Roda exigir_login com o Streamlit de mentira. Devolve (travou, textos)."""
    falso = montar_streamlit(**kw)
    textos = []
    falso.error.side_effect = lambda t, *a, **k: textos.append(str(t))
    falso.title.side_effect = lambda t, *a, **k: textos.append(str(t))
    falso.write.side_effect = lambda t, *a, **k: textos.append(str(t))
    falso.button.side_effect = lambda t, *a, **k: textos.append(str(t))
    with mock.patch.object(acesso, "st", falso):
        try:
            acesso.exigir_login()
            return False, textos
        except Parou:
            return True, textos


def rodar():
    print("--- 1. a combinação perigosa: na rede e sem login ---")
    for endereco in ("0.0.0.0", "192.168.0.16", None, ""):
        travou, textos = tentar_entrar(endereco=endereco, segredos=None, logado=False)
        junto = " ".join(textos).lower()
        conferir(travou, f"endereço {endereco!r}: TRAVA a tela", "deixou passar")
        conferir("login" in junto and "credenciais" in junto,
                 f"endereço {endereco!r}: explica o risco, não só 'erro'", junto[:70])
        conferir("127.0.0.1" in " ".join(textos),
                 f"endereço {endereco!r}: diz as duas saídas possíveis")

    print()
    print("--- 2. máquina de trabalho: segue como hoje ---")
    for endereco in ("127.0.0.1", "localhost", "::1"):
        travou, _ = tentar_entrar(endereco=endereco, segredos=None, logado=False)
        conferir(not travou,
                 f"endereço {endereco!r}: deixa passar, sem atrapalhar o teste",
                 "travou")

    print()
    print("--- 3. com login configurado, exige entrar ---")
    travou, textos = tentar_entrar(endereco="0.0.0.0", segredos=AUTH_COMPLETO,
                                   logado=False)
    conferir(travou, "na rede, sem estar logado: para e pede para entrar")
    conferir(any("Entrar" in t for t in textos),
             "e oferece o botão de entrar", str(textos)[:80])

    travou, _ = tentar_entrar(endereco="0.0.0.0", segredos=AUTH_COMPLETO, logado=True)
    conferir(not travou, "logado: passa")

    print()
    print("--- 4. configuração pela metade não conta como configurada ---")
    # O caso ruim seria dar por configurado e falhar no meio do login, com
    # mensagem que não ajuda ninguém.
    travou, textos = tentar_entrar(endereco="0.0.0.0", segredos=AUTH_PELA_METADE,
                                   logado=False)
    junto = " ".join(textos).lower()
    conferir(travou, "com auth incompleto, ainda trava")
    conferir("credenciais" in junto,
             "e trava pela mensagem de falta de login, que é a verdadeira",
             junto[:70])

    print()
    print("--- 5. quem entrou, mas não está liberado ---")
    original = acesso.LISTA_DE_PERMISSAO
    try:
        acesso.LISTA_DE_PERMISSAO = ["autorizado@empresa.com"]
        travou, textos = tentar_entrar(endereco="0.0.0.0", segredos=AUTH_COMPLETO,
                                       logado=True, email="outro@empresa.com")
        conferir(travou, "conta fora da lista é barrada mesmo autenticada")
        conferir(any("outro@empresa.com" in t for t in textos),
                 "e a mensagem diz qual conta foi barrada", str(textos)[:90])

        travou, _ = tentar_entrar(endereco="0.0.0.0", segredos=AUTH_COMPLETO,
                                  logado=True, email="AUTORIZADO@empresa.com")
        conferir(not travou, "e a comparação não depende de maiúscula")
    finally:
        acesso.LISTA_DE_PERMISSAO = original

    print()
    print("--- 5b. lista de e-mails vazia: vale o DOMÍNIO ---")
    # ESTA SEÇÃO CORRIGE UMA AFIRMAÇÃO ANTERIOR DESTE PRÓPRIO TESTE.
    # Até 31/08/2026 aqui se afirmava que "com a lista vazia, qualquer pessoa
    # autenticada entra", e isso era verdade e era aceitável, porque o provedor
    # previsto era o Entra ID da empresa, que já não deixa entrar quem é de
    # fora. Com a possibilidade de entrar pela conta Google, o provedor passa a
    # ser global, e o mesmo padrão aceitaria qualquer conta do mundo numa
    # ferramenta que guarda credencial de escopo amplo.
    lista_original = acesso.LISTA_DE_PERMISSAO
    dominios_originais = acesso.DOMINIOS_AUTORIZADOS
    try:
        acesso.LISTA_DE_PERMISSAO = []
        acesso.DOMINIOS_AUTORIZADOS = ["grupoegb.com"]
        conferir(acesso.pode_entrar("qualquer@empresa.com"),
                 "conta do domínio da empresa entra")
        conferir(acesso.pode_entrar("QUALQUER@GrupoEGB.COM"),
                 "e não depende de maiúscula")
        conferir(not acesso.pode_entrar("estranho@gmail.com"),
                 "conta Google pessoal NÃO entra",
                 "este é o ponto: accounts.google.com aceita o mundo inteiro")
        conferir(not acesso.pode_entrar("alguem@empresa.com.br"),
                 "domínio parecido não entra",
                 "comparação é do domínio inteiro, não do começo dele")
        conferir(not acesso.pode_entrar("grupoegb.com"),
                 "texto sem @ não entra")
        conferir(not acesso.pode_entrar("a@b@empresa.com"),
                 "texto com dois @ não entra")
        conferir(not acesso.pode_entrar(""), "vazio não entra")
        conferir(not acesso.pode_entrar(None), "nada não entra")

        # A lista de e-mails é mais específica, e por isso manda: estar no
        # domínio não basta se existe lista e a conta está fora dela.
        acesso.LISTA_DE_PERMISSAO = ["so.eu@empresa.com"]
        conferir(not acesso.pode_entrar("outro@empresa.com"),
                 "com lista de e-mails, o domínio NÃO libera quem está fora dela")

        # Falha fechada: sem lista e sem domínio, ninguém entra.
        acesso.LISTA_DE_PERMISSAO = []
        acesso.DOMINIOS_AUTORIZADOS = []
        conferir(not acesso.pode_entrar("alguem@empresa.com"),
                 "sem lista e sem domínio, ninguém entra",
                 "porta de entrada falha fechada de propósito")

        # E a mensagem precisa dizer que o problema é do servidor, não da conta.
        travou, textos = tentar_entrar(endereco="0.0.0.0", segredos=AUTH_COMPLETO,
                                       logado=True, email="alguem@empresa.com")
        junto = " ".join(textos).lower()
        conferir(travou, "e a tela para nesse caso")
        conferir("servidor" in junto and "dominios_autorizados" in junto,
                 "dizendo que falta configuração do servidor, não culpando a conta",
                 junto[:90])
    finally:
        acesso.LISTA_DE_PERMISSAO = lista_original
        acesso.DOMINIOS_AUTORIZADOS = dominios_originais

    conferir(acesso.DOMINIOS_AUTORIZADOS == ["grupoegb.com"],
             "e o padrão de fábrica é o domínio da empresa, não vazio",
             str(acesso.DOMINIOS_AUTORIZADOS))

    print()
    print("--- 5c. a barreira aparece como PÁGINA, e cada página se protege ---")
    # ACHADO NO PRIMEIRO USO REAL DO LOGIN, em 31/08/2026, e revisão de código
    # não pegou. O exigir_login interrompia a página com st.stop() antes de o
    # painel.py chamar st.navigation. Sem receber a lista de abas, o Streamlit
    # caía no menu automático da pasta pages/, e daí:
    #
    #   1. a aba "Validação Regulatória" desaparecia, porque o arquivo dela
    #      está na raiz e só existe pela navegação declarada. Foi esse o
    #      sintoma que o auditor viu
    #   2. as páginas de pages/ continuavam alcançáveis por rota própria, sem
    #      passar pela porta, inclusive no caso em que o programa deveria estar
    #      travado. A trava protegia a porta e deixava as janelas abertas
    lista_original = acesso.LISTA_DE_PERMISSAO
    try:
        falso = montar_streamlit(endereco="127.0.0.1", segredos=None, logado=False)
        with mock.patch.object(acesso, "st", falso):
            conferir(acesso.situacao() == acesso.LIBERADO,
                     "máquina de trabalho sem login: liberado", acesso.situacao())

        falso = montar_streamlit(endereco="0.0.0.0", segredos=None, logado=False)
        with mock.patch.object(acesso, "st", falso):
            conferir(acesso.situacao() == acesso.BLOQUEADO,
                     "na rede sem login: bloqueado", acesso.situacao())

        falso = montar_streamlit(endereco="0.0.0.0", segredos=AUTH_COMPLETO, logado=False)
        with mock.patch.object(acesso, "st", falso):
            conferir(acesso.situacao() == acesso.PRECISA_ENTRAR,
                     "login configurado e ninguém entrou: precisa entrar",
                     acesso.situacao())

        falso = montar_streamlit(endereco="0.0.0.0", segredos=AUTH_COMPLETO,
                                 logado=True, email="alguem@empresa.com")
        with mock.patch.object(acesso, "st", falso):
            conferir(acesso.situacao() == acesso.LIBERADO,
                     "entrou com conta do domínio: liberado", acesso.situacao())

        falso = montar_streamlit(endereco="0.0.0.0", segredos=AUTH_COMPLETO,
                                 logado=True, email="estranho@gmail.com")
        with mock.patch.object(acesso, "st", falso):
            conferir(acesso.situacao() == acesso.BLOQUEADO,
                     "entrou com conta de fora: bloqueado", acesso.situacao())
    finally:
        acesso.LISTA_DE_PERMISSAO = lista_original

    # O painel precisa decidir a navegação pela situação, e não interromper
    # antes dela. Se voltar a chamar exigir_login antes do st.navigation, o
    # menu automático volta e o furo volta com ele.
    with open(os.path.join(BASE, "painel.py"), encoding="utf-8") as f:
        fonte_painel = f.read()
    conferir("acesso.situacao()" in fonte_painel,
             "o painel decide pela situação, sem interromper antes da navegação")
    conferir("pagina_de_barreira" in fonte_painel,
             "e a barreira entra como página da navegação")
    pos_navegacao = fonte_painel.find("st.navigation")
    pos_exigir = fonte_painel.find("acesso.exigir_login()")
    conferir(pos_exigir == -1 or pos_exigir > pos_navegacao,
             "o painel NÃO chama exigir_login antes de declarar a navegação",
             "era exatamente isso que fazia o menu automático aparecer")

    # E cada página se protege sozinha, porque no menu automático ela roda sem
    # passar pelo painel.
    paginas = [
        os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py"),
        os.path.join(BASE, "pages", "2_Monitoramento.py"),
    ]
    for caminho in paginas:
        with open(caminho, encoding="utf-8") as f:
            fonte = f.read()
        nome = os.path.basename(caminho)
        conferir("acesso.exigir_login()" in fonte,
                 f"{nome} exige login por conta própria",
                 "é rota própria do Streamlit, alcançável sem o painel")

    print()
    print("--- 5d. papel de coordenação, para o envio manual de arquivo ---")
    # PEDIDO DO AUDITOR EM 01/09/2026, por controle interno. A seção de envio
    # manual é o único caminho em que a pessoa escolhe tudo (o @, a data, o ciclo
    # e a tela), então é onde a discricionariedade é máxima. Nas outras seções o
    # programa descobre esses campos do próprio material.
    #
    # A autorização é por identidade, e não por senha da seção: senha
    # compartilhada faria o registro dizer "alguém que sabia a senha", e é o
    # registro que dá sentido ao controle.
    papeis_originais = dict(acesso.EMAILS_POR_PAPEL)
    sem_login_original = acesso.LIBERAR_PAPEL_SEM_LOGIN
    try:
        acesso.EMAILS_POR_PAPEL[acesso.PAPEL_COORDENACAO] = ["chefe@empresa.com"]
        acesso.LIBERAR_PAPEL_SEM_LOGIN = False

        # Com login e o papel: passa.
        falso = montar_streamlit(endereco="0.0.0.0", segredos=AUTH_COMPLETO,
                                 logado=True, email="chefe@empresa.com")
        with mock.patch.object(acesso, "st", falso):
            pode, motivo, sem_prova = acesso.autorizacao_para(acesso.PAPEL_COORDENACAO)
        conferir(pode, "quem tem o papel de coordenação pode enviar")
        conferir(not sem_prova, "e a identidade dela está provada pelo login")

        # Com login e SEM o papel: barra, e explica que é controle e não desconfiança.
        falso = montar_streamlit(endereco="0.0.0.0", segredos=AUTH_COMPLETO,
                                 logado=True, email="analista@empresa.com")
        with mock.patch.object(acesso, "st", falso):
            pode, motivo, _ = acesso.autorizacao_para(acesso.PAPEL_COORDENACAO)
        conferir(not pode, "quem NÃO tem o papel é barrado, mesmo autenticado")
        conferir("analista@empresa.com" in motivo,
                 "e a mensagem diz com qual conta a pessoa entrou", motivo[:90])
        conferir("controle interno" in motivo,
                 "dizendo que é controle interno, não desconfiança", motivo[:120])

        # SEM login e sem a chave: barra, falha fechada.
        falso = montar_streamlit(endereco="127.0.0.1", segredos=None, logado=False)
        with mock.patch.object(acesso, "st", falso):
            pode, motivo, _ = acesso.autorizacao_para(acesso.PAPEL_COORDENACAO)
        conferir(not pode, "sem login, ninguém envia arquivo à mão")
        conferir("LIBERAR_PAPEL_SEM_LOGIN" in motivo,
                 "e a mensagem diz qual é a chave de teste, para não travar o trabalho",
                 motivo[:120])

        # SEM login e COM a chave: libera, mas avisa que não há prova de quem é.
        acesso.LIBERAR_PAPEL_SEM_LOGIN = True
        falso = montar_streamlit(endereco="127.0.0.1", segredos=None, logado=False)
        with mock.patch.object(acesso, "st", falso):
            pode, motivo, sem_prova = acesso.autorizacao_para(acesso.PAPEL_COORDENACAO)
        conferir(pode, "com a chave de teste, o envio funciona sem login")
        conferir(sem_prova,
                 "mas o programa avisa que NÃO há prova de quem está usando",
                 "é esse aviso que a tela mostra em vermelho")
        conferir("registrado com o usuário do computador" in motivo,
                 "e diz o que vai para o registro nesse caso", motivo[:130])

        # Papel configurado vazio: barra e diz que falta configurar, em vez de
        # deixar passar. Falha fechada também aqui.
        acesso.LIBERAR_PAPEL_SEM_LOGIN = False
        acesso.EMAILS_POR_PAPEL[acesso.PAPEL_COORDENACAO] = []
        falso = montar_streamlit(endereco="0.0.0.0", segredos=AUTH_COMPLETO,
                                 logado=True, email="chefe@empresa.com")
        with mock.patch.object(acesso, "st", falso):
            pode, motivo, _ = acesso.autorizacao_para(acesso.PAPEL_COORDENACAO)
        conferir(not pode,
                 "lista de papel vazia NÃO libera todo mundo",
                 "seria o mesmo erro que a lista de e-mails vazia tinha antes")
        conferir("Ninguém está configurado" in motivo,
                 "e a mensagem diz que falta configurar o servidor", motivo[:90])

        # E os papéis não se confundem entre si.
        acesso.EMAILS_POR_PAPEL[acesso.PAPEL_COORDENACAO] = ["chefe@empresa.com"]
        acesso.EMAILS_POR_PAPEL[acesso.PAPEL_SUPERVISAO] = ["supervisao@empresa.com"]
        conferir(acesso.papeis_de("chefe@empresa.com") == {acesso.PAPEL_COORDENACAO},
                 "quem é coordenação não vira supervisão de graça",
                 str(acesso.papeis_de("chefe@empresa.com")))
        conferir(acesso.papeis_de("ninguem@empresa.com") == set(),
                 "e quem não tem papel nenhum tem conjunto vazio")
    finally:
        acesso.EMAILS_POR_PAPEL.clear()
        acesso.EMAILS_POR_PAPEL.update(papeis_originais)
        acesso.LIBERAR_PAPEL_SEM_LOGIN = sem_login_original

    # A tela precisa conferir onde a AÇÃO acontece, e não só ao desenhar o botão.
    #
    # "ENVIAR ARQUIVO DO POST" SE MUDOU PARA A PÁGINA DE UPLOADS EM
    # 23/09/2026, junto com a checagem de papel que a acompanha.
    pagina = open(os.path.join(BASE, "pages", "5_Uploads.py"),
                  encoding="utf-8").read()
    # Conta por padrão, e não por texto exato: a chamada pode estar quebrada em
    # duas linhas, e está. Contar texto cru dava falso negativo, e juntar os
    # espaços deixava " acesso.PAPEL" com espaço no meio do parêntese.
    # O papel da seção de envio manual é SUPERVISÃO, corrigido em 01/09/2026: ele
    # nasceu como coordenação porque o pedido falava da "coordenadora do setor",
    # e o auditor esclareceu que quem autoriza é a supervisão.
    chamadas = re.findall(r"autorizacao_para\(\s*acesso\.PAPEL_SUPERVISAO\s*\)", pagina)
    conferir(len(chamadas) >= 2,
             "a página confere o papel duas vezes: ao desenhar e ao agir",
             f"achei {len(chamadas)}; botão desabilitado é aparência, não autorização")
    # SÓ NA SEÇÃO DE ENVIO MANUAL, e não na página inteira (15/09/2026): desde
    # essa data a seção de "baixar de novo" de um sucesso passou a exigir
    # supervisão OU coordenação (mesmo mecanismo do Cadastro), então a página
    # como um todo passou a citar PAPEL_COORDENACAO de propósito. O que não
    # pode voltar é o papel errado especificamente na seção de envio manual,
    # que é column diferente: aqui quem autoriza é só a supervisão de
    # Marketing de Influência, nunca a coordenação.
    _inicio_envio = pagina.index('st.subheader("Enviar arquivo do post")')
    _resto = pagina[_inicio_envio:]
    # SEM PRÓXIMO st.subheader() DESDE 17/09/2026: "Enviar arquivo do post"
    # virou a última seção da página, depois que "Manutenção" saiu do fim da
    # tela (o botão de encerrar passou a viver só dentro de "Cuidar das
    # bibliotecas de download"). .find() em vez de .index(): sem achar,
    # -1 vira "vai até o fim do arquivo", que é o caso de agora.
    _fim_envio = _resto.find('st.subheader(', len('st.subheader("Enviar arquivo do post")'))
    _secao_envio = _resto if _fim_envio == -1 else _resto[:_fim_envio]
    conferir("PAPEL_COORDENACAO" not in _secao_envio,
             "e a seção de envio manual não exige mais coordenação, que era o papel errado",
             "supervisão e coordenação são níveis distintos na estrutura deles")

    print()
    print("--- 6. o segredo não pode ir para o repositório ---")
    # Este pedaço achou um buraco de verdade em 30/08/2026, ANTES de o arquivo
    # existir: a liberação era `!.streamlit/*.toml`, um curinga que pegaria o
    # secrets.toml junto. Antes de o arquivo existir é a única hora em que dá
    # para corrigir sem reescrever histórico do git.
    with open(os.path.join(BASE, ".gitignore"), encoding="utf-8") as f:
        gitignore = f.read()
    conferir("secrets.toml" in gitignore,
             "o secrets.toml está bloqueado pelo nome",
             "ele carrega client_secret e cookie_secret")
    conferir("!.streamlit/*.toml" not in gitignore,
             "e a pasta .streamlit NÃO é liberada por curinga",
             "curinga ali pegaria o secrets.toml junto")

    print()
    print("--- 6b. a dependência do login está na lista que vai para o servidor ---")
    # ACHADO DE 31/08/2026, e não foi revisão de código que pegou: o
    # requirements.txt foi montado lendo os imports dos arquivos .py, e nenhum
    # arquivo nosso importa authlib. Quem depende dela é o Streamlit, por dentro
    # do st.login. Resultado: o servidor seria montado sem ela e o login não
    # subiria, com o problema aparecendo no dia de ligar o login.
    with open(os.path.join(BASE, "requirements.txt"), encoding="utf-8") as f:
        requisitos = f.read().lower()
    conferir("authlib" in requisitos,
             "o requirements.txt lista a Authlib",
             "sem ela o st.login não sobe, mesmo com secrets.toml correto")
    # A checagem do próprio Streamlit é a fonte desta exigência. Se um dia ela
    # sair de lá, este teste passa a cobrar algo que não é mais necessário, e é
    # melhor descobrir por aqui.
    try:
        import streamlit.auth_util as _au
        conferir(hasattr(_au, "is_authlib_installed"),
                 "e o Streamlit realmente exige Authlib para o login",
                 "se isto falhar, reveja se a linha do requirements ainda faz sentido")
    except Exception as e:
        conferir(False, "consegui olhar a exigência do Streamlit", str(e)[:60])

    # A prova de verdade: perguntar ao próprio git, com um arquivo de mentira.
    import shutil
    import subprocess
    git = shutil.which("git") or os.path.expandvars(
        r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe")
    if not os.path.exists(str(git)):
        print("       (git não encontrado, pulei a conferência com o próprio git)")
        return
    pasta = os.path.join(BASE, ".streamlit")
    os.makedirs(pasta, exist_ok=True)
    falso = os.path.join(pasta, "secrets.toml")
    ja_existia = os.path.exists(falso)
    if ja_existia:
        print("       (já existe um secrets.toml de verdade, não vou mexer nele)")
    else:
        with open(falso, "w", encoding="utf-8") as f:
            f.write("[auth]\nclient_secret = \"DE_MENTIRA\"\n")
    try:
        r = subprocess.run([git, "check-ignore", ".streamlit/secrets.toml"],
                           cwd=BASE, capture_output=True, text=True)
        conferir(r.returncode == 0,
                 "o próprio git confirma que ele não subiria", r.stdout.strip())
        r2 = subprocess.run([git, "check-ignore", ".streamlit/config.toml"],
                            cwd=BASE, capture_output=True, text=True)
        conferir(r2.returncode != 0,
                 "e o config.toml continua podendo subir, que é o certo")
    finally:
        if not ja_existia and os.path.exists(falso):
            os.remove(falso)


if __name__ == "__main__":
    print("=" * 74)
    print("  Quem pode abrir o programa")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
