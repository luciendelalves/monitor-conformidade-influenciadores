"""
Identidade visual do programa, aplicada uma vez em painel.py e valendo para as
três abas.

As cores e as fontes vêm do design system do EGB
(contexto/design-system.html), não foram escolhidas aqui: navy institucional,
ciano de destaque, Plus Jakarta Sans nos títulos e Inter no texto. As cores
básicas também estão em .streamlit/config.toml, que é o único lugar de onde o
Streamlit lê tema; este arquivo cuida do resto.

O CSS aqui é deliberadamente contido. Streamlit muda a estrutura interna das
telas entre versões, então quanto mais o estilo depende de detalhe interno,
mais ele quebra numa atualização. O que está aqui mexe em tipografia,
espaçamento e nos poucos elementos com identificação estável.
"""

import streamlit as st

NAVY = "#0F1E3C"
CIANO = "#00BFFF"

# TESTIDS QUE O CSS MIRA E QUE NÃO EXISTEM NA VERSÃO INSTALADA (08/09/2026).
#
# Regra que mira nome inexistente não quebra nada, e é justamente o problema:
# ela fica no arquivo parecendo que funciona. Descoberto ao escrever
# teste_estilo_nao_usa_seletor_posicional.py, que confere cada nome contra o
# JS do Streamlit instalado.
#
# Ficam listados aqui em vez de apagados, porque em grupo de seletor a
# redundância é proteção contra renomeação, o mesmo raciocínio já aplicado a
# `stMainBlockContainer` e `.block-container`. O que não pode é ninguém saber
# qual está inativo.
#
#   stExpanderToggleIcon   zero ocorrências no Streamlit 1.59.2. O grupo em que
#                          ele está continua funcionando por `stIconMaterial`,
#                          que existe, e pelas classes .material-*. Sem esse
#                          grupo, a seta do expansor aparece como o texto
#                          "keyboard_double_arrow_left" escrito na tela.
TESTIDS_INATIVOS = {"stExpanderToggleIcon"}

_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --navy: #0F1E3C;
  --navy-alt: #1a3060;
  --ciano: #00BFFF;
  --g100: #F3F4F6;
  --g200: #E5E7EB;
  --g300: #D1D5DB;
  --g500: #6B7280;
  --g700: #374151;
  --g900: #111827;
  --verde: #059669;
  --ambar: #D97706;
  --vermelho: #DC2626;
  --raio-cartao: 13px;
  --raio-campo: 10px;
}

/* A fonte é aplicada nos contêineres e herdada dali pra dentro. NÃO usar um
   seletor amplo tipo [class*="st-"]: ele acerta também os elementos de ícone,
   e aí o desenho da seta vira o texto "keyboard_double_arrow_left" escrito na
   tela, porque ícone no Streamlit é uma fonte em que o nome vira desenho. */
[data-testid="stAppViewContainer"],
[data-testid="stSidebar"],
[data-testid="stHeader"] {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}
button, input, textarea, select { font-family: inherit; }
/* Devolve a fonte de ícone pra quem desenha ícone. */
[data-testid="stIconMaterial"],
[data-testid="stExpanderToggleIcon"],
.material-icons, .material-icons-outlined,
.material-symbols-rounded, .material-symbols-outlined {
  font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
               'Material Icons' !important;
}

h1, h2, h3, h4 {
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
  letter-spacing: -0.015em;
  color: var(--navy);
}
h1 { font-weight: 800 !important; }
h2, h3 { font-weight: 700 !important; }

/* st.subheader VIROU h3, E O TAMANHO PADRÃO DO STREAMLIT É GRANDE DEMAIS
   (14/09/2026, pedido do auditor olhando a tela: título de seção maior que o
   próprio título da página, .egb-titulo, que é 1.32rem). É usado em toda tela
   deste programa para separar seção ("Escopo contratado x entrega", "Link do
   Instagram para baixar e analisar", etc), então o ajuste é aqui, uma vez só,
   em vez de trocar cada st.subheader por markdown em cada arquivo. */
h3 { font-size: 1.05rem !important; }

