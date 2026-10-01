# Instalar o Monitoramento de Influenciadores

**Versão 22 · 17/09/2026.** Financeiro, tela "Histórico de entregas": a nota
de orgânico contratado saiu do "Conferir à mão" (já é conferido na rotina
normal, sem veredito nenhum a decidir); o texto de orgânico que continua
("contam à parte") foi corrigido para "contam no total junto com o resto",
que é como funciona desde 16/09/2026. A seção "Histórico de entregas" virou
sempre visível, no topo da tela, e não depende mais de escolher um
influenciador antes (achado ao testar: o seletor de Influenciador do topo
abria com o primeiro @ da lista já marcado, sem ninguém escolher, e isso
escondia o histórico e confundia o filtro dele, que copiava esse @ sem
querer). Ganhou filtros novos de Marca e Ciclo, numa linha só com os que já
existiam (Situação/Influenciador/Procurar); "Quem registrou" chegou a entrar
como filtro à parte no mesmo dia, mas saiu por ser a mesma pergunta que o
"Procurar" já responde.

**Versão 21 · 17/09/2026.** Empacotamento, sem mudança de código: o mapa
`pasta_por_handle_futebol.json` (Responsável B, layout FUTEBOL) voltou a vir dentro
do zip geral de instalação. Tinha saído mais cedo no mesmo dia por menor
exposição (não é dado sensível, só @ de influenciador e apelido de pasta),
mas o auditor decidiu que simplicidade da instalação pesa mais: um zip só
para todo mundo, mesmo o mapa dela viajando também para quem não é FUTEBOL,
sem uso nenhum lá.

**Versão 20 · 17/09/2026.** Dois achados testando ao vivo, sem relação entre
si. Primeiro: "Horas de live" sem os dois-pontos e com menos de 5 dígitos
seguidos (ex: "0150" pensando em 1h50) virava a leitura errada calada
("00:01:50", 1 minuto e 50), porque com poucos dígitos não dá para saber se
sobrou hora ou minuto. Agora esse caso é recusado, com aviso pedindo os
dois-pontos ("1:50") ou os 6 dígitos ("015000"); esses dois formatos
continuam funcionando como sempre. Segundo: a coluna SITUACAO da
Monitoramento tinha o texto "SEM ARQUIVO" para LIVE e YouTube (que nunca são
baixados, de propósito), e isso lia como defeito. Virou "N/A" na própria
planilha, igual já valia para VALIDACAO e VALIDADO_EM na mesma linha; quem
lê a coluna programaticamente (`tem_arquivo_para_analisar`) continua
reconhecendo os dois textos, o novo e o velho, então linha antiga não
precisa ser corrigida à mão.

**Versão 19 · 17/09/2026.** Achado testando ao vivo o caso @saporitorenata:
a tabela "Escopo contratado x entrega" mostrava tudo ✅ (stories e reels
batendo exato) e mesmo assim pedia justificativa obrigatória, sem dizer por
quê, porque faltava confirmar uma diária de gravação que nem aparecia na
tabela. Dois ajustes: a entrega fora da plataforma agora ganha linha própria
na tabela (⏳ até confirmar, ✅ depois); e a justificativa deixou de ser
SEMPRE obrigatória ao marcar o check (como a Versão 18 registrava) — só
volta a pedir quando, mesmo com a confirmação, o ciclo continuar incompleto
de verdade ou algum tipo mensurável ficar abaixo do combinado. Confirmar
sozinho, quando fecha o ciclo por inteiro, vira só um motivo automático na
tela, sem texto obrigatório.

**Versão 18 · 17/09/2026.** O teto diário do Instagram (20 em dia útil, 30 no
fim de semana) parou de travar download. Decisão do auditor, depois de o
risco pra metodologia de subida medida ter sido levantado: o número virou
"teto recomendado", só um aviso na tela, e passar dele não impede mais
nenhuma chamada. As outras duas proteções da mesma função continuam
travando de verdade, sem mudança nenhuma: uma conta por dia por máquina, e a
pausa depois de bloqueio real do Instagram. Foi corrigida também uma
condição de corrida na gravação da Monitoramento (dois registros ao mesmo
tempo podiam se sobrescrever), e a régua de fechamento de ciclo ganhou um
jeito de confirmar manualmente entrega fora da plataforma (diária de
gravação, por exemplo) (regra da justificativa revista na Versão 19).
Contagem de testes do passo 9 corrigida de 72 para 74.

