# Instalar o Monitoramento de Influenciadores no GCP

**Versão 3 · 22/09/2026.** A versão 2, do mesmo dia, tinha revertido a
versão 1 (18/09) para "a VM baixa do Instagram", quando o Marketing decidiu
usar uma conta só para as seis pessoas. Isso mudou de novo, algumas horas
depois: **a conta única fica só para DUAS pessoas** (não seis), e essas
duas continuam baixando cada uma da própria máquina, não pela VM. **A VM
volta a não baixar de ninguém**, igual à versão 1. Ver seção 0 (o porquê) e
a seção 5 (agora sobre as duas pessoas, não mais sobre a VM). Substitui,
para este destino, os checklists anteriores de subida em servidor
(`Checklist_Subir_App_No_Servidor.html`, 26/08, desatualizado).

**Não confundir com `INSTALAR.md`**, que continua valendo para instalação
individual, uma pessoa por notebook: é o caso da Responsável B (Futebol, conta
própria) e das seis pessoas do Marketing, sejam as quatro com conta
individual ou a dupla que compartilha uma (ver seção 5). Este guia é para a
instalação **central** na VM, que só entra para analisar e organizar,
atendendo as duas instalações lado a lado (Marketing e Futebol, ver seção
4). Nenhuma das seis pessoas do Marketing, nem a Responsável B, baixa pela VM.

**Para quem administra a VM e a rede** (TI / Cibersegurança). Decisões de
identidade, rede e permissão do Marketing continuam precisando de quem
decide por essas áreas, marcadas abaixo.

---

## 0. O que já está decidido, e não deve ser reaberto

| decisão | por quê |
|---|---|
| **Duas instalações lado a lado na mesma VM**, uma por layout de Drive (Marketing e Futebol), não uma instância única para as duas | o layout do Drive é uma variável lida uma vez quando o processo sobe; misturar as duas em um processo só mandaria vídeo para a pasta errada |
| **Sem placa de vídeo.** Não compre GPU para isto | a análise já é CPU (medido: 110s por vídeo com CPU, o próprio motor confirma "Using CPU, much faster with GPU" só como aviso, não como requisito) |

**"A VM não baixa do Instagram" VOLTOU A VALER, depois de um dia inteiro de
vaivém, e fica registrado o porquê para não reabrir de novo.**

Passo a passo do que mudou, tudo em 22/09/2026, no mesmo dia:

1. Descoberto: seis contas numa máquina só travam a partir da segunda no
   mesmo dia ("uma conta por dia por máquina", regra criada depois do
   bloqueio real de 27/08). Baixar de seis contas na mesma VM não fecharia.
2. O Marketing decidiu usar UMA conta só para as seis pessoas, para não
   depender de criar conta nova por pessoa. Isso trocou o problema: uma
   conta só, acessada por SEIS máquinas físicas diferentes, é o padrão de
   "muitos dispositivos" que a investigação (ver `COMECE_AQUI.md` e a
   memória do projeto) aponta como causa provável do loop de captcha que
   essa conta já vinha apresentando. A saída proposta então foi a VM
   centralizar essa conta, como único ponto de acesso.
3. **Revisto de novo, mesmo dia:** a conta única não vai ser usada pelas
   seis pessoas, só por DUAS. As outras quatro voltam a ter conta própria,
   cada uma. Com só duas máquinas na mesma conta (não seis), o Marketing
   decidiu manter as duas baixando cada uma da própria máquina, sem
   centralizar na VM. **Isso tira o motivo de a VM precisar falar com o
   Instagram**: nem as quatro contas individuais, nem a dupla compartilhada,
   passam por ela.

**A VM volta a servir só para analisar e organizar**, para as duas
instalações (Marketing e Futebol), igual à versão 1 deste guia. A dupla que
compartilha conta continua exposta a um risco menor do mesmo tipo (dois
dispositivos, não seis, na mesma conta), mitigado pela serialização entre
máquinas já construída (`efa32b2`), configurada entre as duas máquinas
delas, sem relação com a VM. Ver a seção 5.

---

## 1. Provisionar a VM

**FAÇA: Compute Engine, Windows Server, mínimo 8 vCPU / 16 GB de RAM / 60 GB de disco livre.**
Evita subdimensionar: a análise roda 2 vídeos ao mesmo tempo, cada um usando
ffmpeg, OCR e o modelo de visão junto; medido em máquina real, 3,5 GB de RAM
livre já é pouco com o programa de pé. Recomendo 100 GB de disco (SSD),
para sobrar margem além do mínimo.

