# Rodada agendada diária de sincronizacao_planilha_marketing.py — chamada pelo
# Windows Task Scheduler (tarefa "EGB_Auditoria_SincronizarPlanilhaMarketing"),
# não pra rodar manualmente (pra isso, chame o .py direto).
# Só grava um log com timestamp; não interage com a tela.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $scriptDir "..\auditorias\avisos-influenciadores-portaria136\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$logFile = Join-Path $logDir ("sincronizacao_{0}.log" -f (Get-Date -Format "yyyy-MM-dd_HHmmss"))
$scriptPath = Join-Path $scriptDir "sincronizar_planilha_marketing.py"

"=== Rodada iniciada em $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -FilePath $logFile -Encoding utf8
& py $scriptPath aplicar *>> $logFile
"=== Rodada finalizada em $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -FilePath $logFile -Append -Encoding utf8

# Mantém só os últimos 30 logs, pra pasta não crescer pra sempre sem controle.
Get-ChildItem -Path $logDir -Filter "sincronizacao_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 30 | Remove-Item -Force