**Versão 17 · 16/09/2026.** Mais um achado na instalação da Responsável A,
agora no login (`st.login`): ficava num loop voltando pro botão "Entrar",
sem aviso na tela. O motivo, só visível no terminal, era
`CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain` —
a rede da empresa tem inspeção de HTTPS (mesma classe de problema que o
`curl_cffi` já documentava para o download), e a biblioteca do login
(`httpx`, por baixo do Authlib) não confiava no certificado que o Windows já
confia. Corrigido com o pacote `truststore` (novo, 19º pacote), ligado bem
no topo de `painel.py`. Contagem de pacotes do passo 5 e da tabela do passo
8, ambas desatualizadas havia tempo, corrigidas de 18/17 para 19.

**Versão 16 · 16/09/2026.** Achado na instalação da Responsável A, no passo
7.4: em notebook corporativo com antivírus/EDR que sonda porta recém-aberta,
o login do Google podia falhar sempre, primeiro com `WSGITimeoutError` no
Prompt de Comando, depois com `ERR_CONNECTION_REFUSED` no navegador, mesmo
com tudo certo (rede, proxy, Firewall). Os três `autorizar_*.py` corrigidos
para não desistir mais na primeira coisa que tocar a porta local. Uma
segunda rodada de teste, no mesmo dia, achou mais um: a correção inicial
passava a URL capturada como `http://`, e o `oauthlib` recusa processar
resposta de OAuth2 que não seja `https`, mesmo em `localhost`
(`InsecureTransportError`). Corrigido junto. Ver "Se der errado", nova
linha, e `_drive_credenciais/autorizar_local.py`.

**Versão 15 · 16/09/2026.** A régua de escopo x entrega passou a contar tudo:
orgânico e os tipos que a análise não alcança (tweet, YouTube, TikTok,
Facebook) agora entram no total dos dois lados, e uma entrega a mais em um
tipo compensa falta em outro. Quando o ciclo só fecha porque alguém confirma
à mão que uma entrega desses tipos existe, aparece a situação nova "Apto a
pagamento, com conferência humana", separada de CONFORME de propósito. A
linha do Financeiro na tabela "As quatro telas" foi corrigida (não existe
"aviso para o Financeiro", nunca existiu depois de 11/09), e a contagem de
testes do passo 9 foi de 70 para 71.

**Versão 14 · 15/09/2026.** Novo passo 7.6: como configurar os papéis de
supervisão e coordenação (`EMAILS_SUPERVISAO`/`EMAILS_COORDENACAO`), que não
tinha instrução nenhuma no guia apesar de já ser exigido pelo Cadastro desde
14/09; passou a valer também para reabrir e baixar de novo um download que já
teve sucesso, então a tabela "As quatro telas" foi atualizada para dizer isso
na linha do Downloads.

**Versão 13 · 15/09/2026.** A tela "Validação Regulatória" saiu do programa
(o essencial dela migrou para dentro do Monitoramento), então "As cinco
telas" virou "As quatro telas". E a instalação da Responsável B (FUTEBOL) mudou de
plano no item (d) do passo 7: Monitoramento e Calendário continuam na cópia
de teste por enquanto, não nos ids reais e compartilhados como este guia
dizia antes; só o Drive segue como decisão à parte.

**Versão 12 · 14/09/2026.** Substitui as versões anteriores. O que mudou: a
contagem de pacotes do passo 5 estava errada há tempo (dizia 17, o
`requirements.txt` sempre teve 18, contando o `Authlib` acrescentado em
31/08/2026).

**Versão 11 · 12/09/2026.** o passo 7 ganhou uma bifurcação nova, para quem
instala numa máquina que vai cobrir a categoria FUTEBOL, num Drive próprio,
diferente do Drive do Marketing (ver "Instalação para quem cobre FUTEBOL",
dentro do passo 7); a contagem de testes do passo 9 foi corrigida (estava
desatualizada há tempo); e os números do teto do Instagram e da pausa entre
downloads, na seção "Quanto tempo leva", foram atualizados para bater com o
código vigente (pausa mais curta desde 11/09, teto de fim de semana novo
desde 12/09).

Passo a passo para colocar o programa para rodar numa máquina nova.

**Tempo:** de 1 a 2 horas, quase tudo download. **Máquina:** 16 GB de memória e
60 GB livres em disco.

---

## Pedido para o TI, antes de tudo

É comum a conta de trabalho não ter admin local (confirmado isso até na
conta da própria auditoria: só está no grupo `Usuários`, não em
`Administradores`). Por isso, antes de agendar a instalação, mande um pedido
único para o TI com os quatro itens abaixo, em vez de descobrir a trava no
meio da visita:

| o quê | por onde | comando ou instrução |
|---|---|---|
| **Python 3.14** | instalador (site oficial) | marcar `Add python.exe to PATH` na primeira tela |
| **Tesseract OCR** | **instalador, não `winget`** | marcar `Portuguese` na tela de idiomas — ver por quê no passo 2 |
| **ffmpeg** | Prompt de Comando | `winget install Gyan.FFmpeg` |
| **Ollama** | Prompt de Comando | `winget install --id Ollama.Ollama --accept-source-agreements --accept-package-agreements` |
| **modelo de visão do Ollama** | Prompt de Comando, depois do item acima | `ollama pull minicpm-v` (cerca de 5,5 GB) |