**FAÇA: continue em Windows, não migre para Linux nesta subida.**
Evita reescrever e re-testar toda a camada de sistema (`.bat`, PowerShell,
Tarefa Agendada do Windows) no mesmo momento em que já se muda a hospedagem.
O código Python roda nos dois sistemas, mas o encanamento de subida (scripts
`.bat`, `schtasks`) é só Windows hoje.

**FAÇA: disco persistente separado para o estado do programa**
(`teste_watch_folder`, cache, log), não o disco de boot da VM.
Evita perder tudo se a VM for recriada por manutenção do GCP; o disco de
dados sobrevive e é remontado numa VM nova.

**FAÇA: snapshot programado do disco de dados.**
Evita depender só da robustez da VM: os identificadores e o cache locais
não estão em nenhum outro lugar (a evidência em si está no Google Sheets,
mas o estado local que sabe operar não tem outra cópia).

---

## 2. Sistema e dependências (dentro da VM)

**FAÇA: rode `verificar_ambiente.py` como primeira coisa depois de instalar.**
Evita descobrir peça faltando no meio da configuração; ele confere pacotes,
programas externos, Ollama e os cinco identificadores de uma vez.

**FAÇA: instale nesta ordem, e confirme cada um antes do próximo:**
Python 3.14 (marcando `Add python.exe to PATH`) → Tesseract OCR **pelo
instalador oficial, com o pacote de português marcado** → ffmpeg (`winget
install Gyan.FFmpeg`) → Ollama + `ollama pull minicpm-v`.
**Evita** duas armadilhas já medidas: Tesseract por `winget` não traz
português (o programa passaria a não ler duas das três frases obrigatórias
do Ministério da Fazenda); e a versão de Python errada quebra a instalação
dos pacotes com erro de "wheel".

**FAÇA: confirme que a rede da VM alcança `pypi.org`, `ollama.com` e
`github.com` antes de instalar.**
Evita a instalação parar no meio por proxy/firewall do GCP bloqueando esses
domínios, sem aviso claro de qual é a causa.

---

## 3. Rede, domínio e login

**FAÇA: reserve um IP externo fixo e um domínio (ou subdomínio) para a VM,
com certificado válido (Google-managed ou outro).**
Evita a trava que o próprio programa já tem: login por OAuth só aceita
retorno em HTTPS quando o destino não é `localhost`. Sem domínio e
certificado, a tela nunca libera login para mais de uma pessoa.

**FAÇA: decida entre Google e Microsoft Entra ID para o login do
programa** (decisão de Cibersegurança/TI, não técnica).
**Evita** duas coisas ruins: usar o login de teste (Google, pessoal) como
produção por inércia, e criar um segundo cadastro de aplicativo isolado se
a empresa já estiver com um projeto de SSO em andamento.

**FAÇA: só abra a porta 443 (HTTPS) para fora da VM.**
Evita expor qualquer coisa relacionada a Instagram ou a portas internas dos
dois processos; a VM não precisa receber tráfego de mais nada de fora.

**FAÇA: decida com o TI como as DUAS telas (Marketing e Futebol) vão
aparecer sob HTTPS** — dois subdomínios (recomendado, mais simples de
configurar certificado e roteamento) ou um proxy reverso por caminho.
**Evita** expor as duas telas em portas diferentes sem certificado, o que
obrigaria cada pessoa a aceitar aviso de site não seguro.

---

## 4. As duas instalações, lado a lado

