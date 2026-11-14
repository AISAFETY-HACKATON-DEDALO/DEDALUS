# DEDALUS · abre el panel (Windows / PowerShell)
#
#   powershell -ExecutionPolicy Bypass -File .\abrir.ps1
#
# Pide la clave de Oracle sin mostrarla y sin guardarla en ningún archivo.
# Enter sin escribir nada = arranca con SQLite local (sin Oracle).

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $env:CNOSOS_ORDS_URL) {
    $env:CNOSOS_ORDS_URL = "https://gee0c29fc768a8c-cnosos.adb.sa-bogota-1.oraclecloudapps.com/ords/cnosos_app/_/sql"
}
if (-not $env:CNOSOS_DB_USUARIO) { $env:CNOSOS_DB_USUARIO = "cnosos_app" }

$segura = Read-Host "Clave de Oracle (Enter = sin Oracle)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura)
try {
    $clave = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if ($clave) {
    $env:DEDALUS_ALMACEN = "oracle_rest"
    $env:CNOSOS_DB_CLAVE = $clave
    Write-Host "Conectando a Oracle (unos segundos)..."
} else {
    $env:DEDALUS_ALMACEN = "sqlite"
    Write-Host "Sin clave: arranco con SQLite local."
}

# Llaves de los modelos: primero esta ventana, luego las guardadas en Windows ("User"), y si no hay, se piden.
# Enter sin escribir = ese modelo no se usa (el panel ofrece solo los que tienen llave).
foreach ($par in @(@("GEMINI_API_KEY", "Gemini (ataca)"), @("GROQ_API_KEY", "Groq (defiende)"))) {
    $var, $nombre = $par
    $valor = [Environment]::GetEnvironmentVariable($var, "Process")
    if (-not $valor) { $valor = [Environment]::GetEnvironmentVariable($var, "User") }
    if (-not $valor) {
        $s = Read-Host "Llave de $nombre (Enter = sin $($nombre.Split(' ')[0]))" -AsSecureString
        $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
        try { $valor = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
    }
    if ($valor) {
        [Environment]::SetEnvironmentVariable($var, $valor, "Process")
        Write-Host "  $($nombre.Split(' ')[0]): lista"
    } else {
        Write-Host "  $($nombre.Split(' ')[0]): sin llave"
    }
}

$python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }
try {
    & $python -m dedalus.panel --abrir @args
} finally {
    Remove-Item Env:CNOSOS_DB_CLAVE -ErrorAction SilentlyContinue
    $clave = $null
}