**O Tesseract é o único que precisa mesmo do instalador.** Existe
`winget install --id UB-Mannheim.TesseractOCR`, mas a instalação silenciosa
por esse caminho **não traz o pacote de português**, só o inglês — o mesmo
defeito do parágrafo do passo 2, só que chegando por outra porta. Corrigir
depois exigiria copiar o `por.traineddata` para dentro de
`C:\Program Files\Tesseract-OCR\tessdata`, que também tende a pedir admin,
então não sobra vantagem em tentar pelo cmd neste item específico.

Se o `winget` estiver bloqueado nesta máquina, peça a versão portátil do
ffmpeg (zip, sem instalador) no lugar do comando acima.

Se a máquina tiver bloqueio de instalação por política (AppLocker, Defender
Application Control ou parecido), isso vale mesmo com a opção "instalar só
para mim": diga ao TI que precisa dos quatro programas acima instalados, não
só de "liberar admin", porque a política pode barrar o instalador de
qualquer forma.

Vale confirmar também se a rede da empresa deixa acessar `pypi.org` (os
pacotes do Python, passo 5), `ollama.com` e `github.com` (Tesseract): proxy
corporativo pode bloquear esses downloads sem aviso nenhum, e isso só
aparece na hora, no meio da instalação.

---

## Antes de começar, peça duas coisas

Peça a quem administra o programa, por um canal seguro:

1. **A pasta do programa** (`producao\analises`), copiada da máquina de origem.
2. **A pasta `contexto\Auditoria-MKT de influencers`**, que fica um nível acima e
   não vem junto na cópia. É de lá que sai o ciclo de cada vídeo.

Dentro da pasta do programa, dois arquivos de credencial já vêm prontos, e
também só podem vir por canal seguro, nunca e-mail comum:

- **`_drive_credenciais\oauth_client.json`**: o cadastro do programa no
  Google, igual em qualquer instalação. Não precisa recriar.
- **`.streamlit\secrets.toml`** completo, com as cinco chaves: é o login do
  próprio programa, também igual em qualquer máquina.

**O que NÃO vem pronto, de propósito:** os três tokens de login no Google
(`drive_token.json`, `drive_file_token.json`, `sheets_write_token.json`,
também dentro de `_drive_credenciais`). Eles são o que diz QUEM está lendo e
escrevendo no Drive e nas planilhas. Se vierem prontos da máquina de quem te
ajudou a instalar, toda escrita nas planilhas passa a aparecer no histórico
de edição no nome dessa pessoa, não no seu. O passo 7 mostra como criar os
seus, com a sua própria conta Google, em poucos minutos.

Enquanto a pasta do programa não chegar, você já pode fazer os passos 1 a 5.

---

## Passo 1: Python 3.14

Baixe em <https://www.python.org/downloads/> a versão **3.14**.

**Na primeira tela do instalador, marque a caixa `Add python.exe to PATH`.** Sem
ela, todos os comandos deste guia respondem "comando não encontrado".

Confira no Prompt de Comando:

```
py -V
```

Tem que responder `Python 3.14.x`.

---

## Passo 2: Tesseract OCR, com o português

Baixe o instalador em <https://github.com/UB-Mannheim/tesseract/wiki>.

**Na tela de idiomas, marque `Portuguese`.** Sem isso o programa lê português com
o modelo de inglês e não vê duas das três frases obrigatórias do Ministério da
Fazenda. Já aconteceu, e a análise daquele período foi descartada.

Instale no caminho que o instalador sugere. O programa acha sozinho.

**Não tem por `winget` neste item.** Existe o pacote, mas a instalação
silenciosa por ali não traz o português, é a mesma armadilha do parágrafo
acima chegando por outra porta. Ver a tabela do início do guia.

---

## Passo 3: ffmpeg

No Prompt de Comando:

```
winget install Gyan.FFmpeg
```

É esta a forma recomendada porque é a única pasta que o programa encontra
sozinho. Confira:

```
ffmpeg -version
ffprobe -version
```

---

## Passo 4: Ollama e o modelo de visão

1. Instale o Ollama: <https://ollama.com/download>
2. No Prompt de Comando:

```
ollama pull minicpm-v
```

**São 5,5 GB, o download mais pesado do guia.** Deixe rodando e vá tomar um café.

---

## Passo 5: os pacotes do Python

Com o Prompt de Comando **dentro da pasta `producao\analises`**:

```
py -m pip install -r requirements.txt
```