/* ---------- largura e ritmo da página (08/09/2026) ----------

   A tela é `layout="wide"` desde sempre, mas o Streamlit ainda limita o bloco
   central, e o resultado era uma coluna estreita com muito vazio dos dois
   lados. São duas miras de propósito: `stMainBlockContainer` é o nome atual e
   `.block-container` é a classe que se manteve estável por muitas versões. Se
   uma sair numa atualização, a outra segura.                               */

[data-testid="stMainBlockContainer"], .block-container {
  max-width: 1240px !important;
  padding-top: 1.6rem !important;
}

/* RITMO VERTICAL MAIS APERTADO, e o motivo é a dobra, não estética. Na tela de
   Downloads o campo em que se trabalha ficava abaixo do título, da descrição,
   de quatro indicadores, de um aviso e de uma linha de estado. Cada um deles
   vinha com o espaçamento padrão do Streamlit, que é generoso para uma página
   de leitura e largo demais para uma tela de operação.

   Não mexemos na ORDEM dos blocos de propósito: reordenar código de página com
   1.400 linhas mexe em dependência de variável, e o programa entra em teste
   com o Marketing agora. Espaço resolve a maior parte com risco muito menor. */
[data-testid="stVerticalBlock"] { gap: 0.8rem; }
hr { margin: 0.8rem 0 !important; }

/* ---------- cabeçalho de página ---------- */

/* O TÍTULO ENCOLHEU EM 08/09/2026, e não é economia de espaço: a barra lateral
   já diz em que tela a pessoa está, com o item ativo destacado. Um título de
   1.9rem repetia essa informação com o maior tamanho da página, e empurrava
   para baixo da dobra justamente o campo em que se trabalha. Cromo redundante
   perde tamanho. */
.egb-cabecalho {
  border-bottom: 1px solid var(--g200);
  padding-bottom: 0.7rem;
  margin-bottom: 1.1rem;
}
.egb-eyebrow {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--ciano);
  margin-bottom: 0.35rem;
}
.egb-titulo {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.32rem;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.01em;
  color: var(--navy);
  margin: 0 0 0.2rem;
}
/* 68ch em vez de 78ch: acima disso o olho perde a linha na volta, e a
   descrição de tela é texto de leitura corrida, não dado. */
.egb-descricao {
  font-size: 0.9rem;
  color: var(--g500);
  margin: 0;
  max-width: 68ch;
  line-height: 1.5;
}

/* ---------- zonas coloridas do Financeiro (15/09/2026) ----------

   Pedido do auditor: a tela de Financeiro faz DUAS conferências diferentes
   (escopo do contrato inteiro, e cronograma data a data contra o Calendário
   do Marketing), e ficava difícil ver onde uma terminava e a outra começava.
   `st.container(key="...")` gera um `div` com a classe `st-key-<chave>`
   (documentado no próprio Streamlit, `elements/layouts.py`), e é nela que
   este seletor mira, em vez de uma classe interna que pode mudar de nome
   entre versões. */
.st-key-fin_zona_escopo {
  background: rgba(0, 191, 255, 0.05);
  border: 1px solid rgba(0, 191, 255, 0.18);
  border-radius: var(--raio-cartao);
  padding: 1rem 1.2rem;
}
.st-key-fin_zona_cronograma {
  background: rgba(5, 150, 105, 0.05);
  border: 1px solid rgba(5, 150, 105, 0.18);
  border-radius: var(--raio-cartao);
  padding: 1rem 1.2rem;
}
/* A TERCEIRA ZONA ENTROU EM 16/09/2026: a planilha de histórico virou seção
   própria no fim da tela, no mesmo papel que a Monitoramento tem na tela de
   Monitoramento. Cinza de propósito, e não uma terceira cor: é consulta ao
   que já aconteceu, não uma conferência em andamento como as duas de cima.

   O CINZA É O MESMO DO CADASTRO (107,114,128). Nasceu com 100,116,139 no
   mesmo dia, por descuido meu: duas zonas com o mesmo papel, em telas
   diferentes, precisam ser a mesma cor, senão a cor deixa de significar. */
