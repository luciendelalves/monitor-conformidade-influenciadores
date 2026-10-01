# -*- coding: utf-8 -*-
"""
Prova que encerrar o trabalhador avisa o alcance, e que a tela não voltou a
ficar cheia de botão.

POR QUE ESTE TESTE EXISTE (31/08/2026)

Existe UM trabalhador para as cinco pessoas. Quem clica em "Encerrar o
trabalhador" encerra o de todas, e o texto do botão não dizia isso: lia como
ação local de quem clicou. Numa ferramenta de auditoria isso é pior do que
parece, porque quem encerrou não fica sabendo que interrompeu a fila alheia, e
quem foi interrompido não fica sabendo por quê.

A decisão do auditor foi avisar em vez de tirar o botão da tela, porque
encerrar antes de atualizar o programa é o procedimento correto e frequente.
Então o que este teste protege é o aviso: se alguém reescrever o texto e o
alcance sumir, o teste cai.

Confere também que a marcação de ciência só aparece quando há trabalho de
verdade em andamento ou na fila. Se ela aparecesse sempre, viraria clique
automático e deixaria de ser aviso.

A última seção guarda a simplificação da mesma tela, pedida no mesmo dia:
"Abrir a fila" e o expansor "Anteriores" saíram, e nenhum dos dois deve voltar
por descuido em alteração futura. Nenhum dos dois guardava dado: a fila continua
na planilha e o histórico continua no registro do fluxo, no fim da tela.

    py testes\teste_manutencao_e_atalhos.py
"""
import os
import re
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


class Caixa:
    """Imita o que o `with st.popover(...)` devolve."""

    def __enter__(self):
        return self

    def __exit__(self, *erro):
        return False


class StreamlitFalso:
    """Registra o que a tela desenhou, para o teste poder olhar.

    O botão desabilitado devolve False, igual ao Streamlit de verdade. É isso
    que faz o teste medir o efeito (o pedido de parada acontece ou não) em vez
    de só conferir um parâmetro.
    """

    def __init__(self, ciencia_marcada=False, clicou=True):
        self.ciencia_marcada = ciencia_marcada
        self.clicou = clicou
        self.textos = []
        self.avisos = []
        self.checkboxes = []
        self.botoes = []
        self.caixa = None

    def popover(self, rotulo, **kwargs):
        # Guarda em `caixa`, e não em `popover`: atributo com o nome do método
        # apagaria o próprio método.
        self.caixa = (rotulo, kwargs)
        return Caixa()

    def caption(self, texto, **kwargs):
        self.textos.append(texto)

    def warning(self, texto, **kwargs):
        self.avisos.append(texto)

    def success(self, texto, **kwargs):
        self.textos.append(texto)

    def checkbox(self, rotulo, **kwargs):
        self.checkboxes.append(rotulo)
        return self.ciencia_marcada

    def button(self, rotulo, **kwargs):
        self.botoes.append((rotulo, kwargs))
        if kwargs.get("disabled"):
            return False
        return self.clicou


class FilaFalsa:
    RODANDO = "rodando"
    PENDENTE = "pendente"

    def __init__(self, rodando=0, esperando=0, de_pe=True, fazendo=()):
        self.quantidades = {self.RODANDO: rodando, self.PENDENTE: esperando}
        self._de_pe = de_pe
        self._fazendo = list(fazendo)
        self.parada_pedida = False

    def contar(self, situacao, tipo=None):
        return self.quantidades.get(situacao, 0)

    def trabalhador_de_pe(self):
        return self._de_pe, {"fazendo_agora": self._fazendo}

    def pedir_parada(self):
        self.parada_pedida = True


def montar(rodando=0, esperando=0, de_pe=True, fazendo=(), ciencia=False, clicou=True):
    import painel_trabalhador

    tela = StreamlitFalso(ciencia_marcada=ciencia, clicou=clicou)
    fila = FilaFalsa(rodando=rodando, esperando=esperando, de_pe=de_pe, fazendo=fazendo)
    painel_trabalhador.st = tela
    painel_trabalhador.fila = fila
    painel_trabalhador.botao_encerrar()
    return tela, fila


