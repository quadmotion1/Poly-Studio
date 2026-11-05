<#
.SYNOPSIS
  Build Poly Studio and package it as an MSIX for the Microsoft Store.

.EXAMPLE
  pwsh packaging/windows/package-msix.ps1 -IdentityName "12345Fabian.PolyStudio" `
       -Publisher "CN=ABCDEF01-2345-6789-ABCD-EF0123456789" -PublisherDisplayName "Fabian"

  Take the three values from Partner Center > your app > Product management > Product identity.
  Output: dist/msix/PolyStudio_<version>_<arch>.msix (not signed: Partner Center signs it).
  To try the package on your own PC first, sign it with a self-signed certificate (see README).

  Needs: Rust (MSVC toolchain) and the Windows 10/11 SDK (makeappx.exe).
#>
param(
  [Parameter(Mandatory)] [string] $IdentityName,
  [Parameter(Mandatory)] [string] $Publisher,
  [Parameter(Mandatory)] [string] $PublisherDisplayName,
  [ValidateSet('x64', 'arm64')] [string] $Arch = 'x64',
  [switch] $SkipBuild
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Target = if ($Arch -eq 'x64') { 'x86_64-pc-windows-msvc' } else { 'aarch64-pc-windows-msvc' }

# The version lives in [workspace.package] in Cargo.toml. The Store wants four numbers and keeps the
# fourth for itself, so 0.40.0-rc.2 becomes 0.40.0.0.
$Version = $null
$inPkg = $false
foreach ($line in Get-Content (Join-Path $Root 'Cargo.toml')) {
  if ($line -match '^\s*\[') { $inPkg = ($line.Trim() -eq '[workspace.package]'); continue }
  if ($inPkg -and $line -match '^\s*version\s*=\s*"(\d+)\.(\d+)\.(\d+)') { $Version = "$($Matches[1]).$($Matches[2]).$($Matches[3]).0"; break }
}
if (-not $Version) { throw 'could not read the version from Cargo.toml' }

if (-not $SkipBuild) {
  $flagVar = 'CARGO_TARGET_' + ($Target.ToUpper() -replace '-', '_') + '_RUSTFLAGS'
  [Environment]::SetEnvironmentVariable($flagVar, '-C target-feature=+crt-static')
  Write-Output "==> cargo build ($Target)"
  # No --locked the first time: the first build after the rebrand may rewrite Cargo.lock.
  cargo build --release -p solidcraft --target $Target
  if ($LASTEXITCODE -ne 0) { throw 'cargo build failed' }
}
$Exe = Join-Path $Root "target\$Target\release\solidcraft.exe"
if (-not (Test-Path $Exe)) { throw "missing $Exe" }

$Stage = Join-Path $Root "target\msix-stage\$Arch"
Remove-Item -Recurse -Force $Stage -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $Stage | Out-Null
Copy-Item $Exe (Join-Path $Stage 'PolyStudio.exe')
Copy-Item -Recurse (Join-Path $PSScriptRoot 'msix\Assets') (Join-Path $Stage 'Assets')

# Licence texts travel with the app: the MIT/Apache terms of the SolidCraft code it is built on
# require the copyright and permission notices to stay with every copy.
$Legal = Join-Path $Stage 'legal'
New-Item -ItemType Directory -Force $Legal | Out-Null
foreach ($f in 'LICENSE-MIT', 'LICENSE-APACHE', 'NOTICE', 'ATTRIBUTION.md', 'THIRD-PARTY-LICENSES.txt', 'POLYSTUDIO.md') {
  Copy-Item (Join-Path $Root $f) $Legal
}

$manifest = Get-Content (Join-Path $PSScriptRoot 'msix\AppxManifest.xml.template') -Raw
$manifest = $manifest.Replace('@IDENTITY_NAME@', $IdentityName).Replace('@PUBLISHER@', $Publisher).
  Replace('@PUBLISHER_DISPLAY_NAME@', $PublisherDisplayName).Replace('@VERSION@', $Version).Replace('@ARCH@', $Arch)
Set-Content -Path (Join-Path $Stage 'AppxManifest.xml') -Value $manifest -Encoding UTF8

$makeappx = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\makeappx.exe" -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending | Select-Object -First 1
if (-not $makeappx) { throw 'makeappx.exe not found: install the Windows 10/11 SDK' }
$Out = Join-Path $Root 'dist\msix'
New-Item -ItemType Directory -Force $Out | Out-Null
$Msix = Join-Path $Out "PolyStudio_${Version}_$Arch.msix"
& $makeappx.FullName pack /d $Stage /p $Msix /o
if ($LASTEXITCODE -ne 0) { throw 'makeappx failed' }
Write-Output "==> $Msix"