.st-key-fin_zona_historico {
  background: rgba(107, 114, 128, 0.05);
  border: 1px solid rgba(107, 114, 128, 0.18);
  border-radius: var(--raio-cartao);
  padding: 1rem 1.2rem;
}

/* ---------- zonas coloridas das outras telas (15/09/2026) ----------

   MESMO PEDIDO DO AUDITOR, ESTENDIDO ÀS QUATRO TELAS: cada uma mistura
   funcionalidades diferentes visualmente, e a cor por zona (já aprovada no
   Financeiro, acima) organiza sem decorar, sempre em opacidade baixa (fundo
   0.05, borda 0.18) porque o app é claro e a cor aqui é organização, não
   ênfase.

   A CONVENÇÃO FOI REESCRITA EM 16/09/2026, numa revisão das quatro telas de
   uma vez. A de 15/09 descrevia o verde como "caminho alternativo de entrada
   de material, em Downloads", e o Financeiro já usava verde pra outra coisa
   (a conferência de cronograma): a regra não descrevia mais o próprio app.
   Agora ela é por FUNÇÃO, e vale igual nas quatro:

     CIANO  onde se trabalha: a frente principal daquela tela
     VERDE  a SEGUNDA frente de trabalho da mesma tela, quando existe uma e
            ela é outra coisa (entrada alternativa em Downloads, conferência
            de cronograma no Financeiro)
     CINZA  consulta ao que já existe, sem ação: a planilha do Cadastro e o
            histórico do Financeiro

   ÂMBAR SAIU DA LISTA EM 24/09/2026: era a zona de escrita do Cadastro,
   sem par nenhum hoje. Ver o comentário de .st-key-cad_zona_escrita, mais
   abaixo, para o porquê.

   E UMA REGRA DE USO, que veio do mesmo dia: DUAS ZONAS VIZINHAS NUNCA
   REPETEM A MESMA COR. Repetindo, a cor para de separar e viram só duas
   caixas iguais empilhadas. Quando a segunda seção não merece cor própria,
   ela fica SEM caixa, que é mais limpo do que pintá-la igual à de cima.

   Vermelho fica de fora de propósito: é reservado para aviso de erro e
   veredito NÃO CONFORME em outros lugares do app (ver .egb-veredito). */

/* Downloads e Organização */
.st-key-dl_zona_principal {
  background: rgba(0, 191, 255, 0.05);
  border: 1px solid rgba(0, 191, 255, 0.18);
  border-radius: var(--raio-cartao);
  padding: 1rem 1.2rem;
}
/* A ZONA DE EXCEÇÕES PERDEU A CAIXA EM 16/09/2026 (regra de "duas vizinhas
   nunca repetem cor", acima). Ela era ciana igual à zona principal e fica
   logo abaixo dela: eram duas caixas idênticas coladas, e a cor não estava
   separando nada. O container continua no código, com a chave, porque ele é
   o que agrupa a seção; só o fundo saiu. */
.st-key-dl_zona_alternativas {
  background: rgba(5, 150, 105, 0.05);
  border: 1px solid rgba(5, 150, 105, 0.18);
  border-radius: var(--raio-cartao);
  padding: 1rem 1.2rem;
}

/* Campo Jogo só em caixa alta (15/09/2026), pedido do auditor: é só
   aparência, força o que já aparece na tela enquanto a pessoa digita. Quem
   digita minúsculo ou cola texto de outro lugar continua normalizado de
   verdade no código (ver pages/1_Downloads_e_Organizacao.py), porque CSS
   não valida nada, só mostra diferente. */
.st-key-dl_campo_jogo input {
  text-transform: uppercase;
}

/* Monitoramento */
.st-key-mon_zona_andamento {
  background: rgba(0, 191, 255, 0.05);
  border: 1px solid rgba(0, 191, 255, 0.18);
  border-radius: var(--raio-cartao);
  padding: 1rem 1.2rem;
}
/* A ZONA DE CORREÇÃO PERDEU A CAIXA EM 16/09/2026, por dois motivos que se
   somam: ela era ciana igual à zona de andamento logo acima (regra de "duas
   vizinhas nunca repetem cor"), e o que ela envolve é um `st.expander`, que
   já é uma caixa fechada por si. Caixa colorida em volta de caixa é
   moldura de moldura. O container e a chave continuam no código. */

