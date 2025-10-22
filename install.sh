#!/usr/bin/env bash

set -euo pipefail

OWNER="bbbugg"
REPO="TJUEcard"
API="https://api.github.com/repos/${OWNER}/${REPO}/releases/latest"
UA="TJUEcard-Installer"

# 检测系统与架构
case "$(uname -s)" in
Linux) OS="linux" ;;
Darwin) OS="macos" ;;
*)
    echo "❌ 不支持的系统: $(uname -s)，请在仓库中提交 Issue。"
    exit 1
    ;;
esac

case "$(uname -m)" in
    # 64位支持
    x86_64 | amd64) ARCH="x86_64" ;;
    arm64 | aarch64) ARCH="arm64" ;;
    # 32位x86支持（i386/i686常见于老Linux）
    i386 | i686 | x86) ARCH="x86" ;;
    # 32位ARM支持（armv7l等常见于Raspberry Pi等设备）
    armv7l | armhf | armel) ARCH="arm32" ;;
    # macOS 32位不支持（Apple已弃用）
    i386 | i686)  # 只在Darwin时检查
        if [[ "$OS" == "macos" ]]; then
            echo "❌ macOS不支持32位架构: $(uname -m)"
            exit 1
        fi
        ;;
    *)
    echo "❌ 不支持的架构: $(uname -m)，请在仓库中提交 Issue。"
    exit 1
    ;;
esac

# 询问安装目录
default_dir="$(pwd)"
read -r -p "输入安装目录 (回车使用默认当前目录: ${default_dir}): " INSTALL_DIR
INSTALL_DIR="${INSTALL_DIR:-$default_dir}"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# 获取下载链接
echo "🔍 正在获取最新版本..."
url=$(curl -fsSL -H "User-Agent: $UA" "$API" |
    grep -oE '"browser_download_url": *"[^"]+"' |
    sed -E 's/.*"browser_download_url": *"([^"]+)".*/\1/' |
    grep "TJUEcard-${OS}-${ARCH}-v.*\.tar\.gz" |
    head -n1)

if [[ -z "$url" ]]; then
    echo "❌ 未找到匹配的安装包 (TJUEcard-${OS}-${ARCH}-v*.tar.gz)"
    echo "   提示: 请检查GitHub仓库是否提供${OS}-${ARCH}版本https://github.com/bbbugg/TJUEcard/releases"
    echo "        或在仓库中提交 Issue。"
    exit 1
fi

file="$(basename "$url")"
echo "⬇️  下载: $file"
curl -fL --retry 3 -H "User-Agent: $UA" -o "$file" "$url"

# 解压并执行安装器
echo "📦 解压中..."
tar -xzf "$file"
rm -f "$file" # 删除下载包

if [[ ! -x "./TJUEcardSetup" ]]; then
    echo "❌ 未找到 TJUEcardSetup 可执行文件"
    exit 1
fi

echo "🚀 运行安装程序..."
chmod +x ./TJUEcardSetup
./TJUEcardSetup

echo "✅ 安装完成。"