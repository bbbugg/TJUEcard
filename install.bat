@echo off
setlocal enabledelayedexpansion
title TJUEcard Installer
chcp 65001 >nul

set "OWNER=bbbugg"
set "REPO=TJUEcard"
set "API=https://api.github.com/repos/%OWNER%/%REPO%/releases/latest"

echo 检测系统与架构...
set "OS=windows"
for /f "tokens=2 delims==" %%a in ('wmic os get osarchitecture /value ^| find "="') do set "ARCH=%%a"
if /i "%ARCH%"=="64-bit" (set "ARCH=x86_64") else (set "ARCH=arm64")

set "DEFAULT_DIR=%cd%"
set /p INSTALL_DIR=安装目录 (默认: %DEFAULT_DIR%) : 
if "%INSTALL_DIR%"=="" set "INSTALL_DIR=%DEFAULT_DIR%"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

echo.
echo 获取最新 Release 信息...
set "UA=TJUEcard-Installer"
for /f "usebackq tokens=*" %%a in (`curl -fsSL -H "User-Agent: %UA%" "%API%"`) do (
  set "JSON=!JSON!%%a"
)

rem 提取下载链接: TJUEcard-windows-x86_64-v*.tar.gz
for /f "tokens=*" %%u in ('echo !JSON! ^| findstr /r /c:"TJUEcard-%OS%-%ARCH%-v[0-9][0-9]*[.]tar[.]gz"') do (
  for /f "tokens=2 delims=:" %%b in ("%%u") do (
    set "URL=%%b"
  )
)
set "URL=%URL:~2,-2%"

if "%URL%"=="" (
  echo ❌ 未找到匹配的安装包 (TJUEcard-%OS%-%ARCH%-v*.tar.gz)
  exit /b 1
)

for %%f in ("%URL%") do set "FILE=%%~nxf"
echo.
echo 下载: %FILE%
curl -L -o "%FILE%" "%URL%"
if errorlevel 1 (
  echo ❌ 下载失败。
  exit /b 1
)

echo 解压中...
tar -xzf "%FILE%"
del "%FILE%"

if not exist "TJUEcardSetup.exe" (
  echo ❌ 未找到 TJUEcardSetup.exe
  exit /b 1
)

echo.
echo 运行安装程序...
start /wait "" "%INSTALL_DIR%\TJUEcardSetup.exe"

echo.
echo ✅ 安装完成。
pause