/* Cadastro de influenciadores */
.st-key-cad_zona_consulta {
  /* NEUTRO, E NÃO CIANO: é a leitura pura da planilha do Marketing, sem
     ação nenhuma sobre ela. Cinza em vez de --g100/--g200 sólido para
     manter a MESMA técnica (rgba baixo) das outras zonas coloridas. */
  background: rgba(107, 114, 128, 0.05);
  border: 1px solid rgba(107, 114, 128, 0.18);
  border-radius: var(--raio-cartao);
  padding: 1rem 1.2rem;
}
/* A ZONA DE ESCRITA PERDEU O ÂMBAR EM 24/09/2026. Ela nasceu âmbar em
   15/09 porque era a única escrita direta na planilha real do Marketing a
   partir desta tela. Isso mudou em 23/09: a tela passou a espelhar a real
   numa cópia antes de abrir, e as três escritas abaixo miram só a cópia
   (ver cadastro.espelhar_cadastro_para_teste). Manter o âmbar depois disso
   avisava um risco que não existe mais do jeito antigo, e ficava estranho
   ao lado do cinza da zona de consulta, que é logo acima (regra de "duas
   vizinhas nunca repetem cor", já usada aqui mesmo). O container e a chave
   continuam no código, sem cor: a exigência de supervisão ou coordenação
   continua valendo, só que aparece na hora de tentar preencher, e não como
   caixa colorida por cima de tudo. */

/* ---------- barra lateral ---------- */

