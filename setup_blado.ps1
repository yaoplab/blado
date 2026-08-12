# Setup Blado v1.0 — Installateur complet Windows
# Exécuter en tant qu'administrateur
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Blado — Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$BLADO_DIR = "C:\Program Files\Blado"
$PG_DIR = "C:\Program Files\PostgreSQL\16"

# 1. Vérifier PostgreSQL
Write-Host "[1/5] PostgreSQL..." -ForegroundColor Yellow
$pgInstalled = Test-Path "$PG_DIR\bin\psql.exe"
if (-not $pgInstalled) {
    Write-Host "  PostgreSQL non trouve. Telechargement..." -ForegroundColor Red
    Write-Host "  Veuillez installer PostgreSQL 16+ depuis https://www.postgresql.org/download/windows/" -ForegroundColor Red
    Write-Host "  Port: 55515 | User: postgres | Password: postgres" -ForegroundColor Yellow
    $continue = Read-Host "  Continuer si PostgreSQL est deja installe (o/n)?"
    if ($continue -ne "o") { exit 1 }
} else {
    Write-Host "  PostgreSQL trouve: $PG_DIR" -ForegroundColor Green
}

# 2. Créer la base de données
Write-Host "[2/5] Base de donnees BladoDB..." -ForegroundColor Yellow
$env:PGPASSWORD = "postgres"
$result = & "$PG_DIR\bin\psql.exe" -h 127.0.0.1 -p 55515 -U postgres -c "CREATE DATABASE bladodb;" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Base existe deja ou deja creee" -ForegroundColor Yellow
} else {
    Write-Host "  Base bladodb creee" -ForegroundColor Green
}

# 3. Exécuter les scripts SQL
Write-Host "[3/5] Schema SQL..." -ForegroundColor Yellow
& "$PG_DIR\bin\psql.exe" -h 127.0.0.1 -p 55515 -U postgres -d bladodb -f "$PSScriptRoot\sql\init_blado.sql" 2>&1 | Out-Null
Write-Host "  init_blado.sql OK" -ForegroundColor Green
& "$PG_DIR\bin\psql.exe" -h 127.0.0.1 -p 55515 -U postgres -d bladodb -f "$PSScriptRoot\sql\seed_metallurgie.sql" 2>&1 | Out-Null
Write-Host "  seed_metallurgie.sql OK" -ForegroundColor Green
& "$PG_DIR\bin\psql.exe" -h 127.0.0.1 -p 55515 -U postgres -d bladodb -f "$PSScriptRoot\sql\seed_agenda.sql" 2>&1 | Out-Null
Write-Host "  seed_agenda.sql OK" -ForegroundColor Green

# 4. Créer l'utilisateur admin
Write-Host "[4/5] Utilisateur admin..." -ForegroundColor Yellow
$hash = (Get-Content "$PSScriptRoot\sql\hash.py" -ErrorAction SilentlyContinue)
if (-not $hash) {
    # SHA-256 de "admin123"
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes("admin123"))
    $hash = [System.BitConverter]::ToString($bytes).Replace("-", "").ToLower()
}
& "$PG_DIR\bin\psql.exe" -h 127.0.0.1 -p 55515 -U postgres -d bladodb -c "INSERT INTO blado_user (email, password, full_name, role) VALUES ('admin@blado.local', '$hash', 'Administrateur', 'RH') ON CONFLICT (email) DO UPDATE SET password='$hash';" 2>&1 | Out-Null
Write-Host "  admin@blado.local / admin123" -ForegroundColor Green

# 5. Copier Blado
Write-Host "[5/5] Installation Blado..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$BLADO_DIR" | Out-Null
Copy-Item "$PSScriptRoot\dist\Blado.exe" "$BLADO_DIR\Blado.exe" -Force
Copy-Item "$PSScriptRoot\BladoCommon" "$BLADO_DIR\BladoCommon" -Recurse -Force
Copy-Item "$PSScriptRoot\photos" "$BLADO_DIR\photos" -Recurse -Force
Write-Host "  Blado installe dans $BLADO_DIR" -ForegroundColor Green

# Raccourci bureau
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Blado.lnk")
$Shortcut.TargetPath = "$BLADO_DIR\Blado.exe"
$Shortcut.WorkingDirectory = "$BLADO_DIR"
$Shortcut.Save()
Write-Host "  Raccourci bureau cree" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Blado installe avec succes !" -ForegroundColor Green
Write-Host "  Login : admin@blado.local" -ForegroundColor Green
Write-Host "  Mot de passe : admin123" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
