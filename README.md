# Automação de Auditoria de Influenciadores

Sistema em duas partes que atende o ciclo completo da auditoria de publicidade de
influenciadores: **baixar e organizar** o material publicado, e depois **conferir
automaticamente** se ele traz os avisos obrigatórios.

Versão deste documento: 1.1, de 29/08/2026.

> **Atenção:** hoje o sistema aponta para planilhas e pastas de **TESTE**. Nada
> aqui escreve na Monitoramento real do Marketing. Ver "Antes de subir no
> servidor" no fim.

---

## Visão geral do fluxo

```
link do post
   │
   ├─ Parte 1 ─ baixa o vídeo, organiza no Drive,
   │            e grava a linha na Monitoramento (colunas W a AB)
   │
   │            o link do arquivo na coluna X é o gatilho
   │
   └─ Parte 2 ─ pega as linhas com arquivo e sem veredito, baixa a mídia,
                confere os avisos obrigatórios e devolve o veredito
                na MESMA planilha (colunas Z, AA e AB)
```

Desde 28/08/2026 a **Monitoramento é a fonte única**: a planilha antiga de
validação saiu do fluxo. As colunas A a V são do Marketing e a automação só lê;
as colunas W a AB são da automação e o Marketing só lê. A automação **só escreve
em célula vazia**, então apagar a célula VALIDACAO de uma linha é o jeito de
mandar reprocessar.

Quem executa as duas partes é o **trabalhador**, um programa separado da tela
(ver "Como rodar").

---

## Parte 1: Downloads e Organização

Aplicação: `pages/1_Downloads_e_Organizacao.py`
Motor: `fluxo_downloads.py`

### O que a tela oferece

**1. Fila de downloads.** A pessoa cola o link do post, escolhe influenciador,
ciclo e bet, e a automação baixa o vídeo, sobe para a pasta
`@influenciador/Ciclo N` no Drive e cria a linha na Monitoramento. Tem botão para
reabrir uma linha já processada e para limpar a fila.

**2. Registrar link do YouTube.** Para vídeo e live do YouTube, que são grandes
demais para baixar. **Não baixa nada**, só grava o endereço na Monitoramento como
registro. Todos os campos são obrigatórios aqui, porque sem arquivo não há de
onde deduzir influenciador nem data. O mesmo endereço não entra duas vezes.

**2.1. Enviar foto do post.** Aceita PNG e JPG. Vai para as mesmas pastas de post
no Drive. Os campos são opcionais: em branco, o programa descobre influenciador e
data pelo nome do arquivo, e o ciclo pela data.

**3. Pasta monitorada.** Alternativa ao envio pela tela, válida só enquanto o
programa roda na máquina da pessoa. Basta salvar o arquivo em
`teste_watch_folder/downloads_simulado` que a automação identifica e organiza.
Num servidor com várias pessoas isso não vale, porque cada uma baixa na própria
máquina.

### Proteções contra bloqueio do Instagram

O Instagram barra contas que apresentam padrão automatizado. O programa tem três
freios, todos em `fluxo_downloads.py`:

| Freio | Valor | O que faz |
|---|---|---|
| Limite diário | 12 por conta | Para de falar com o Instagram ao atingir |
| Pausa entre chamadas | 45 a 120 segundos | Espaça as tentativas |
| Máximo por rodada | 3 | Evita rajada |
| Pausa após bloqueio | 24 horas | Ao detectar bloqueio, para de insistir |

O estado fica em `teste_watch_folder/estado_conta_instagram.json`, por conta.
Sinais tratados como bloqueio: 429, 401, "please wait a few minutes", challenge,
checkpoint.

**Limitação conhecida:** o contador é por conta, não por máquina. Trocar de conta
zera o contador sem querer, e duas contas saindo do mesmo endereço de rede é, por
si só, um padrão que a plataforma costuma sinalizar.

### Autenticação

Story exige sessão autenticada. Os cookies são exportados do navegador por
extensão e salvos em `teste_watch_folder/cookies_instagram.txt`. A constante
`USUARIO_DOS_COOKIES` precisa bater com a conta de onde vieram, senão a biblioteca
trata a sessão como anônima e os limites ficam muito mais duros.

### Onde as coisas são gravadas

| O quê | Onde |
|---|---|
| Vídeos e fotos | Drive, pasta de TESTE, em `@influenciador/Ciclo N` |
| Cópia local espelho | `teste_watch_folder/drive_simulado` (só teste, `MANTER_COPIA_LOCAL_DE_TESTE`) |
| Linha da Monitoramento | planilha cujo id está em `teste_watch_folder/monitoramento_teste_id.txt` |
| Fila | planilha cujo id está em `teste_watch_folder/fila_downloads_id.txt` |
| Registro de tudo | `teste_watch_folder/log_fluxo_completo.csv` |