São 19 pacotes com versão fixa, cerca de 800 MB. Se algum falhar com mensagem
sobre "wheel" ou "build", a causa quase sempre é versão de Python diferente da
3.14: volte ao passo 1.

> A primeira análise que você rodar ainda baixa mais uns 200 MB de modelos,
> sozinha. Por isso ela é mais lenta que as seguintes e precisa de internet.

---

## Passo 6: limpar o estado da outra máquina

A cópia trouxe arquivos que descrevem a máquina de origem. Um comando resolve:

```
py preparar_copia.py
```

Ele mostra o que vai apagar, pergunta se esta é a máquina nova, e você responde
`SIM`. Ele não toca em credencial, identificador nem cache.

No fim, ele lista os oito arquivos que **precisam** ter chegado na pasta
`teste_watch_folder`. Se algum aparecer como `FALTA`, peça a quem administra o
programa antes de continuar.

---

## Passo 7: identidade da máquina, Instagram e Google

**Este é o passo mais fácil de errar em silêncio.** Duas contas diferentes
entram aqui, a do Instagram (7.1 e 7.2) e a do Google (7.3 a 7.5), e as DUAS
precisam ser suas, não de quem te ajudou a instalar.

**7.1.** Abra o **Firefox**, entre no Instagram com a conta de trabalho e deixe
logado. O programa lê a sessão direto do Firefox.

> Tem que ser Firefox. Chrome e Edge, da versão 127 em diante, cifram os cookies
> de um jeito que impede a leitura por fora.

**7.2.** Abra o arquivo `teste_watch_folder\conta_instagram.txt` e troque o que
está lá pelo **@ da sua conta, sem o arroba, numa linha só**:

```
seuusuario
```

Ele chegou com o nome da conta da máquina de origem. Se ficar assim, o programa
trabalha se apresentando como outra pessoa, o Instagram trata o acesso como
anônimo sem avisar, e a conta corre risco de bloqueio. O passo 8 mostra qual
conta está valendo, para você confirmar.

> **Uma conta por dia por máquina.** Duas contas diferentes falando com o
> Instagram no mesmo dia, do mesmo endereço de rede, é o padrão que leva ao
> bloqueio. Cada pessoa usa a conta dela, na máquina dela.

**7.3.** Confirme que `_drive_credenciais\oauth_client.json` chegou junto com
a pasta do programa (ver "Antes de começar"). Sem ele, os comandos do próximo
item param sozinhos com uma mensagem dizendo onde procuraram e como resolver.

**7.4.** Com o Prompt de Comando **dentro de `_drive_credenciais`**, rode os
três comandos abaixo, um de cada vez, esperando cada um terminar antes do
próximo:

```
py autorizar_drive.py
py autorizar_drive_escrita_arquivo.py
py autorizar_sheets_escrita.py
```

Cada um abre o navegador pedindo login do Google. **Entre com a SUA conta**,
a mesma que tem acesso à Monitoramento e ao Drive do Marketing, nunca com a
de quem te ajudou a instalar. Ao aceitar a permissão na tela do Google, cada
script grava o seu próprio token (`drive_token.json`,
`drive_file_token.json`, `sheets_write_token.json`) dentro de
`_drive_credenciais`, por cima de qualquer um que tenha chegado junto por
engano.

> **Por que isso importa:** sem este passo, o programa lê e escreve no Drive
> e nas planilhas se apresentando como quem autorizou antes, não como você.
> Toda edição feita por você ficaria registrada no histórico no nome errado.

**7.5.** Confirme, com quem administra a Monitoramento e o Drive do
Marketing, que a SUA conta Google já tem permissão de **edição** (não só
visualização) nos arquivos que o programa vai usar: a cópia de teste, sempre;
a Monitoramento e o Drive reais, só quando o modo real for combinado (ver o
Anexo no fim deste guia). Autorizar sem ter essa permissão não dá erro
nenhum na hora, só quebra depois, na primeira tentativa de escrita.

**7.6. Papéis de supervisão e coordenação** (15/09/2026, opcional na
instalação, mas sem isso duas coisas ficam travadas para todo mundo: corrigir
ou incluir/excluir no Cadastro, e reabrir para baixar de novo um vídeo que já
teve sucesso). Sem configuração nenhuma, a tela mostra "Ninguém está
configurado com o papel de supervisão ou coordenação neste servidor" e
recusa as duas ações, sempre, mesmo para quem devia poder.

Quem administra o servidor define, com o Prompt de Comando:

```
setx EMAILS_SUPERVISAO "fulana@empresa.com,beltrano@empresa.com"
setx EMAILS_COORDENACAO "ciclana@empresa.com"
```

