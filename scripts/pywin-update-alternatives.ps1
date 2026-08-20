[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"

function Get-RepositoryRoot {
    return Split-Path -Parent $PSScriptRoot
}

function Get-EmbeddedRuntimeDirectory {
    return Join-Path (Get-RepositoryRoot) ".embedded-python"
}

function Get-EmbeddedPythonExe {
    return Join-Path (Get-EmbeddedRuntimeDirectory) "python.exe"
}

function Get-PythonArchitectureSuffix {
    switch ($env:PROCESSOR_ARCHITECTURE.ToUpperInvariant()) {
        "ARM64" { return "embed-arm64.zip" }
        "X86" { return "embed-win32.zip" }
        default { return "embed-amd64.zip" }
    }
}

function Get-LatestPythonVersion {
    $response = Invoke-WebRequest -Uri "https://www.python.org/ftp/python/"
    $versions = [regex]::Matches($response.Content, 'href="(\d+\.\d+\.\d+)/"') |
        ForEach-Object { $_.Groups[1].Value } |
        Sort-Object {[version]$_}

    if (-not $versions) {
        throw "Unable to determine the latest Python release from python.org."
    }

    return $versions[-1]
}

function Enable-EmbeddedSitePackages {
    $runtimeDir = Get-EmbeddedRuntimeDirectory
    $pthFile = Get-ChildItem -Path $runtimeDir -Filter "python*._pth" | Select-Object -First 1
    if (-not $pthFile) {
        throw "Unable to locate python*._pth in the embedded runtime."
    }

    $lines = Get-Content -Path $pthFile.FullName
    if ($lines -notcontains ".") {
        $lines += "."
    }
    if ($lines -notcontains "import site") {
        $lines += "import site"
    }
    Set-Content -Path $pthFile.FullName -Value $lines
}

function Install-EmbeddedPython {
    $runtimeDir = Get-EmbeddedRuntimeDirectory
    if (Test-Path (Get-EmbeddedPythonExe)) {
        return
    }

    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

    $version = Get-LatestPythonVersion
    $archiveName = "python-$version-" + (Get-PythonArchitectureSuffix)
    $downloadUrl = "https://www.python.org/ftp/python/$version/$archiveName"
    $archivePath = Join-Path $runtimeDir $archiveName

    Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath
    Expand-Archive -Path $archivePath -DestinationPath $runtimeDir -Force
    Remove-Item -Path $archivePath -Force
    Enable-EmbeddedSitePackages
}

Install-EmbeddedPython

$repoRoot = Get-RepositoryRoot
Push-Location $repoRoot
try {
    & (Get-EmbeddedPythonExe) -m pywin_update_alternatives @Arguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