def rodar():
    print("--- 1. sem nada em andamento, não custa clique a mais ---")
    tela, fila = montar()
    conferir(not tela.checkboxes,
             "sem trabalho na fila, não pede marcação de ciência",
             str(tela.checkboxes))
    conferir(not tela.avisos, "e não mostra aviso de trabalho em andamento", str(tela.avisos))
    conferir(tela.botoes and not tela.botoes[0][1].get("disabled"),
             "o botão de encerrar vem liberado", str(tela.botoes))
    conferir(fila.parada_pedida, "e o pedido de parada chegou ao trabalhador")

    print()
    print("--- 2. o alcance está escrito na tela ---")
    tudo = " ".join(tela.textos).lower()
    conferir("não só você" in tudo or "nao so voce" in tudo,
             "o texto diz que não alcança só quem clicou")
    conferir("todas as pessoas" in tudo,
             "o texto diz que alcança todas as pessoas que usam o programa")
    conferir("fila" in tudo,
             "o texto explica que o pedido fica esperando na fila depois disso")

    print()
    print("--- 3. com trabalho em andamento, exige ciência ---")
    tela, fila = montar(rodando=2, esperando=3, fazendo=["analisar @exemplo"])
    conferir(len(tela.checkboxes) == 1,
             "aparece a marcação de ciência", str(tela.checkboxes))
    conferir(tela.avisos and "2 em andamento" in tela.avisos[0],
             "avisa quantos estão em andamento", str(tela.avisos))
    conferir(tela.avisos and "3 esperando na fila" in tela.avisos[0],
             "avisa quantos estão esperando", str(tela.avisos))
    conferir(any("@exemplo" in t for t in tela.textos),
             "mostra o que está sendo feito agora", str(tela.textos))
    conferir(tela.botoes and tela.botoes[0][1].get("disabled"),
             "o botão fica travado enquanto a ciência não é marcada", str(tela.botoes))
    conferir(not fila.parada_pedida,
             "e NADA é encerrado sem a ciência",
             "este é o ponto do teste: o efeito, não só o parâmetro")

    print()
    print("--- 4. marcou ciência: aí sim encerra ---")
    tela, fila = montar(rodando=2, fazendo=["analisar @exemplo"], ciencia=True)
    conferir(tela.botoes and not tela.botoes[0][1].get("disabled"),
             "o botão libera depois da marcação", str(tela.botoes))
    conferir(fila.parada_pedida, "o pedido de parada chegou ao trabalhador")

    print()
    print("--- 5. trabalhador fora do ar: não há o que encerrar ---")
    tela, fila = montar(de_pe=False)
    conferir(tela.caixa and tela.caixa[1].get("disabled"),
             "o botão nasce desabilitado quando ninguém está de pé",
             str(tela.caixa))

    print()
    print("--- 6. a tela de Downloads continua sem botão demais ---")
    caminho = os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py")
    fonte = open(caminho, encoding="utf-8").read()
    # Procura pelo uso, e não pela palavra: o comentário que explica a retirada
    # cita os dois nomes de propósito, e não pode derrubar o teste.
    conferir('("📋 Abrir a fila"' not in fonte,
             "o atalho 'Abrir a fila' não voltou",
             "saiu em 31/08; a fila é passagem, e continua registrada na planilha")
    conferir('st.expander(f"▾ Anteriores' not in fonte and 'st.expander("▾ Anteriores' not in fonte,
             "o expansor 'Anteriores' não voltou",
             "saiu em 31/08; o histórico completo fica no registro do fluxo")
    # O CARACTERE NÃO ENTRA NO TEXTO IMPRESSO, só na comparação. O console do
    # Windows usa cp1252, que não tem o triangulinho, e imprimi-lo derrubava o
    # teste com UnicodeEncodeError DEPOIS de a conferência já ter passado: a
    # suíte acusava falha onde não havia (visto em 04/09/2026).
    conferir('st.expander("▾' not in fonte,
             "nenhum rotulo de expansor traz o triangulo que o Streamlit "
             "ja desenha sozinho")

    print()
    print("--- 6b. um clique só para baixar (01/09/2026) ---")
    # Pedido do auditor: "o usuário coloca o link e clica em BAIXAR". Antes eram
    # dois cliques em botões diferentes, "Adicionar" aqui e "Baixar e analisar
    # agora" mais abaixo na tela.
    # O QUE ESTA CONFERÊNCIA GUARDA é o rótulo, e não a linha em que ele foi
    # escrito. A versão anterior exigia o texto exato
    # `form_submit_button("⬇️ Baixar"`, com o emoji grudado. Em 08/09/2026 o
    # emoji saiu (virou `icon=":material/download:"`, ver
    # teste_telas_sem_emoji_em_botao.py) e a linha ficou longa demais, então
    # foi quebrada em duas. Nada do que este teste protege mudou, e ele
    # acusou falha: estava medindo a formatação do código, não o rótulo.
    conferir(bool(re.search(r'form_submit_button\(\s*"Baixar"\s*,', fonte)),
             "o botão do formulário é Baixar, e não Adicionar")
    conferir('form_submit_button("➕ Adicionar"' not in fonte,
             "o rótulo Adicionar não voltou")
    conferir("ja_tem_trabalho = fila_trabalho.ha_trabalho" in fonte,
             "o clique manda baixar, mas não cria tarefa se já há uma esperando",
             "cada tarefa processa TODOS os pendentes; a segunda ficaria vazia")

    # O PONTO QUE PROTEGE O CONTROLE DE RAJADA, e é o que faria essa mudança
    # piorar tudo se fosse feita do jeito óbvio: uma tarefa por clique, de um
    # link cada, deixaria as pausas de fora, porque elas acontecem entre links
    # da mesma rodada e não entre tarefas.
    conferir("elas acontecem dentro" in fonte or "não entre tarefas" in fonte,
             "e o motivo disso está escrito no código, para não ser desfeito",
             "sem a explicação, alguém 'simplifica' e volta a rajada")

    conferior_pendentes = "Baixar os {len(pendentes)} que ficaram pendentes"
    conferir(conferior_pendentes in fonte,
             "o segundo botão passou a ser só para o que ficou pendente")
    conferir("if pendentes:" in fonte,
             "e ele só aparece quando existe pendência",
             "antes ficava na tela dizendo '0 pendente(s)'")

    print()
    print("--- 7. falha não pode aparecer como sucesso ---")
    # ACHADO NA TELA PELO AUDITOR em 31/08/2026, no uso real. Um Story que era
    # foto, e não vídeo, saiu como "0 de 1 baixados e organizados" com a MARCA
    # VERDE de sucesso. A tarefa termina como concluída porque a rodada rodou
    # até o fim; o arquivo que não veio é resultado dela, não erro dela. Só que
    # marca verde com zero é pior que erro: lê como "está tudo bem".
    #
    # É o mesmo padrão do defeito do vídeo reaproveitado, corrigido antes: a
    # detecção funcionava e a reação estava errada.
    #
    # MUDOU EM 23/09/2026: resumo_da_tarefa se mudou de dentro da página para
    # fluxo_downloads.py, porque passou a servir duas páginas (Downloads e
    # Uploads), e função de tela não é importável sem rodar a tela inteira.
    # Virando função de módulo comum, a extração de código-fonte que existia
    # aqui (carregar só um pedaço do arquivo sem executar a tela) deixou de
    # ser necessária: agora é só importar.
    import fluxo_downloads as fluxo_para_o_teste

    caminho_pagina = os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py")
    fonte_pagina = open(caminho_pagina, encoding="utf-8").read()

    conferir(hasattr(fluxo_para_o_teste, "resumo_da_tarefa"),
             "resumo_da_tarefa existe em fluxo_downloads.py",
             "se voltar a viver só dentro de uma tela, deixa de ser "
             "testável sem rodar o Streamlit inteiro")
    resumo = fluxo_para_o_teste.resumo_da_tarefa

    fila_real = __import__("fila_trabalho")

    # O caso exato que apareceu na tela.
    foto = {
        "situacao": fila_real.CONCLUIDA,
        "tipo": fila_real.BAIXAR_FILA,
        "terminou_em": "2026-08-31 16:06:46",
        "resultado": {"processados": 1, "organizados": 0},
        "mensagens": [
            "[Fila linha 21] | https://www.instagram.com/stories/exemplo/1/",
            "   -> FALHA: Story é uma foto, não um vídeo, fora do escopo atual",
        ],
    }
    aparencia, texto, motivos = resumo(foto)
    conferir(aparencia == "erro",
             "1 processado e 0 organizados NÃO aparece como sucesso", aparencia)
    conferir("Nenhum arquivo entrou" in texto,
             "e o texto diz que nada entrou", texto)
    conferir(any("foto" in m for m in motivos),
             "e o motivo da falha vem junto, sem precisar abrir nada", str(motivos))

    # FALHA REAL QUE ESCAPOU DA PRIMEIRA VERSÃO, em 31/08/2026, no mesmo dia.
    # A seleção dos motivos procurava a palavra "FALHA", e a primeira falha real
    # que apareceu no uso não usava essa palavra: um story cujo link não trazia o
    # número, de influenciador sem número de perfil guardado. O resumo saiu
    # vermelho e certo, e o motivo ficou escondido justamente quando era mais
    # necessário.
    sem_numero = {
        "situacao": fila_real.CONCLUIDA,
        "tipo": fila_real.BAIXAR_FILA,
        "terminou_em": "2026-08-31 18:33:30",
        "resultado": {"processados": 1, "organizados": 0},
        "mensagens": [
            "18:31:52 [Fila linha 26]  | https://www.instagram.com/stories/exemplo/?hl=pt",
            "18:31:52    (organizando como @exemplo, que é o @ do próprio link)",
            "18:31:57    -> Ainda não sei o número do perfil de @exemplo, e a consulta "
            "pelo @ não respondeu agora (429 Too Many Requests). Adicione na fila um "
            "link de Reel ou post desse mesmo influenciador.",
            "18:31:57    (pausa de 92s antes do próximo link do Instagram, de propósito)",
        ],
    }
    aparencia, texto, motivos = resumo(sem_numero)
    conferir(aparencia == "erro", "a falha sem a palavra FALHA também é erro", aparencia)
    conferir(any("número do perfil" in m for m in motivos),
             "e o motivo aparece mesmo sem a palavra FALHA na mensagem",
             str(motivos)[:140])
    conferir(not any("pausa de 92s" in m for m in motivos),
             "e a linha que é só informação não entra como motivo",
             "a seleção é pela seta, que marca resultado de item")

    parcial = {
        "situacao": fila_real.CONCLUIDA,
        "tipo": fila_real.BAIXAR_FILA,
        "terminou_em": "2026-08-31 17:00:00",
        "resultado": {"processados": 3, "organizados": 2},
        "mensagens": ["   -> FALHA: link privado"],
    }
    aparencia, texto, _ = resumo(parcial)
    conferir(aparencia == "atencao", "2 de 3 aparece como atenção, não sucesso", aparencia)
    conferir("1 não entrou" in texto, "dizendo quantos ficaram de fora", texto)

    inteiro = {
        "situacao": fila_real.CONCLUIDA,
        "tipo": fila_real.BAIXAR_FILA,
        "terminou_em": "2026-08-31 18:00:00",
        "resultado": {"processados": 2, "organizados": 2},
        "mensagens": [],
    }
    aparencia, texto, _ = resumo(inteiro)
    conferir(aparencia == "ok", "2 de 2 continua aparecendo como sucesso", aparencia)

    # RODADA VAZIA: NEM FALHA NEM SUCESSO (revisto em 02/09/2026).
    #
    # A regra original era só "não acusar falha", e por isso este caso caía no
    # mesmo verde de sucesso das outras. Em 02/09 o auditor viu na tela "0 de 0
    # baixados e organizados" em verde e leu como defeito do programa, com
    # razão: a frase conta uma divisão que não aconteceu e a cor afirma que deu
    # certo algo que não foi feito.
    #
    # A conferência passou a ser pela INTENÇÃO das duas pontas, e não pelo valor
    # exato: não pode ser erro, e não pode ser o mesmo verde de quem trabalhou.
    vazia = {
        "situacao": fila_real.CONCLUIDA,
        "tipo": fila_real.BAIXAR_FILA,
        "terminou_em": "2026-08-31 19:00:00",
        "resultado": {"processados": 0, "organizados": 0},
        "mensagens": ["Nada para baixar: a fila está vazia."],
    }
    aparencia, texto_vazia, motivos_vazia = resumo(vazia)
    conferir(aparencia != "erro", "rodada sem nada para baixar não acusa falha",
             aparencia)
    conferir(aparencia != "ok", "e também não se pinta de sucesso", aparencia)
    conferir("0 de 0" not in texto_vazia,
             "o texto não conta uma divisão que não aconteceu", texto_vazia)
    conferir(any("nada para baixar" in m.lower() for m in motivos_vazia),
             "e a explicação do trabalhador aparece sem precisar abrir nada",
             str(motivos_vazia))

    # E a tarefa que falhou de verdade continua sendo erro.
    quebrou = {
        "situacao": fila_real.FALHA,
        "tipo": fila_real.BAIXAR_FILA,
        "terminou_em": "2026-08-31 20:00:00",
        "erro": "conexão perdida",
    }
    aparencia, texto, _ = resumo(quebrou)
    conferir(aparencia == "erro", "tarefa que falhou continua como erro", aparencia)
    conferir("conexão perdida" in texto, "e mostra o erro", texto)

    print()
    print("--- 8. com trabalho em andamento, o resultado anterior não aparece ---")
    conferir("if tem_trabalho:\n        return" in fonte_pagina,
             "a tela sai antes de desenhar o resultado anterior",
             "eram dois blocos de registro na tela ao mesmo tempo")


if __name__ == "__main__":
    print("=" * 70)
    print("  Encerrar o trabalhador, e a tela sem botão demais")
    print("=" * 70)
    print()
    rodar()
    print()
    print("=" * 70)
    if falhas:
        print(f"  {len(falhas)} FALHA(S):")
        for f in falhas:
            print(f"    - {f}")
    else:
        print("  PASSOU.")
    print("=" * 70)
    sys.exit(1 if falhas else 0)
