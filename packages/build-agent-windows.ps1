# Aegis SIEM Agent - Windows Installer Build Script
# Requires: NSIS (Nullsoft Scriptable Install System)
# Download from: https://nsis.sourceforge.io/

$VERSION = "1.0.0"
$PACKAGE_NAME = "Aegis-SIEM-Agent-$VERSION-Windows-x64"
$BUILD_DIR = "$(Get-Location)\packages\aegis-agent-windows"
$DIST_DIR = "$(Get-Location)\dist"

Write-Host "📦 Building Aegis SIEM Agent Windows installer v$VERSION" -ForegroundColor Green

# Create dist directory
New-Item -ItemType Directory -Force -Path $DIST_DIR | Out-Null

# Copy agent files
Write-Host "📂 Copying agent files..." -ForegroundColor Cyan
$TARGET_DIR = "$BUILD_DIR\agent"
Remove-Item -Path $TARGET_DIR -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $TARGET_DIR | Out-Null

# Copy agent source
Copy-Item -Path "aegis-agent\*" -Destination $TARGET_DIR -Recurse -Exclude @('__pycache__', '*.pyc', 'venv', '.pytest_cache', '*.db', 'agent.id', 'agent.credentials')

# Create NSIS script
Write-Host "📝 Creating NSIS installer script..." -ForegroundColor Cyan

$nsis_script = @"
!include "MUI2.nsh"

Name "Aegis SIEM Agent"
OutFile "$DIST_DIR\$PACKAGE_NAME.exe"
InstallDir "`$PROGRAMFILES64\Aegis\Agent"
InstallDirRegKey HKLM "Software\Aegis\Agent" "Install_Dir"
RequestExecutionLevel admin

# UI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "`${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "`${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

# Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "`$INSTDIR"
    
    # Copy agent files
    File /r "$TARGET_DIR\*.*"
    
    # Create config template
    FileOpen `$0 "`$INSTDIR\.env.example" w
    FileWrite `$0 "AEGIS_SERVER_URL=https://your-server.example.com`$\r`$\n"
    FileWrite `$0 "REGISTRATION_TOKEN=your-token-here`$\r`$\n"
    FileWrite `$0 "AGENT_NAME=`$\{COMPUTERNAME}`$\r`$\n"
    FileClose `$0
    
    # Install Python dependencies
    DetailPrint "Installing Python dependencies..."
    nsExec::ExecToLog 'python -m venv "`$INSTDIR\venv"'
    nsExec::ExecToLog '"`$INSTDIR\venv\Scripts\pip.exe" install -r "`$INSTDIR\requirements.txt"'
    
    # Create Windows Service
    DetailPrint "Installing Windows Service..."
    nsExec::ExecToLog 'sc create "AegisSIEMAgent" binPath= "`$INSTDIR\venv\Scripts\python.exe `$INSTDIR\main.py" start= auto'
    
    # Registry
    WriteRegStr HKLM "Software\Aegis\Agent" "Install_Dir" "`$INSTDIR"
    WriteRegStr HKLM "Software\Aegis\Agent" "Version" "$VERSION"
    
    # Uninstaller
    WriteUninstaller "`$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AegisSIEMAgent" "DisplayName" "Aegis SIEM Agent"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AegisSIEMAgent" "UninstallString" '"`$INSTDIR\Uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AegisSIEMAgent" "DisplayVersion" "$VERSION"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AegisSIEMAgent" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AegisSIEMAgent" "NoRepair" 1
SectionEnd

Section "Uninstall"
    # Stop and remove service
    nsExec::ExecToLog 'sc stop "AegisSIEMAgent"'
    nsExec::ExecToLog 'sc delete "AegisSIEMAgent"'
    
    # Remove files
    RMDir /r "`$INSTDIR"
    
    # Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AegisSIEMAgent"
    DeleteRegKey HKLM "Software\Aegis\Agent"
SectionEnd
"@

$nsis_script | Out-File -FilePath "$BUILD_DIR\installer.nsi" -Encoding ASCII

Write-Host "✅ NSIS script created!" -ForegroundColor Green
Write-Host ""
Write-Host "To build the installer:" -ForegroundColor Yellow
Write-Host "1. Install NSIS: https://nsis.sourceforge.io/"
Write-Host "2. Run: makensis packages\aegis-agent-windows\installer.nsi"
Write-Host ""
Write-Host "Note: Requires Python 3.11+ to be installed on target Windows systems"
