# ------------------------------------------------------------------
#  A máquina está pronta para ser o servidor?
#
#  CONFERE E NÃO MEXE EM NADA, a não ser que você mande com -Aplicar.
#  Mesmo padrão do verificar_ambiente.py: primeiro diz o que está errado,
#  depois você decide.
#
#  POR QUE ESTE ARQUIVO EXISTE (30/08/2026)
#
#  O programa vai sair da máquina de uma pessoa para uma máquina que fica
#  ligada rodando trabalho de cinco. Se essa máquina for um notebook, e tudo
#  indica que será, existem três jeitos de ele parar sem ninguém perceber:
#
#     suspende por inatividade      o trabalhador morre no meio de um lote
#     alguém fecha a tampa          idem, e é o gesto mais natural do mundo
#     o Windows reinicia sozinho    os dois programas não voltam
#
#  Nenhum desses dá erro na tela. A fila fica parada, os vídeos não são
#  analisados, e a pessoa conclui que o programa está quebrado.
#
#  ISTO É PARA WINDOWS. Se o servidor for Linux, as conferências continuam
#  valendo (não dormir, voltar sozinho, disco, memória), mas os comandos são
#  outros. O verificador de ambiente em Python funciona nos dois.
#
#  Uso:
#      powershell -ExecutionPolicy Bypass -File preparar_servidor.ps1
#      powershell -ExecutionPolicy Bypass -File preparar_servidor.ps1 -Aplicar
# ------------------------------------------------------------------

param(
    [switch]$Aplicar
)

$ErrorActionPreference = "Continue"
$PASTA = Split-Path -Parent $MyInvocation.MyCommand.Path

# Exigências, com o porquê de cada número. Servem também como lista do que
# pedir, se for o caso de conseguir uma máquina melhor.
$MIN_NUCLEOS  = 8     # a análise roda 2 vídeos ao mesmo tempo, e cada um usa
                      # ffmpeg, OCR e o modelo de visão
$MIN_MEMORIA  = 16    # GB. O modelo de visão sozinho ocupa alguns GB, e são
                      # 2 processos de análise além da tela e do trabalhador
$MIN_DISCO    = 60    # GB livres. Modelo de visão ~6 GB, vídeos de passagem,
                      # e margem para o disco não encher no meio de um lote

$problemas = @()
$avisos    = @()
$acoes     = @()

function Titulo($t) {
    Write-Host ""
    Write-Host "--- $t ---" -ForegroundColor Cyan
}
function Ok($t, $d = "")      { Write-Host ("[  ok  ] {0,-38} {1}" -f $t, $d) }
function Falta($t, $d = "")   { Write-Host ("[ FALTA] {0,-38} {1}" -f $t, $d) -ForegroundColor Red;    $script:problemas += "$t. $d" }
function Aviso($t, $d = "")   { Write-Host ("[ aviso] {0,-38} {1}" -f $t, $d) -ForegroundColor Yellow; $script:avisos    += "$t. $d" }

$souAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host "==========================================================================="
Write-Host "  A máquina está pronta para ser o servidor?"
Write-Host "  $(if ($Aplicar) { 'MODO APLICAR: vai alterar configuração' } else { 'Só conferindo, nada será alterado' })"
Write-Host "==========================================================================="

# ------------------------------------------------------------------
Titulo "A máquina"
# ------------------------------------------------------------------
$cs  = Get-CimInstance Win32_ComputerSystem
$os  = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1

Write-Host ("         {0} {1}" -f $cs.Manufacturer, $cs.Model)
Write-Host ("         {0}" -f $os.Caption)
Write-Host ("         {0}" -f $cpu.Name.Trim())

$nucleos = [int]$cpu.NumberOfLogicalProcessors
if ($nucleos -ge $MIN_NUCLEOS) {
    Ok "processadores" "$nucleos (mínimo $MIN_NUCLEOS)"
} else {
    Falta "processadores" "$nucleos, e o mínimo é ${MIN_NUCLEOS}: a análise roda 2 vídeos ao mesmo tempo"
}