Os ids ficam em arquivo, não fixos no código. Para apontar para outra planilha,
basta trocar o conteúdo desses arquivos.

Colunas da Monitoramento que a automação preenche: influenciador (B), mês (K),
ano (L), data do post (M), ciclo (N), tipo (O), número do post (P), marca (R) e
link (T). As demais ficam em branco para preenchimento humano.

---

## Parte 2: Análise dos avisos obrigatórios

Aplicação: `app_validacao_influenciadores.py`
Orquestração: `pipeline_influenciadores.py`
Motor de análise: `validar_avisos_portaria136.py`
Versão sem tela: `processar_lote_cli.py`

### O que ele confere

Os avisos exigidos pela Portaria SPA/MF nº 136/2025 e correlatas, **por peça**, não
por post. Um clipe sem aviso não é coberto pelo aviso de outro clipe do mesmo
story.

| Elemento | Quando é exigido |
|---|---|
| 18+ ou restrição de idade | sempre |
| Menção à portaria | sempre |
| Identificação de publicidade (#publi) | sempre |
| "Jogue com responsabilidade" ou equivalente | posts **anteriores** a 17/07/2026 |
| Uma das 3 frases do Ministério da Fazenda | posts **a partir** de 17/07/2026 |

A partir de 17/07/2026 (Portaria SPA/MF 1.964/2026, art. 13, II) a frase do
Ministério da Fazenda **substitui** o aviso de jogo responsável, não se acumula
com ele.

### Como ele procura

Escada de quatro degraus, do mais rápido para o mais demorado, subindo só
enquanto faltar algum elemento exigido para a data daquele post:

| Degrau | Tempo por quadro | Por que existe |
|---|---|---|
| 1. Tesseract | 1,5s | Resolve banner nítido, é o mais rápido |
| 2. RapidOCR | 5,9s | Melhor em 18+, portaria e principalmente #publi |
| 3. EasyOCR | 11,3s | Único bom no aviso de jogo responsável em texto miúdo |
| 4. Visão local (Ollama) | ~5s por pergunta | Lê selo e emoji, que nenhum leitor de texto reconhece |

Medição de 28/08/2026 em 40 quadros reais, sendo 24 de casos difíceis conhecidos.
Somando os três leitores de texto, a detecção melhora nos cinco elementos e não se
perde nenhum caso.

O áudio é transcrito à parte (faster-whisper) para detectar fala vedada pelo CONAR
Anexo X: ilusão de controle, promessa de enriquecimento e sugestão de que o ganho
é repetível. **O áudio nunca conta como aviso**, porque a norma exige aviso
escrito.

### Regra de ouro da classificação

**Só o texto lido conta como prova.** A visão local pode errar, e já confirmou um
"18+" numa imagem que era só print de conversa. Quando ela sugere presença de algo
que nenhum leitor de texto confirmou, o post vai para **Requer Verificação**, nunca
para Conforme.

| Classificação | Significado |
|---|---|
| **Conforme** | Todo clipe com conteúdo de aposta tem o aviso completo exigido para a data |
| **Não Conforme** | Falta pelo menos um elemento obrigatório, confirmado por ausência no texto |
| **Requer Verificação** | Pasta vazia, arquivo com indício de recompressão, ou sinal ambíguo que o programa não consegue confirmar nem descartar |

### Onde ele lê e escreve

Planilha `1Uzxi3K1o6Nq7bgUhLZNBIYm5Qw7hD9Y7FOtLxr4-V9w`, aba "Validação
Regulatória de Publicações (SPA/+18)".

| Coluna | Uso |
|---|---|
| A a E | leitura: influenciador, ano, data, tipo, link |
| F | veredito da automação |
| G | qual vídeo específico é o problema, com link |
| H | alerta de fala problemática no áudio |
| I | alerta de aparição de criança |

Uma linha é **pendente** enquanto a coluna F estiver vazia. Os resultados também
ficam guardados em
`producao/auditorias/avisos-influenciadores-portaria136/resultados.json`, gravado
de forma segura contra interrupção (arquivo temporário mais cópia de segurança).

### Desempenho medido

Medições de 28/08/2026, em uso real, máquina de 12 núcleos e 15,7 GB:

| Configuração | Por vídeo | Por hora |
|---|---|---|
| 1 análise por vez | 185s | 19 vídeos |
| **2 ao mesmo tempo** | **110s** | **33 vídeos** |

O modelo de visão é a etapa que mais demora e roda num **servidor único
compartilhado** por todos os processos. Por isso aumentar o paralelismo tem limite: passa um ponto
e todos passam a esperar na fila dele em vez de calcular.

Uma linha da planilha equivale a **uma pasta de post**, que na base atual tem em
média 1,7 arquivos, sendo 2 vídeos o caso mais comum.

---

## Instalação

**Programas externos:**

- Python 3.14
- Tesseract OCR (caminho hoje fixo em `validar_avisos_portaria136.py`)
- FFmpeg e FFprobe (hoje procurados em pastas do WinGet, específico de Windows)
- Ollama, com o modelo `minicpm-v` baixado

**Bibliotecas Python:**

```
streamlit openpyxl pandas
opencv-python pillow numpy
pytesseract easyocr rapidocr-onnxruntime
faster-whisper
yt-dlp instaloader
google-api-python-client google-auth-oauthlib
```

**Credenciais do Google**, em `_drive_credenciais/`, uma por finalidade, cada uma
com o mínimo de permissão:

| Arquivo | Para quê |
|---|---|
| `drive_token.json` | ler vídeos do Drive |
| `drive_file_token.json` | subir arquivos criados pelo próprio programa |
| `sheets_write_token.json` | ler e escrever nas planilhas |

Os scripts `autorizar_*.py` geram cada um deles.

**Ajuste recomendado no Ollama**, para o modelo não descarregar entre chamadas:

```
OLLAMA_KEEP_ALIVE=-1
OLLAMA_NUM_PARALLEL=4
```

---

## Como rodar

São **dois programas**, e os dois precisam estar de pé.

**1. O trabalhador**, que é quem baixa e analisa de verdade:

```
cd producao/analises
py trabalhador.py
```

Ou dois cliques em `iniciar_trabalhador.bat`. A janela precisa ficar aberta.

**2. A tela**, que é por onde as pessoas pedem o trabalho:

```
cd producao/analises
py -m streamlit run painel.py --server.port 8501 --server.fileWatcherType none --server.runOnSave false
```

Abre em `http://localhost:8501`, com três abas na barra lateral: **Downloads**,
**Validação Regulatória** e **Monitoramento**. Se o trabalhador não estiver de
pé, a tela avisa em vermelho e o que for pedido fica esperando na fila.

O arquivo de entrada é o `painel.py`, que só monta a barra lateral e dá nome a
cada aba. Ele existe porque, sem ele, o Streamlit usa o nome do arquivo como
nome da aba. A configuração da página (título da janela, ícone, largura) mora
só nele, porque o Streamlit aceita essa chamada uma única vez.

O `--server.fileWatcherType none` é proposital: sem ele, salvar qualquer arquivo
do projeto durante um lote **derruba o lote em andamento**. Em compensação,
qualquer alteração de código só entra depois de reiniciar.

### Por que dois programas (29/08/2026)

Até 28/08/2026 o trabalho acontecia dentro da aba do navegador de quem clicava.
Isso funcionava com uma pessoa e não funciona com cinco, por três motivos:

1. **Cada aba abria o seu próprio grupo de processos de análise.** Cinco pessoas
   clicando ao mesmo tempo viravam dez análises disputando o mesmo modelo de
   visão, que é um servidor só. Medido em 28/08/2026: acima de duas análises ao
   mesmo tempo não há ganho nenhum. O resultado não seria cinco vezes mais
   rápido, seria todo mundo mais lento.
2. **Duas pessoas baixando ao mesmo tempo furavam o teto diário do Instagram**,
   porque cada uma contava as chamadas por conta própria. Foi descuido com esse
   contador que marcou duas contas em agosto de 2026, com uma pessoa só usando.
3. **Fechar a aba deixava o lote órfão**, consumindo a máquina sem ninguém
   conseguir acompanhar nem parar.

Agora existe **uma fila só** (`fila_trabalho.py`, gravada em
`teste_watch_folder/fila_trabalho/`) e **um trabalhador só** (`trabalhador.py`).
A tela apenas põe tarefa na fila e mostra a situação. Fechar a aba não perde
nada, e o que uma pessoa enfileira todas as outras enxergam.

Ter um trabalhador só não é limitação técnica: é o número certo, porque o
gargalo é um servidor de modelo compartilhado e um teto de chamadas por
endereço de rede. Mais processos não produzem mais, só distribuem a mesma
capacidade entre mais gente esperando.

### Encerrar antes de atualizar

Alterar arquivo com trabalho em andamento derruba o que está rodando. Use
**Manutenção > Encerrar o trabalhador** no fim da tela de Downloads: ele termina
o que já começou e sai. O que não tiver terminado volta para a fila sozinho na
próxima vez que ele subir.

### Linha de comando

`processar_lote_cli.py` está **desatualizado e travado desde 29/08/2026**. Ele
escreve na planilha antiga de validação, que saiu do fluxo, e concorre com o
trabalhador. Para rodar um lote sem tela, enfileire e deixe o trabalhador
executar.

---

## Limitações conhecidas

**Fechar a aba do navegador não afeta mais nada** desde 29/08/2026: quem executa
é o trabalhador, num programa separado. Se o trabalhador cair, o que estava em
andamento volta para a fila quando ele subir de novo.

**Suspender a máquina para o trabalhador**, porque ele roda nela. Bloquear a tela
é seguro.

**Os quadros analisados saem todos do primeiro 0,7 segundo do vídeo.** O filtro de
extração pega 3 quadros por segundo e usa os 3 primeiros, então mais de 98% de um
vídeo de 60 segundos nunca é olhado. Um aviso que apareça só no fim não é visto.
Correção pendente de decisão, porque muda o resultado das análises já feitas.

**A checagem de aparição de criança está desligada** desde 28/08/2026, por decisão
do auditor. Ela consumia 50,3% do tempo total e nunca gerou um alerta em 445
linhas. A coluna I passa a dizer "não verificado" em vez de ficar em branco,
porque célula vazia seria lida como "conferido e sem criança". Religar é trocar
`CHECAR_CRIANCA_VISUAL` para `True`.

**A checagem de criança nunca alcançou a faixa de 15 a 17 anos**, que é a que a
norma protege. A pergunta é restrita a "claramente uma criança", porque um modelo
de visão genérico não é um classificador de idade confiável nessa faixa.

**Várias pessoas podem usar a tela ao mesmo tempo desde 29/08/2026**, mas a
produção total continua a mesma: o trabalhador é um só, com duas análises ao
mesmo tempo, o que dá cerca de 33 vídeos por hora somando todo mundo. Cinco
pessoas usando não produzem cinco vezes mais, produzem o mesmo, dividido entre
elas. Isso é o teto do modelo de visão, não da tela, e nenhuma mudança de
programa muda esse número.

**Não existe login.** Quem alcança o endereço do programa usa as credenciais do
Google que estão no servidor, que hoje são as de uma pessoa física e de escopo
amplo. As tarefas já registram quem pediu cada uma, e esse campo passa a valer
sozinho quando o login for ligado, mas até lá ele guarda o usuário do
computador, não a pessoa autenticada.

**Um vídeo baixado duas vezes hoje entra duas vezes na pasta.** A proteção atual
compara o link do Drive, que é novo a cada envio. Correção na fila.

---

## Antes de subir no servidor

Ver também `Checklist_Subir_App_No_Servidor.html`, com a lista completa.

Os pontos que impedem o programa de rodar ou que mudam o desenho:

1. **Caminhos fixos de Windows.** O leitor de texto está apontado para uma pasta
   do usuário atual, e o programa de vídeo é procurado em pastas do WinGet. Em
   Linux, nada disso existe.
2. **Planilhas e pastas de TESTE.** Trocar os ids nos arquivos de
   `teste_watch_folder` e a planilha de validação, com acordo formal do Marketing
   sobre quem pode escrever nas colunas F a I.
3. **Cookies do Instagram são por pessoa.** Não existe uma sessão compartilhada, e
   concentrar tudo numa conta só aumenta o risco de bloqueio dela.
4. **Uma fila única em vez de lotes em paralelo.** Cinco pessoas rodando ao mesmo
   tempo dariam 10 ou mais processos disputando um único servidor de visão, que é
   o cenário em que todos ficam parados esperando.
5. **Dimensionamento.** Sem placa de vídeo dedicada, servidor com menos de 12
   núcleos fica mais lento que a máquina atual. Com placa de vídeo, bem mais
   rápido, porque a etapa de visão é a que mais demora.

---

## Pendências combinadas

1. Travar o uso a uma conta de Instagram por dia **por máquina**, não por conta.
2. Impedir que o mesmo vídeo entre duas vezes na pasta, conferindo nome e conteúdo
   antes de subir.
3. Página só de consulta com a Monitoramento dentro do programa.
4. Decidir como a linha registrada pela Parte 1 entra automaticamente na fila da
   Parte 2.
5. Decidir se a amostragem de quadros passa a cobrir o vídeo inteiro.