Uma lista por papel, e-mails separados por vírgula, sem espaço depois da
vírgula. Os dois papéis são **distintos** na estrutura deles: coordenação
não vira supervisão de graça, e vice-versa. `setx` só vale a partir do
**próximo** Prompt de Comando aberto depois de rodar isso, então feche e
suba os dois programas de novo. A autorização é por identidade de quem
logou (passo de login do programa), nunca por senha compartilhada da seção.

### Instalação para quem cobre a categoria FUTEBOL (Drive próprio, layout diferente)

**Só se aplica à instalação da Responsável B.** Ela organiza o Drive dela sozinha,
separado do Drive do Marketing, e a estrutura de pastas de lá é diferente da
que o resto do guia pressupõe: `[pasta do influenciador] / DIVULGAÇÕES / MM.
MÊS`, sem bet, sem ano, sem pasta de dia. Isso é um terceiro **layout** de
pastas (`futebol`), que existe ao lado dos dois de sempre (`teste` e
`marketing`). Continue seguindo o resto deste guia normalmente; só troque o
que está aqui.

**a) Ligue o layout, de forma que sobreviva a reiniciar o computador:**

```
setx LAYOUT_PASTAS_DRIVE futebol
```

`setx` grava a variável para sempre nesta máquina, mas só vale a partir do
**próximo** Prompt de Comando aberto depois de rodar isso; feche e abra de
novo antes de continuar. Sem essa variável, o programa volta ao layout
`teste` de sempre, que não serve para o Drive dela.

**b) O mapa @ → pasta.** As pastas dela são por apelido ou nome de página
("Rafa Lira", "Central do Timão"), sem relação com o @ do Instagram, e a
Dados_influ só guarda o @. Por isso existe um arquivo próprio,
`teste_watch_folder\pasta_por_handle_futebol.json`, ligando cada @ ao nome
exato da pasta dela no Drive. **Ele já vem pronto dentro do zip de
instalação** (voltou a vir junto em 17/09/2026, por simplicidade; antes
precisava ser copiado à parte), com o seed de 21 entradas construído em
12/09/2026. Confira que ele chegou em `teste_watch_folder` mesmo assim; se
faltar, peça a quem administra o programa. Um @ sem entrada nesse mapa não
trava o programa nem inventa pasta nova: a linha fica marcada `FALTA PASTA
NO DRIVE` na fila, explicando o que falta, e o vídeo já baixado naquela
tentativa se perde (a chamada ao Instagram não volta). Hoje falta **Renata
Saporito** nesse mapa, sem @ confirmado ainda.

**c) Enquanto ela estiver testando localmente (antes do servidor):** não
aponte para o Drive real dela ainda. Use uma pasta de teste que já imita a
estrutura dela (feita pelo próprio programa em 12/09/2026, dentro da pasta de
teste padrão do projeto: `TESTE_LAYOUT_FUTEBOL_SCRIPT_12set`). Ponha o id
dessa pasta em `teste_watch_folder\drive_teste_pasta_raiz_id.txt`. A pasta de
teste genérica do resto do time (a que já vem pronta na cópia) **não serve**
para ensaiar este layout: a estrutura dela é bet/ano/mês, bem diferente da
dela.

**d) Monitoramento e Calendário continuam de teste por enquanto** (decisão
revista em 15/09/2026: este guia dizia antes que as duas usariam os ids reais
e compartilhados assim que ela testasse; não é mais o plano). Ela escreve nas
CÓPIAS DE TESTE (`monitoramento_teste_id.txt` e `calendario_teste_id.txt`, em
`teste_watch_folder`, já preenchidas na cópia do programa), não nas reais. A
planilha de Calendário de teste foi povoada com os dados reais da aba
SET.26 do Calendário oficial do Marketing (946 linhas, copiadas em
15/09/2026), para o que ela testa refletir a realidade deles mesmo a escrita
caindo numa cópia segura, sem risco de mexer no que é real. **Só SET.26 foi
copiada até agora**, as outras abas (DEZ.25 a AGO.26 e OUT.26 a DEZ.26)
continuam só com o que o uso normal do programa em teste gravou nelas; peça
a quem administra se precisar de outro mês copiado também. Ela precisa ter
permissão de **edição** nas
DUAS planilhas de teste, mesma exigência do passo 7.5, só que na cópia em vez
da real, senão os tokens dela (passo 7.4) sobem sem conseguir escrever. O
Drive continua a decisão à parte do item (c) acima: quando for para o Drive
real dela, é decisão de quando, não muda a Monitoramento nem o Calendário.

**e) A conta do Instagram dela ainda não foi definida** (12/09/2026). Sem
isso, os passos 7.1 e 7.2 ficam pendentes para esta instalação especificamente;
confirme antes de seguir com o login do Firefox.

---

## Passo 8: conferir tudo