$memoria = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
if ($memoria -ge ($MIN_MEMORIA - 0.5)) {
    Ok "memória" "$memoria GB (mínimo $MIN_MEMORIA)"
} else {
    Falta "memória" "$memoria GB, e o mínimo é $MIN_MEMORIA GB"
}

$disco = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$($env:SystemDrive)'"
$livres = [math]::Round($disco.FreeSpace / 1GB, 0)
if ($livres -ge $MIN_DISCO) {
    Ok "disco livre" "$livres GB (mínimo $MIN_DISCO)"
} else {
    Falta "disco livre" "$livres GB, e o mínimo é $MIN_DISCO GB"
}

$bateria = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
if ($bateria) {
    Write-Host ""
    Write-Host "         É um notebook. As três conferências abaixo existem por causa disso." -ForegroundColor Yellow
}

# ------------------------------------------------------------------
Titulo "O que faz a máquina parar sozinha"
# ------------------------------------------------------------------
function LerEnergia($guidConfig) {
    $texto = (powercfg /query SCHEME_CURRENT SUB_SLEEP $guidConfig 2>&1 | Out-String)
    if ($texto -match '(?ms)Correntes Alternadas Atuais:\s*0x([0-9a-f]+)') { return [Convert]::ToInt32($Matches[1], 16) }
    if ($texto -match '(?ms)AC Power Setting Index:\s*0x([0-9a-f]+)')      { return [Convert]::ToInt32($Matches[1], 16) }
    return $null
}

$suspender = LerEnergia "STANDBYIDLE"
if ($suspender -eq 0) {
    Ok "suspender por inatividade" "desligado, que é o certo"
} elseif ($null -eq $suspender) {
    Aviso "suspender por inatividade" "não consegui ler; confira à mão em Configurações de energia"
} else {
    Falta "suspender por inatividade" "suspende após $([math]::Round($suspender/60)) min na tomada"
    $acoes += "powercfg /change standby-timeout-ac 0"
}

$hibernar = LerEnergia "HIBERNATEIDLE"
if ($hibernar -eq 0) {
    Ok "hibernar por inatividade" "desligado, que é o certo"
} elseif ($null -eq $hibernar) {
    Aviso "hibernar por inatividade" "não consegui ler"
} else {
    Falta "hibernar por inatividade" "hiberna após $([math]::Round($hibernar/60)) min na tomada"
    $acoes += "powercfg /change hibernate-timeout-ac 0"
}

$monitor = (powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE 2>&1 | Out-String)
if ($monitor -match '(?ms)Correntes Alternadas Atuais:\s*0x([0-9a-f]+)') {
    $seg = [Convert]::ToInt32($Matches[1], 16)
    # Tela apagando é INOFENSIVO e até desejável: economiza energia e não
    # interrompe processo nenhum. Fica registrado só para ninguém confundir
    # tela apagada com máquina suspensa.
    Ok "desligar a tela" "$(if ($seg -eq 0) { 'nunca' } else { "após $([math]::Round($seg/60)) min" }), e isso não atrapalha"
}

# A ação da tampa vem oculta em muitos notebooks novos.
$LID = "5ca83367-6e45-459f-a27b-476b1d01c936"
$SUB_BOTOES = "4f971e89-eebd-4455-a8de-9e59040e7347"
$tampaTexto = (powercfg /query SCHEME_CURRENT $SUB_BOTOES $LID 2>&1 | Out-String)
$tampaValor = $null
if ($tampaTexto -match '(?ms)Correntes Alternadas Atuais:\s*0x([0-9a-f]+)') { $tampaValor = [Convert]::ToInt32($Matches[1], 16) }
elseif ($tampaTexto -match '(?ms)AC Power Setting Index:\s*0x([0-9a-f]+)')  { $tampaValor = [Convert]::ToInt32($Matches[1], 16) }