[data-testid="stSidebar"] {
  background: var(--navy);
  border-right: none;
}
[data-testid="stSidebar"] * { color: #E5EAF3; }

/* BOTÃO NA BARRA LATERAL (corrigido em 31/08/2026, visto na tela no primeiro
   uso do login).
   A regra logo acima pinta TODO descendente da barra lateral de cor clara, e o
   botão do programa tem fundo branco. O resultado era caixa branca com texto
   quase branco: o "Sair" ficava ilegível e a caixa parecia campo de digitar,
   ao ponto de ser confundida com o campo de nome. Na barra escura o botão
   passa a ser escuro com borda clara, que é o que combina com o fundo. */
[data-testid="stSidebar"] .stButton button {
  background: transparent;
  border: 1px solid rgba(229, 234, 243, 0.45);
  color: #E5EAF3;
}
[data-testid="stSidebar"] .stButton button:hover {
  background: var(--navy-alt);
  border-color: var(--ciano);
  color: #FFFFFF;
}
[data-testid="stSidebarNav"] a {
  border-radius: var(--raio-campo);
  margin: 2px 6px;
  padding: 0.35rem 0.6rem;
}
[data-testid="stSidebarNav"] a:hover { background: var(--navy-alt); }
[data-testid="stSidebarNav"] a[aria-current="page"] {
  background: rgba(0, 191, 255, 0.15);
  box-shadow: inset 3px 0 0 var(--ciano);
}
[data-testid="stSidebarNav"] a[aria-current="page"] span { color: #FFFFFF; font-weight: 600; }
/* O nome da aba vinha cortado ("Validação Re..."). Deixa quebrar em duas
   linhas em vez de esconder metade do nome. */
[data-testid="stSidebarNav"] a span {
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
}

/* ---------- campo de identificação, na barra lateral ----------

   Ele estava apagado justamente onde precisa chamar atenção (apontado em
   30/08/2026): fundo claro sobre fundo escuro, com o texto de exemplo em
   cinza quase ilegível. Como sem o nome o programa não separa o trabalho de
   uma pessoa do das outras, o campo VAZIO precisa parecer pendência, e o
   preenchido precisa sossegar.                                            */

[data-testid="stSidebar"] [data-testid="stTextInput"] label p {
  color: #FFFFFF;
  font-weight: 600;
  font-size: 0.86rem;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input {
  background: var(--navy-alt);
  color: #FFFFFF;
  border: 1px solid rgba(0, 191, 255, 0.45);
  font-size: 0.95rem;
  font-weight: 500;
}
/* Cinza claro sobre azul escuro não se lê. */
[data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder {
  color: #9FB3CC;
  opacity: 1;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input:focus {
  border-color: var(--ciano);
  box-shadow: 0 0 0 3px rgba(0, 191, 255, 0.25);
}
/* Vazio chama atenção. Preenchido para de chamar. */
[data-testid="stSidebar"] [data-testid="stTextInput"] input:placeholder-shown {
  border-color: var(--ambar);
  background: rgba(217, 119, 6, 0.14);
}

/* ---------- indicadores ---------- */

/* A SOMBRA SAIU EM 08/09/2026, e a razão é de desenho, não de gosto: raio
   igual em tudo, borda igual em tudo e a mesma sombra suave embaixo de cada
   caixa é o arranjo mais repetido de painel genérico. Sem ela, o indicador
   passa a ser uma superfície contida, e a única coisa da tela que ganha
   presença de verdade é o veredito. Ver .egb-veredito. */
[data-testid="stMetric"] {
  background: #FFFFFF;
  border: 1px solid var(--g200);
  border-radius: var(--raio-cartao);
  padding: 0.85rem 1rem;
  height: 100%;
}
/* ALTURA IGUAL NA FILEIRA. O quarto indicador da tela de Downloads tem uma
   variação embaixo ("11 restantes") e os outros três não, então a caixa dele
   crescia e a linha perdia o alinhamento. Esticar a coluna resolve sem
   depender de saber quantos indicadores existem. */
[data-testid="stHorizontalBlock"] { align-items: stretch; }
[data-testid="stMetricLabel"] p {
  font-size: 0.7rem !important;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--g500) !important;
  line-height: 1.35;
}
/* O RÓTULO PASSA A QUEBRAR EM VEZ DE SER CORTADO. Na tela, "STORY HOJE (CONTA
   @CANDYBOXCONFE..." aparecia truncado com reticências, e o que sumia era
   justamente qual conta. Duas linhas de rótulo custam menos que esconder a
   informação. */
[data-testid="stMetricLabel"] {
  white-space: normal !important;
  overflow: visible !important;
}
[data-testid="stMetricValue"] {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.75rem !important;
  font-weight: 700;
  color: var(--navy);
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
[data-testid="stMetricDelta"] { font-size: 0.78rem; }

/* ---------- botões e campos ---------- */

.stButton button, .stDownloadButton button, .stLinkButton a, .stFormSubmitButton button {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-weight: 600;
  border-radius: var(--raio-campo);
  transition: transform .12s ease, box-shadow .12s ease;
}
.stButton button:hover, .stFormSubmitButton button:hover { transform: translateY(-1px); }
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
  background: var(--navy);
  border-color: var(--navy);
  color: #FFFFFF;
}
.stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover {
  background: var(--navy-alt);
  border-color: var(--navy-alt);
  color: #FFFFFF;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-baseweb="select"] > div {
  border-radius: var(--raio-campo) !important;
}

[data-testid="stForm"] {
  border: 1px solid var(--g200);
  border-radius: var(--raio-cartao);
  padding: 1.2rem 1.3rem 0.6rem;
  background: #FFFFFF;
}
/* O Streamlit escreve "Press Enter to submit form" dentro de todo campo de
   texto que esteja num formulário. Isso se sobrepõe à dica que a gente
   escreve no campo e deixa as duas ilegíveis. Some com o aviso: quem usa o
   programa não precisa dele, e o botão de enviar está logo ali. */
[data-testid="InputInstructions"] { display: none; }

/* ---------- avisos ---------- */

[data-testid="stAlert"] { border-radius: var(--raio-campo); }

/* ---------- nota de estado, e a regra de cor (08/09/2026) ----------

   COR CARREGA VEREDITO, NÃO DECORAÇÃO. Verde, âmbar e vermelho ficam
   reservados para o que a régua decidiu sobre uma peça. Antes eles vazavam
   para linha de encanamento, do tipo "trabalhador de pé e sem nada em
   andamento", que ganhava um ✅ verde. Estado de rotina não é conformidade, e
   gastar a paleta de veredito nele tira força de quem precisa dela.

   Então: estado normal é CINZA. Só sobe de cor quando pede ação.
   `.egb-nota` também substitui o emoji que ficava na frente dessas linhas: o
   fio da esquerda diz a mesma coisa, e não muda de desenho conforme o sistema
   operacional de quem abre.                                                */

.egb-nota {
  display: flex;
  gap: 0.55rem;
  align-items: baseline;
  font-size: 0.84rem;
  color: var(--g500);
  line-height: 1.5;
  padding: 0.2rem 0 0.2rem 0.65rem;
  border-left: 2px solid var(--g300);
  margin: 0.35rem 0;
}
.egb-nota--atencao { border-left-color: var(--ambar); color: var(--g700); }
.egb-nota--problema { border-left-color: var(--vermelho); color: var(--g700); }
.egb-nota b { color: var(--g900); font-weight: 600; }

/* ---------- o veredito, e é o único lugar com presença de verdade ----------

   Toda a tela é contida para que isto não seja. O programa existe para
   entregar um veredito com evidência, então o veredito é o que o olho encontra
   primeiro. Chanel: antes de sair, tire um acessório. Os acessórios saíram das
   caixas de indicador; ficaram aqui.                                       */

.egb-veredito {
  border: 1px solid var(--g200);
  border-left: 4px solid var(--g300);
  border-radius: var(--raio-cartao);
  padding: 0.9rem 1.1rem;
  background: #FFFFFF;
}
.egb-veredito__rotulo {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--g500);
  margin-bottom: 0.15rem;
}
.egb-veredito__valor {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1.2;
  color: var(--navy);
}
.egb-veredito--conforme { border-left-color: var(--verde); }
.egb-veredito--conforme .egb-veredito__valor { color: var(--verde); }
.egb-veredito--nao-conforme { border-left-color: var(--vermelho); }
.egb-veredito--nao-conforme .egb-veredito__valor { color: var(--vermelho); }
.egb-veredito--verificar { border-left-color: var(--ambar); }
.egb-veredito--verificar .egb-veredito__valor { color: var(--ambar); }

/* ---------- barra de progresso ----------

   Ela era ciano de largura total e pesava mais que o número que mede. Fina e
   contida, ela volta a ser indicador em vez de faixa decorativa.

   O ALVO É O NOME, NÃO A POSIÇÃO, e isso custou um defeito em tela para ficar
   claro (08/09/2026). A primeira versão desta regra era:

       [data-testid="stProgress"] > div > div { height: 5px; }

   Lendo o código do Streamlit (static/Progress.*.js), o desenho é:

       div[data-testid="stProgress"]
         div                                    <- envolve o RÓTULO
           div                                  <- o markdown do texto
         ProgressBar
           div[data-testid="stProgressBarTrack"] <- a barra

   Então "> div > div" acertou o contêiner do TEXTO e o achatou em 5px. Na tela,
   a frase "100% do que tem vídeo já validado" transbordou e a barra ciano foi
   desenhada por cima dela. É exatamente o que o docstring deste arquivo avisa
   no começo, e foi desrespeitado no mesmo dia em que foi escrito. */
[data-testid="stProgressBarTrack"] { height: 5px !important; }

/* ---------- tabelas ---------- */

[data-testid="stDataFrame"] { border-radius: var(--raio-campo); overflow: hidden; }

/* ---------- legendas e divisores ---------- */

[data-testid="stCaptionContainer"] p { color: var(--g500); line-height: 1.55; }
hr { border-color: var(--g200); }

/* ---------- respeita quem prefere menos animação ---------- */

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
  .stButton button:hover, .stFormSubmitButton button:hover { transform: none; }
}
</style>
"""


def _sem_linhas_em_branco(texto):
    """Tira as linhas vazias do bloco antes de mandar pra tela.

    Não é firula: o Markdown encerra um bloco de HTML na primeira linha em
    branco que encontra. Com as linhas em branco que deixam o CSS legível aqui
    no arquivo, tudo o que vinha depois da primeira delas era mostrado como
    texto na tela em vez de aplicado como estilo. Mantendo a limpeza só na
    hora de injetar, o arquivo continua legível e a tela funciona."""
    return "\n".join(linha for linha in texto.splitlines() if linha.strip())


def aplicar():
    """Injeta a identidade visual. Chamar uma vez, em painel.py."""
    st.markdown(_sem_linhas_em_branco(_CSS), unsafe_allow_html=True)


def porcento(valor):
    """Percentual sem decimal inútil: 100.0 sai "100", e 45.2 sai "45,2".

    POR QUE ISTO EXISTE (08/09/2026). A tela mostrava "100.0% do que tem vídeo
    já validado". A casa decimal num número redondo é precisão falsa, e chama
    atenção para o lugar errado. Onde a casa decimal informa, ela fica.

    A vírgula é decimal em português, e o Streamlit não formata isso por
    conta."""
    texto = f"{float(valor):.1f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def nota(texto, tipo="normal"):
    """Linha de estado discreta, no lugar de emoji com legenda.

    `tipo` é "normal", "atencao" ou "problema". NÃO existe tipo "ok" de
    propósito: estado de rotina é cinza, porque verde é reservado para veredito
    de conformidade. Ver o comentário de .egb-nota no CSS.

    Use isto para o que o programa está fazendo ou acabou de fazer. Para o que
    a régua decidiu sobre uma peça, use veredito()."""
    sufixo = "" if tipo == "normal" else f" egb-nota--{tipo}"
    st.markdown(f'<div class="egb-nota{sufixo}">{texto}</div>',
                unsafe_allow_html=True)


_CLASSE_DO_VEREDITO = {
    "Conforme": "conforme",
    "Não Conforme": "nao-conforme",
    "Requer Verificação": "verificar",
}


def veredito(valor, rotulo="Veredito", classificacao=None):
    """O veredito da régua, e é o único elemento com presença na tela.

    `classificacao` é o que decide a cor, e aceita as três da régua: Conforme,
    Não Conforme e Requer Verificação. Qualquer outra coisa, ou nada, sai em
    navy, que é o neutro. Não inventa cor para valor que não conhece: cor
    errada num veredito é pior que cor nenhuma."""
    classe = _CLASSE_DO_VEREDITO.get(str(classificacao or valor).strip())
    sufixo = f" egb-veredito--{classe}" if classe else ""
    st.markdown(
        f'<div class="egb-veredito{sufixo}">'
        f'<div class="egb-veredito__rotulo">{rotulo}</div>'
        f'<div class="egb-veredito__valor">{valor}</div>'
        f'</div>',
        unsafe_allow_html=True)


def cabecalho(titulo, descricao="", secao=""):
    """Cabeçalho padrão das três abas, para que todas comecem igual.

    `secao` é o rótulo pequeno acima do título. Ele era "Auditoria Interna" em
    todas as telas e SAIU EM 01/09/2026, por decisão do auditor: a ferramenta
    passa a ser do Marketing de influência, e o rótulo dizia a origem errada.

    Vazio, o rótulo não é desenhado, em vez de aparecer uma faixa em branco.
    Continua aceitando um valor para quem quiser identificar uma tela
    específica.

    `descricao` é a linha que explica o que a tela faz, e deve caber em uma ou
    duas frases: quem precisa de mais que isso está lendo o README."""
    linha_desc = f'<p class="egb-descricao">{descricao}</p>' if descricao else ""
    linha_secao = f'<div class="egb-eyebrow">{secao}</div>' if secao else ""
    st.markdown(
        f'<div class="egb-cabecalho">'
        f'{linha_secao}'
        f'<h1 class="egb-titulo">{titulo}</h1>'
        f'{linha_desc}'
        f'</div>',
        unsafe_allow_html=True,
    )