```
py verificar_ambiente.py
```

Ele confere cinco camadas e marca cada item com `ok`, `aviso` ou `FALTA`:

| camada | o que confere |
|---|---|
| pacotes Python | os 19, comparando com o `requirements.txt` |
| programas externos | ffmpeg, ffprobe, Tesseract e os idiomas dele |
| serviços | Ollama de pé e o `minicpm-v` baixado |
| configuração | os cinco identificadores, os tokens, **a conta do Instagram que está valendo**, **o modo de escrita (teste ou real)**, o registro de contratos, o cache de perfis, a cópia da Monitoramento e as cinco chaves do login |
| manutenção | se as bibliotecas de download envelheceram, e o espaço em disco |

**`FALTA` impede o uso. `aviso` não impede.**

Duas coisas para olhar na saída:

- **A linha `conta do Instagram`.** Se aparecer o nome de outra pessoa, pare e
  volte ao passo 7.2.
- **A linha `login do programa`.** Se disser que faltam chaves, o programa vai
  abrir **sem pedir login**. Peça o `secrets.toml` completo, que tem cinco
  chaves.
- **A linha `modo de escrita`.** Se disser `REAL` e você não esperava isso,
  pare: alguém ligou a escrita nos sistemas verdadeiros do Marketing nesta
  máquina. Ver o Anexo no fim deste guia.

Numa máquina nova é normal aparecer um aviso de `yt-dlp` velho. Resolva no passo
11.

**Mande essa saída para quem está te ajudando.** É a forma mais rápida de saber
o que falta.

---

## Passo 9: rodar os testes

São 74 arquivos, e é a única prova de que a instalação funciona de verdade, e
não apenas está completa. Eles não gastam chamada ao Instagram.

```
for %f in (testes\*.py) do py "%f"
```

Cada um imprime `PASSOU` ou lista as falhas.

---

## Passo 10: abrir o programa

São **dois programas, e os dois precisam estar de pé**. Duas formas, o
resultado é o mesmo:

**Com atalho na Área de Trabalho (mais fácil, criado em 09/09/2026):** rode
uma vez, só nesta máquina:

```
powershell -ExecutionPolicy Bypass -File ferramentas\criar_atalho_area_de_trabalho.ps1
```

Isso cria o atalho **"Abrir Monitoramento de Influenciadores"** na Área de
Trabalho. Um clique nele sobe os dois programas na ordem certa. O ícone é um
padrão do Windows; troque à vontade com botão direito > Propriedades >
Alterar ícone.

**Sem atalho, dois cliques na pasta do programa, nesta ordem:**

1. **`iniciar_trabalhador.bat`** — é quem baixa e analisa. **Deixe essa janela
   aberta.** Fechar ela para o trabalho.
2. **`iniciar_validacao_influenciadores.bat`** — abre a tela no navegador.

Se a tela abrir e nada acontecer quando você clicar em Baixar, o motivo mais
provável é o processo não estar de pé.

**Se o Windows Terminal for o terminal padrão desta máquina**, as duas janelas
podem aparecer como duas ABAS da mesma janela, em vez de duas janelas
separadas. Continua seguro: fechar uma aba encerra só aquele processo, não os
dois. O título de cada aba continua dizendo o que é e se pode fechar.

### As quatro telas

Até 14/09/2026 eram cinco, com uma "Validação Regulatória" separada para
escolher o que analisar. Ela saiu do menu porque a análise já acontece
sozinha assim que o vídeo termina de baixar; o pouco que sobrava de
essencial (acompanhar quantos vídeos estão sendo analisados) migrou pra
dentro do Monitoramento. **"Tirar da análise", "devolver" e "tentar de
novo" chegaram a migrar também, e saíram de novo em 15/09/2026**: vídeo
analisado por engano não é problema nenhum, fica lá com veredito, e quem
quiser o vídeo certo usa o "Baixar de novo" de Downloads.

| tela | o que faz |
|---|---|
| Downloads | cola o link, baixa, organiza no Drive e cria a linha na Monitoramento (reabrir um sucesso pra baixar de novo exige supervisão ou coordenação) |
| Monitoramento | mostra as linhas e acompanha quantos vídeos estão sendo analisados |
| Financeiro | escopo contra entrega, cronograma pro WhatsApp do Marketing e o histórico de entregas |
| Cadastro | consulta ao cadastro, com correção, inclusão e exclusão controladas (exige supervisão ou coordenação) |

Se a barra lateral aparecer com **nome de arquivo** em vez desses títulos, você
subiu pelo arquivo errado. O comando certo é `py -m streamlit run painel.py`.

**Duas colunas da planilha continuam sendo trabalho manual:** `CRONOGRAMA`
(`SIM`/`NÃO`) e `PAGAMENTO` (`Realizado`/`Pendente`), linha por linha. O programa
lê as duas e mostra, mas não escreve nenhuma.

