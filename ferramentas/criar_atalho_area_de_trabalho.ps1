# Cria um atalho na Area de Trabalho para abrir o programa com um clique so.
#
# POR QUE ESTE ARQUIVO EXISTE (09/09/2026)
#
# Ate aqui, abrir o programa exigia achar a pasta e clicar em dois arquivos
# .bat diferentes, numa ordem que importa. Pedido do auditor para facilitar
# a vida de quem nao acompanhou a historia dos dois processos, como a
# analista de Marketing que vai usar isso sem ter mexido no codigo nenhuma
# vez.
#
# O atalho aponta para abrir_programa.bat (criado no mesmo dia), que sobe o
# trabalhador e a tela na ordem certa. NAO MUDA NADA DA ARQUITETURA DE DOIS
# PROCESSOS, so poupa o caminho ate a pasta.
#
# O ICONE E SO UM PADRAO DO WINDOWS, escolhido sem poder ver como fica nesta
# maquina. Trocar depois: botao direito no atalho > Propriedades > Alterar
# icone.
#
# Rode uma vez, NA MAQUINA ONDE O ATALHO DEVE APARECER:
#     powershell -ExecutionPolicy Bypass -File ferramentas\criar_atalho_area_de_trabalho.ps1

$ErrorActionPreference = "Stop"

$pastaDoPrograma = Split-Path -Parent $PSScriptRoot
$alvo = Join-Path $pastaDoPrograma "abrir_programa.bat"

if (-not (Test-Path $alvo)) {
    Write-Host "ERRO: nao achei $alvo."
    Write-Host "Rode este script de dentro da pasta ferramentas, sem mover nada de lugar."
    exit 1
}

$areaDeTrabalho = [Environment]::GetFolderPath("Desktop")
$caminhoAtalho = Join-Path $areaDeTrabalho "Abrir Monitoramento de Influenciadores.lnk"

$shell = New-Object -ComObject WScript.Shell
$atalho = $shell.CreateShortcut($caminhoAtalho)
$atalho.TargetPath = $alvo
$atalho.WorkingDirectory = $pastaDoPrograma
$atalho.IconLocation = "%SystemRoot%\System32\imageres.dll,174"
$atalho.Description = "Abre o trabalhador e a tela do programa, na ordem certa"
$atalho.Save()

Write-Host "Atalho criado em:"
Write-Host "  $caminhoAtalho"
Write-Host ""
Write-Host "Se o icone nao agradar, troque em: botao direito no atalho > Propriedades > Alterar icone."
