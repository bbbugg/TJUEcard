@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

:: ===== 基础信息 =====
set "OWNER=bbbugg"
set "REPO=TJUEcard"
set "UA=TJUEcard-Installer"
set "OS=windows"

:: ===== 架构识别 =====
set "ARCH=x86_64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=arm64"
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set "ARCH=arm64"

:: ===== 询问安装目录 =====
set "DEFAULT_DIR=%cd%"
set /p INSTALL_DIR=安装目录 (默认: %DEFAULT_DIR%): 
if "%INSTALL_DIR%"=="" set "INSTALL_DIR=%DEFAULT_DIR%"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

echo 系统: %OS%   架构: %ARCH%
echo 安装目录: %INSTALL_DIR%
echo.

:: ===== 用 PowerShell 拿下载链接 (严格匹配命名) =====
for /f "usebackq delims=" %%U in (`powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$h=@{'User-Agent'='%UA%'}; $api='https://api.github.com/repos/%OWNER%/%REPO%/releases/latest';" ^
  "$a=(Invoke-RestMethod -Headers $h -Uri $api).assets;" ^
  "($a | Where-Object { $_.browser_download_url -match 'TJUEcard-%OS%-%ARCH%-v\d+\.\d+\.\d+\.tar\.gz' } | Select-Object -First 1 -ExpandProperty browser_download_url)"`) do set "URL=%%U"

if not defined URL (
  echo ❌ 未找到匹配的安装包: TJUEcard-%OS%-%ARCH%-v*.tar.gz
  exit /b 1
)

for %%F in ("%URL%") do set "FILE=%%~nxF"
echo ⬇️  下载: %FILE%
curl -L -o "%FILE%" "%URL%"
if errorlevel 1 (
  echo ❌ 下载失败
  exit /b 1
)

echo 📦 解压中...
tar -xzf "%FILE%"
del /f /q "%FILE%"   &  echo ✅ 已删除下载压缩包

if not exist "%INSTALL_DIR%\TJUEcardSetup.exe" (
  echo ❌ 未找到 TJUEcardSetup.exe (应在压缩包内) 
  exit /b 1
)

echo 🚀 运行安装程序...
start /wait "" "%INSTALL_DIR%\TJUEcardSetup.exe"

echo.
echo ✅ 安装完成。
exit /b 0