---

## Passo 11: atualizar a biblioteca que baixa vídeo

Faça isto no primeiro dia. A versão que veio no `requirements.txt` é de
04/07/2026, e o programa considera essa peça velha depois de 45 dias.

1. **Feche a janela do processo** e espere um minuto.
2. Recarregue a tela de Downloads, abra **Cuidar das bibliotecas de download** e
   clique em **Atualizar agora**.
3. **Copie e guarde o comando de volta** que ele mostra, antes de fechar a
   mensagem. É como desfazer, se a versão nova der problema.
4. Suba o processo de novo e baixe um Reel para confirmar.

Pelo Prompt de Comando o equivalente é:

```
py -m pip install --upgrade yt-dlp
py testes\teste_download_em_duas_etapas.py
```

---

## Depois de instalado: o que fazer no dia a dia

**Reinicie os dois programas quando alguém mexer no código.** A tela não
recarrega sozinha, de propósito. Se não reiniciar, você está usando a versão
antiga.

**Encerre o processo antes de mexer em arquivo.** Ele carrega o código na
memória quando sobe.

**Olhe a tela de Downloads.** É lá que aparece o aviso de biblioteca velha e o de
download quebrado. Não existe e-mail nem alerta automático: o aviso só chega a
quem abre a tela. Para ver o mesmo quadro pelo Prompt de Comando:

```
py baixadores.py
```

**Se aparecer faixa vermelha dizendo que o download pode ter parado**, pare de
insistir: provavelmente o Instagram mudou a página e a biblioteca não entende
mais. Faça o passo 11 e, enquanto isso, use o **envio de arquivo** na tela de
Downloads: baixe o vídeo à mão e suba por ali. O programa faz todo o resto
igual, e esse caminho não depende de nenhuma biblioteca de download.

---

## Quanto tempo leva

Cerca de **110 segundos por vídeo**, com dois processos ao mesmo tempo, numa
máquina sem placa de vídeo dedicada. Com 8 a 10 influenciadores e 2 stories cada
são 16 a 20 vídeos, ou **29 a 37 minutos** de máquina ocupada. A máquina fica
lenta nesse período.

Se faltar memória, baixe `TRABALHADORES_PADRAO` de 2 para 1 no
`pipeline_influenciadores.py`. Libera memória e custa velocidade.

**O Instagram tem teto por conta**, mostrado na tela de Downloads: **20 por dia
de segunda a sexta, 30 no sábado e domingo** (o de fim de semana existe desde
12/09/2026, para o plantão em que uma pessoa só cobre o que os outros dias seis
contas dividem). E os links saem espaçados de propósito: **20 a 45 segundos**
entre um link e o outro dentro da mesma rodada (era 30 a 180 até 11/09/2026), e
**3 a 7 minutos entre rodadas de 3 links, só quando a rodada anterior bateu
nesse limite** — colar um link isolado no meio do trabalho não paga mais essa
pausa longa. **Isso não é lentidão, é o que evita o bloqueio da conta.**

---

## Se der errado

