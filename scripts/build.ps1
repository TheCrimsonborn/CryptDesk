param(
    [string]$Python = "python",
    [switch]$OneFile
)

& $Python -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$arguments = @(
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--windowed",
    "--name",
    "CryptDesk",
    "--collect-all",
    "PySide6"
)

if ($OneFile) {
    $arguments += "--onefile"
}

$arguments += "cryptdesk\\__main__.py"

& $Python @arguments
exit $LASTEXITCODE