$nomesTampa = @("não fazer nada", "suspender", "hibernar", "desligar")
if ($null -eq $tampaValor) {
    Aviso "fechar a tampa" "configuração oculta neste Windows, não consegui ler"
    $acoes += "powercfg /attributes $SUB_BOTOES $LID -ATTRIB_HIDE   (revela a opção; precisa de administrador)"
    $acoes += "powercfg /setacvalueindex SCHEME_CURRENT $SUB_BOTOES $LID 0"
} elseif ($tampaValor -eq 0) {
    Ok "fechar a tampa" "não faz nada, que é o certo"
} else {
    Falta "fechar a tampa" "$($nomesTampa[$tampaValor]). É o gesto mais natural com um notebook parado num canto"
    $acoes += "powercfg /setacvalueindex SCHEME_CURRENT $SUB_BOTOES $LID 0"
}

# ------------------------------------------------------------------
Titulo "Os quatro programas voltam sozinhos?"
# ------------------------------------------------------------------
# Reinício do Windows Update derruba todos. A fila sobrevive, porque está em
# disco e a tarefa interrompida volta para pendente, mas isso só acontece
# quando o trabalhador SOBE de novo. Sem subir sozinho, fica parado até alguém
# perceber.
#
# QUATRO, NÃO DOIS (corrigido em 24/09/2026): desde a decisão de 22/09
# (INSTALAR_NO_GCP.md, seção 4), a VM tem DUAS instalações lado a lado
# (Marketing e Futebol), cada uma com trabalhador e tela próprios. Os nomes
# abaixo têm que casar com os das quatro tarefas criadas pelo comando no
# resumo, no fim deste arquivo.
$TAREFAS = @{
    "AuditoriaInfluenciadores-Marketing-Trabalhador" = "iniciar_trabalhador_marketing.bat"
    "AuditoriaInfluenciadores-Marketing-Tela"         = "iniciar_painel_marketing.bat"
    "AuditoriaInfluenciadores-Futebol-Trabalhador"    = "iniciar_trabalhador_futebol.bat"
    "AuditoriaInfluenciadores-Futebol-Tela"           = "iniciar_painel_futebol.bat"
}
foreach ($nome in $TAREFAS.Keys) {
    $t = Get-ScheduledTask -TaskName $nome -ErrorAction SilentlyContinue
    if ($t) {
        Ok "volta sozinho: $($TAREFAS[$nome])" "tarefa agendada existe"
    } else {
        Falta "volta sozinho: $($TAREFAS[$nome])" "não há tarefa agendada; depois de reiniciar, ninguém sobe"
    }
}

# ------------------------------------------------------------------
Titulo "Rede e acesso"
# ------------------------------------------------------------------
$config = Join-Path $PASTA ".streamlit\config.toml"
$secrets = Join-Path $PASTA ".streamlit\secrets.toml"
if (Test-Path $config) {
    $texto = Get-Content $config -Raw
    $soLocal = $texto -match 'address\s*=\s*"(127\.0\.0\.1|localhost)"'
    $temLogin = Test-Path $secrets
    if ($soLocal -and -not $temLogin) {
        Ok "rede e login" "escuta só a própria máquina, sem login: combinação segura"
        Aviso "para as cinco pessoas usarem" "configure o login ANTES de trocar o endereço, nunca ao contrário"
    } elseif (-not $soLocal -and -not $temLogin) {
        Falta "rede e login" "escuta a rede SEM login: qualquer pessoa que alcance usa as credenciais daqui"
    } elseif ($temLogin) {
        Ok "rede e login" "login configurado"
    }
} else {
    Aviso "configuração da tela" "não achei .streamlit\config.toml nesta pasta"
}

# ------------------------------------------------------------------
Titulo "O resto do ambiente"
# ------------------------------------------------------------------
# Pacotes, ffmpeg, Tesseract com português e Ollama são conferidos pelo
# verificador em Python, que funciona em Windows e em Linux. Não repito aqui
# para não existirem duas listas que divergem.
$verificador = Join-Path $PASTA "verificar_ambiente.py"
if (Test-Path $verificador) {
    Write-Host "         Programas, pacotes e o idioma português do Tesseract são"
    Write-Host "         conferidos por: py verificar_ambiente.py"
} else {
    Aviso "verificar_ambiente.py" "não está nesta pasta"
}

