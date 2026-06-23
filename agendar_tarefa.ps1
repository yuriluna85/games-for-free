# Script PowerShell para agendar o Monitor de Jogos Grátis no Windows
$ErrorActionPreference = "Stop"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Agendador do Monitor de Jogos Grátis para Windows" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# Detect python path
$python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Host "[AVISO] Python.exe não foi encontrado no PATH. Usando comando padrão 'python.exe'." -ForegroundColor Yellow
    $python = "python.exe"
} else {
    Write-Host "[INFO] Python encontrado em: $python" -ForegroundColor Green
}

$scriptPath = Join-Path $PSScriptRoot "monitor.py"
Write-Host "[INFO] Caminho do script: $scriptPath" -ForegroundColor Green
Write-Host ""
Write-Host "[INFO] Criando tarefa agendada no Windows..."
Write-Host "[INFO] A tarefa rodará todos os dias às 13:01."
Write-Host ""

# Create task using schtasks
$taskCommand = 'schtasks /create /tn "MonitorJogosGratis" /tr "\"' + $python + '\" \"' + $scriptPath + '\"" /sc daily /st 13:01 /f'
Invoke-Expression $taskCommand

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "  [SUCESSO] Tarefa 'MonitorJogosGratis' criada!" -ForegroundColor Green
Write-Host "  Ela rodará diariamente às 13:01 no seu PC." -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""
Read-Host "Pressione Enter para fechar..."
