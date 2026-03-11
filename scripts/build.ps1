param(
    [string]$Python = "python"
)

& $Python -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $Python -m PyInstaller --noconfirm --windowed --name CryptDesk --collect-all PySide6 cryptdesk\__main__.py
exit $LASTEXITCODE