# ------------------------------------------------------------------
if ($Aplicar -and $acoes.Count -gt 0) {
    Titulo "Aplicando"
    if (-not $souAdmin) {
        Write-Host "         Algumas mudanças precisam de administrador. Abra o PowerShell" -ForegroundColor Yellow
        Write-Host "         como administrador e rode de novo." -ForegroundColor Yellow
    }
    powercfg /change standby-timeout-ac 0
    powercfg /change hibernate-timeout-ac 0
    if ($souAdmin) {
        powercfg /attributes $SUB_BOTOES $LID -ATTRIB_HIDE 2>&1 | Out-Null
    }
    powercfg /setacvalueindex SCHEME_CURRENT $SUB_BOTOES $LID 0 2>&1 | Out-Null
    powercfg /setactive SCHEME_CURRENT
    Write-Host "         Energia ajustada. Rode de novo sem -Aplicar para conferir."
    Write-Host ""
    Write-Host "         As tarefas agendadas NÃO são criadas automaticamente: elas"
    Write-Host "         dependem de qual conta vai rodar o programa no servidor, e"
    Write-Host "         errar isso deixa os programas rodando como a pessoa errada."
    Write-Host "         O comando está no resumo abaixo."
}

# ------------------------------------------------------------------
Write-Host ""
Write-Host "==========================================================================="
if ($problemas.Count -eq 0) {
    Write-Host "  Nada impede." -ForegroundColor Green
} else {
    Write-Host "  $($problemas.Count) coisa(s) impedem:" -ForegroundColor Red
    foreach ($p in $problemas) { Write-Host "    - $p" }
}
if ($avisos.Count -gt 0) {
    Write-Host ""
    Write-Host "  $($avisos.Count) aviso(s):" -ForegroundColor Yellow
    foreach ($a in $avisos) { Write-Host "    - $a" }
}
if ($acoes.Count -gt 0 -and -not $Aplicar) {
    Write-Host ""
    Write-Host "  Para corrigir a energia, rode este mesmo arquivo com -Aplicar,"
    Write-Host "  ou execute à mão:"
    foreach ($c in $acoes) { Write-Host "    $c" }
}
Write-Host ""
Write-Host "  Para os quatro programas voltarem sozinhos depois de reiniciar, crie as"
Write-Host "  tarefas agendadas trocando CONTA pelo usuário que vai rodar, e MARKETING_"
Write-Host "  DIR / FUTEBOL_DIR pela pasta de cada instalação (ex.: C:\Auditoria\marketing,"
Write-Host "  ver INSTALAR_NO_GCP.md seção 4). Aponta para os .bat com layout, e-mails e"
Write-Host "  porta já prontos, não para o .py direto, senão essas variáveis ficam de fora:"
Write-Host ""
Write-Host "    schtasks /create /tn AuditoriaInfluenciadores-Marketing-Trabalhador ^"
Write-Host "      /tr ""MARKETING_DIR\iniciar_trabalhador_marketing.bat"" ^"
Write-Host "      /sc onstart /ru CONTA /rl highest /f"
Write-Host ""
Write-Host "    schtasks /create /tn AuditoriaInfluenciadores-Marketing-Tela ^"
Write-Host "      /tr ""MARKETING_DIR\iniciar_painel_marketing.bat"" ^"
Write-Host "      /sc onstart /ru CONTA /rl highest /f"
Write-Host ""
Write-Host "    schtasks /create /tn AuditoriaInfluenciadores-Futebol-Trabalhador ^"
Write-Host "      /tr ""FUTEBOL_DIR\iniciar_trabalhador_futebol.bat"" ^"
Write-Host "      /sc onstart /ru CONTA /rl highest /f"
Write-Host ""
Write-Host "    schtasks /create /tn AuditoriaInfluenciadores-Futebol-Tela ^"
Write-Host "      /tr ""FUTEBOL_DIR\iniciar_painel_futebol.bat"" ^"
Write-Host "      /sc onstart /ru CONTA /rl highest /f"
Write-Host "==========================================================================="