| o que você vê | o que fazer |
|---|---|
| `py` não é reconhecido | reinstale o Python marcando `Add python.exe to PATH` (passo 1) |
| erro instalando pacote, falando de "wheel" ou "build" | confira `py -V`. Tem que ser 3.14 |
| a tela diz que não achou a planilha | rode `py verificar_ambiente.py` e veja qual identificador está faltando |
| erro de permissão ao gravar no Drive ou na planilha | passo 7.5: confirme que a SUA conta Google tem edição no arquivo, não só visualização |
| não achei o client OAuth do projeto COAF | falta o `oauth_client.json` em `_drive_credenciais` (passo 7.3). Peça a quem administra |
| no passo 7.4, `WSGITimeoutError` no Prompt de Comando, ou o navegador mostra `ERR_CONNECTION_REFUSED` em `localhost` depois de clicar em Permitir | não é rede nem Firewall: é antivírus/EDR corporativo sondando a porta local antes do navegador voltar com a resposta. Corrigido desde a versão 16 (16/09/2026); confirme que `_drive_credenciais\autorizar_local.py` chegou junto com a pasta do programa e tente de novo |
| todo vídeo fica em "Ciclo A CONFIRMAR" | falta a pasta `contexto\Auditoria-MKT de influencers`. Peça a quem administra |
| o fechamento avisa que ficou "só no arquivo local desta máquina" | falta o `fechamentos_planilha_id.txt`. Peça a quem administra |
| o registro diz "Calendário não preenchido" | rode `py verificar_ambiente.py` e veja a linha do Calendário de Divulgações. Sem `calendario_teste_id.txt` em `teste_watch_folder`, o programa não tem onde escrever |
| o programa abre sem pedir login | falta chave no `secrets.toml`. Peça o arquivo completo, com as cinco |
| a barra lateral mostra nome de arquivo | subiu pelo arquivo errado. Use `py -m streamlit run painel.py` |
| `Ainda não conheço o perfil @alguém` | cole um Reel ou post desse perfil, que é como o programa aprende o número dele |
| `FALTA PASTA NO DRIVE`, no layout futebol | o @ não está em `teste_watch_folder\pasta_por_handle_futebol.json`. Adicione a entrada com o nome exato da pasta dela no Drive |
| `Só uma conta por dia por máquina` | outra conta já falou com o Instagram nesta máquina hoje. É proteção, não defeito. Espere o dia virar |
| o botão de atualizar biblioteca está cinza | feche a janela do processo e espere um minuto |
| `verificar_ambiente.py` não acha o tesseract, mas ele está instalado | instalação sem privilégio de administrador costuma cair em `%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe` (sem a pasta `Programs` no meio), fora dos lugares que a busca automática confere. Ache o `tesseract-uninstall.exe` (Aplicativos e Recursos do Windows mostra o caminho, mesmo sem listar o programa) e aponte pro `tesseract.exe` do mesmo diretório: `setx TESSERACT_CMD "C:\caminho\tesseract.exe"`, feche e abra o Prompt de novo. Aconteceu com a Responsável A (16/09/2026) e a Responsável B (17/09/2026) |
| faixa vermelha dizendo que o download pode ter parado | passo 11, e use o envio de arquivo enquanto isso |
| a análise demora | é esperado. Veja **Quanto tempo leva** |

---

## Anexo: ligar o modo real (escrever de verdade no Marketing)

**Só se aplica quando já foi combinado com o Marketing** que esta instalação
específica vai escrever de verdade na Monitoramento e no Drive deles, e não
só na cópia de teste. Numa máquina nova comum, pule este anexo: o programa
funciona inteiro em modo teste, sem nada disto.

**Nunca faça isto na máquina do próprio auditor.** É o que liga a escrita de
verdade, e ligar sem querer numa máquina que só deveria testar escreveria na
planilha e no Drive reais do Marketing por engano.

Por padrão, o programa escreve só na cópia de teste, sempre. Para ligar o
modo real, crie a pasta `marketing_producao` dentro de `producao\analises` e
coloque três arquivos dentro, faltando qualquer um o programa continua em
teste, sem avisar:

| arquivo | conteúdo |
|---|---|
| `monitoramento_id.txt` | o id da planilha Monitoramento REAL (o trecho do endereço entre `/d/` e `/edit`) |
| `drive_pasta_raiz_id.txt` | o id da pasta REAL do Drive onde os vídeos vão ser organizados (o trecho depois de `/folders/`) |
| `AUTORIZO_ESCREVER_NOS_SISTEMAS_REAIS_DO_MARKETING.txt` | pode ficar vazio; é a existência dele que conta |
| `calendario_id.txt` | o id do CALENDÁRIO GERAL DIVULGAÇÕES real. Só este é opcional: sem ele, o resto vai para o sistema real e o Calendário continua na cópia de teste |

**Os dois ids precisam vir de quem administra a Monitoramento e o Drive do
Marketing, confirmados para esta instalação.** Não reaproveite um id só
porque ele apareceu num cruzamento de leitura antigo: leitura autorizada e
escrita autorizada são decisões diferentes.

**Exceção, só na instalação da Responsável B (layout futebol):** o
`drive_pasta_raiz_id.txt` é o id do Drive **dela**, não da pasta de vídeos do
Marketing (ver "Instalação para quem cobre FUTEBOL", no passo 7). O
`monitoramento_id.txt` e o `calendario_id.txt` continuam sendo os mesmos ids
reais e compartilhados de sempre. A autorização, mesmo assim, precisa vir de
quem decide isso para o Drive dela, do mesmo jeito que o resto deste anexo
pede confirmação e não reaproveita id de leitura antiga.

Depois de criar os três, rode `py verificar_ambiente.py` e confira a linha
`modo de escrita`: tem que dizer `REAL`. Ver `fluxo_downloads.modo_real_autorizado`
e `testes\teste_modo_real_autorizado.py` para o mecanismo completo.

---

## Anexo: só baixar, sem instalar o programa inteiro

Existe uma peça separada em `baixador_local`, com o atalho `Baixar.bat`. Ela
baixa vídeo usando a sessão do Firefox da própria pessoa e **não tem credencial
nenhuma da auditoria dentro**.

Para quem só precisa baixar, bastam os passos 1, 3 e 7, mais:

```
py -m pip install yt-dlp
```