**FAÇA: duas pastas separadas na VM** (ex.: `C:\Auditoria\marketing\` e
`C:\Auditoria\futebol\`), cada uma com sua própria cópia completa do
programa.
Evita o problema já identificado: o layout do Drive é uma variável de
ambiente lida uma vez por processo; instâncias separadas garantem que cada
uma sempre usa o layout certo, sem depender de reconfigurar nada em tempo
de execução.

**FAÇA: defina a variável de layout DENTRO do `.bat` de cada instalação**
(`set LAYOUT_PASTAS_DRIVE=marketing` / `set LAYOUT_PASTAS_DRIVE=futebol`
antes de chamar o Python), **nunca com `setx`**.
Evita o erro real de usar `setx`: ele grava no perfil do Windows inteiro, e
a segunda instalação sobrescreveria a variável da primeira, já que as duas
rodam na mesma máquina.

**FAÇA: uma porta própria do Streamlit para cada instalação**
(ex.: 8501 e 8502).
Evita as duas telas disputarem a mesma porta.

**FAÇA: quatro tarefas agendadas no Windows** (trabalhador + painel, vezes
duas instalações), cada uma rodando sob a conta certa, para voltar sozinho
depois de reiniciar.
Evita o defeito já visto: reinício sem tarefa agendada deixa os processos
parados até alguém notar.

**JÁ FEITO, não precisa reconstruir:** a trava contra as duas instalações
sobrescreverem a mesma linha da Monitoramento ao mesmo tempo
(`_caminho_trava_entre_instalacoes` e a releitura em
`registrar_na_monitoramento`, corrigidas e testadas em 18/09/2026). Ela
funciona exatamente neste cenário (duas instalações, mesma máquina, mesma
planilha), porque o arquivo de trava fica em `%ProgramData%`, comum às duas.

**DEFINIDO EM 22/09/2026: quem é supervisão e coordenação em cada
instalação.** Corrigir Cadastro e reabrir download aceitam QUALQUER um dos
dois papéis; o envio manual de arquivo (baixar à mão quando o automático
falha) exige especificamente **supervisão**, porque no código essa ação
está ligada a quem aprova pagamento do ciclo. Por isso as pessoas abaixo
entram nos DOIS papéis, em vez de só um: as três (Responsável C, Responsável D e
Responsável B) precisam do envio manual, não só de corrigir cadastro.

| instalação | e-mails (mesmos nos dois papéis) |
|---|---|
| Marketing | `responsavel.c@empresa.com,responsavel.d@empresa.com` |
| Futebol | `responsavel.b@empresa.com` |

**Não confundir com quem faz login para usar a tela no dia a dia**: as seis
pessoas do Marketing que só baixam, e a própria Responsável A, continuam usando o
programa normalmente sem estar em nenhuma das duas listas; elas só não
têm acesso às ações que exigem esses papéis.

**FAÇA: defina as duas variáveis DENTRO do `.bat` de cada instalação**,
com os e-mails da tabela acima:

```
:: dentro do .bat da instalação do Marketing
set EMAILS_SUPERVISAO=responsavel.c@empresa.com,responsavel.d@empresa.com
set EMAILS_COORDENACAO=responsavel.c@empresa.com,responsavel.d@empresa.com
```

```
:: dentro do .bat da instalação do Futebol
set EMAILS_SUPERVISAO=responsavel.b@empresa.com
set EMAILS_COORDENACAO=responsavel.b@empresa.com
```

**Nunca com `setx`**, pelo mesmo motivo do layout: `setx` grava no perfil do
Windows inteiro, e a segunda instalação sobrescreveria a configuração da
primeira.

**JÁ PRONTOS, desde 24/09/2026:** `iniciar_trabalhador_marketing.bat`,
`iniciar_painel_marketing.bat`, `iniciar_trabalhador_futebol.bat` e
`iniciar_painel_futebol.bat`, na raiz de `producao\analises`, já com o
layout, os e-mails da tabela acima e a porta (8501/8502) escritos dentro,
para não depender de digitar isso a mão no dia da subida. Cada instalação
usa o par que é dela (copiam junto com o resto da pasta). O comando de
`schtasks` para as quatro tarefas agendadas está no resumo final de
`preparar_servidor.ps1`.

---

## 5. A dupla que compartilha conta (reescrita em 22/09/2026, não é mais sobre a VM)

**Não é assunto desta VM.** As duas pessoas continuam com instalação local,
uma por notebook, como manda `INSTALAR.md`. Fica aqui só porque nasceu da
mesma investigação que gerou este guia, e vale registrar antes que se perca
entre uma versão e outra deste documento.

**FAÇA: crie um perfil NOVO do Firefox em cada uma das duas máquinas**, sem
usar o perfil que já foi usado no dia a dia da conta até aqui, e logue a
conta compartilhada nele pela primeira vez ali. Perfil do Firefox não pede
conta Google nem conta nenhuma para existir (`about:profiles`, ou
`firefox.exe -P`).
**Evita** herdar o histórico de anos de uso por várias pessoas, que é a
causa mais provável já investigada para o loop de "não sou um robô" que
essa conta vem apresentando (ver a memória do projeto). Um perfil sem esse
histórico foi o que já destravou o acesso da Responsável A em 22/09.

**FAÇA: confirme `teste_watch_folder\conta_instagram.txt`** com o @ da
conta compartilhada, nas duas instalações.
**Evita** o programa cair no @ fixo do código por engano
(`candyboxconfeitaria`, a conta de teste) e a sessão do Firefox ser tratada
como anônima sem avisar (foi o que causou o primeiro bloqueio real desta
conta, em 25/08/2026).

**JÁ FEITO, não precisa reconstruir: a serialização entre as duas
máquinas** (`aguardar_vez_da_conta`/`liberar_vez_da_conta`, commit
`efa32b2`) e a pausa compartilhada (`f11c396`). Confirme só que as DUAS
instalações apontam para o mesmo identificador de planilha de estado
(`ABA_ESTADO_INSTAGRAM`), senão cada uma acha que está sozinha com a conta
e a proteção não vale nada.

**ATENÇÃO, risco que fica, mesmo com tudo isso certo:** duas máquinas na
mesma conta é mais seguro que seis, mas não é o mesmo que uma só. A
serialização evita as duas se atropelarem; não evita a Meta continuar
vendo dois dispositivos diferentes na mesma conta, que é o sinal que
aparenta pesar mais nesta investigação. Se puder, no futuro, concentrar em
uma pessoa só, o risco cai de vez; enquanto isso não for possível
operacionalmente, esta seção é a mitigação disponível, não a eliminação do
risco.

---

## 6. Credenciais do Google (Drive e Sheets)

**FAÇA: um único `oauth_client.json`** (o cadastro do programa no Google
Cloud), reaproveitado nas duas instalações.
Evita criar um segundo registro de aplicativo sem necessidade; ele identifica
o programa, não o Drive nem a pessoa.

**FAÇA: gere os tokens de escrita de cada instalação com a conta de quem
vai de fato operar aquele lado** (`autorizar_drive.py`,
`autorizar_drive_escrita_arquivo.py`, `autorizar_sheets_escrita.py`, um de
cada vez, dentro da pasta daquela instalação).
Evita o histórico de edição do Drive e da planilha aparecer no nome de quem
não é responsável por aquele lado.

**FAÇA: confirme com quem administra o Drive e a Monitoramento do Marketing
que a conta usada em cada instalação tem permissão de EDIÇÃO**, não só
leitura, nas pastas e planilhas que vai escrever (decisão do Marketing).
Evita a armadilha que não dá erro na hora: autorizar sem essa permissão só
quebra na primeira tentativa de escrita, depois de tudo parecer certo.

**AVALIE (não obrigatório para esta subida): mover os tokens para o Secret
Manager do GCP em vez de arquivo local.**
Reduz exposição de credencial de escopo amplo num disco de VM; exige mudança
de código para buscar do Secret Manager, hoje não implementada. Registrar
como melhoria, não como bloqueio.

---

## 7. Testes antes de ligar de verdade

**FAÇA: rode os testes nas duas instalações**
(`for %f in (testes\*.py) do py "%f"`; 76 arquivos conferidos em 22/09/2026,
contagem que só tende a crescer, não trave neste número).
Evita subir com um ambiente incompleto; eles não gastam chamada ao
Instagram.

**FAÇA: rode `testar_corrida_entre_maquinas.py` uma vez na VM, contra a
cópia de teste da Monitoramento.**
Prova que a proteção contra escrita simultânea das duas instalações
funciona nesta máquina específica, não só na máquina onde foi
desenvolvida.

**FAÇA: mantenha as duas instalações na Monitoramento e Calendário DE
TESTE até confirmar tudo o resto deste guia.**
Evita ligar escrita real (`marketing_producao\`, ver `INSTALAR.md`) antes de
rede, login e permissão do Marketing estarem certos; sem os três arquivos
daquela pasta, o programa cai em teste sozinho, sem avisar, que é o
comportamento seguro por padrão.

---

## 8. Pendências que não são desta VM, e travam a virada para produção

| pendência | de quem é | trava o quê |
|---|---|---|
| **IP fixo, domínio e certificado HTTPS para a VM** | TI/Cibersegurança | login de mais de uma pessoa, sem isso ninguém além de quem está no console abre a tela (URGENTE, meta de 22/09 é subir até sexta) |
| Entrar na leva de SSO da empresa (Entra ID) | Cibersegurança/TI | só se a empresa quiser SSO único; **não precisa esperar isso pra sexta** |
| Conceder escrita real na pasta do Marketing no Drive | quem administra o Drive do Marketing | ligar modo real |
| Confirmar os ids reais da Monitoramento e do Calendário para esta instalação | quem administra a Monitoramento | ligar modo real |
| Decidir se os tokens migram para Secret Manager | TI/Cibersegurança | só hardening, não bloqueia a subida em teste |

**Sobre os dois primeiros itens, para não travar a meta de sexta à toa:** o
login por Google OAuth com domínio `@empresa.com` **já está pronto e
funcionando** hoje, na instalação local (`acesso.py`, `.streamlit/secrets.toml`
já configurado assim). Não é preciso esperar uma integração formal de SSO
corporativo (Entra ID) para religar o login na VM: basta repetir a mesma
configuração de Google OAuth que já existe, só apontando `redirect_uri` para
o domínio da VM. O único item que de fato bloqueia é o domínio e o
certificado em si; o provedor de login (Google vs. Entra ID) é decisão de
TI, mas não precisa ser a de Entra ID pra destravar sexta-feira.

Este documento cobre a VM. As pendências acima seguem sendo conversa com
outras áreas, e a VM funciona em modo teste, inteira, sem esperar nenhuma
delas.
